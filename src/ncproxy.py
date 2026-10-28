#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["paramiko>=2.7"]
# ///
# SPDX-License-Identifier: BSD-3-Clause
"""Transparent NETCONF over SSH proxy with logging and message patching."""

from __future__ import annotations

import argparse
import binascii
import json
import logging
import os
import re
import socket
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import BinaryIO, List, Optional, TextIO, Tuple
from urllib.parse import urlparse

import paramiko

__version__ = "2.0.0"

EOM = b"]]>]]>"
CHUNK_END = b"\n##\n"


class Framing(str, Enum):
    BASE10 = "base:1.0"
    BASE11 = "base:1.1"


class NetconfFramer:
    """Stateful RFC 6241/6242 message extractor for one direction of the proxy."""

    def __init__(self) -> None:
        self._wire = b""
        self._base11_body = b""

    def feed(self, data: bytes) -> List[Tuple[bytes, Framing]]:
        self._wire += data
        messages: List[Tuple[bytes, Framing]] = []
        while self._extract_one(messages):
            pass
        return messages

    def _extract_one(self, messages: List[Tuple[bytes, Framing]]) -> bool:
        if not self._wire and not self._base11_body:
            return False
        if self._base11_body or (len(self._wire) >= 2 and self._wire[:2] == b"\n#"):
            return self._extract_base11(messages)
        if len(self._wire) <= 4:
            return False
        return self._extract_base10(messages)

    def _extract_base10(self, messages: List[Tuple[bytes, Framing]]) -> bool:
        if EOM not in self._wire:
            return False
        msg, self._wire = self._wire.split(EOM, 1)
        if msg:
            messages.append((msg, Framing.BASE10))
        return True

    def _extract_base11(self, messages: List[Tuple[bytes, Framing]]) -> bool:
        body = self._base11_body
        buf = self._wire
        pos = 0
        while pos < len(buf):
            if buf[pos : pos + 4] == CHUNK_END:
                messages.append((body, Framing.BASE11))
                self._base11_body = b""
                self._wire = buf[pos + 4 :]
                return True
            if buf[pos : pos + 2] == b"\n#":
                nl = buf.find(b"\n", pos + 2)
                if nl == -1:
                    self._base11_body = body
                    self._wire = buf[pos:]
                    return False
                try:
                    chunk_len = int(buf[pos + 2 : nl])
                except ValueError:
                    self._base11_body = body
                    self._wire = buf[pos:]
                    return False
                data_start = nl + 1
                data_end = data_start + chunk_len
                if data_end > len(buf):
                    self._base11_body = body
                    self._wire = buf[pos:]
                    return False
                body += buf[data_start:data_end]
                pos = data_end
                continue
            self._base11_body = body
            self._wire = buf[pos:]
            return False
        self._base11_body = body
        self._wire = b""
        return False


def split_messages(buf: bytes) -> Tuple[List[bytes], bytes, Optional[Framing]]:
    """One-shot parse (tests); production code uses NetconfFramer per direction."""
    framer = NetconfFramer()
    pairs = framer.feed(buf)
    msgs = [msg for msg, _ in pairs]
    if pairs:
        framing = pairs[-1][1]
    elif framer._base11_body or (len(framer._wire) >= 2 and framer._wire[:2] == b"\n#"):
        framing = Framing.BASE11
    elif framer._wire:
        framing = Framing.BASE10
    else:
        framing = None
    remainder = framer._wire
    if framer._base11_body:
        remainder = framer._base11_body + remainder
    return msgs, remainder, framing


def encode_message(msg: bytes, framing: Framing, chunk_size: int = 16384) -> bytes:
    """Encode a NETCONF message for the wire."""
    if framing == Framing.BASE10:
        return msg + EOM
    out = b""
    pos = 0
    while pos < len(msg):
        piece = msg[pos : pos + chunk_size]
        pos += len(piece)
        out += b"\n#%d\n" % len(piece)
        out += piece
    return out + CHUNK_END


@dataclass
class ModifierRule:
    regex: re.Pattern[str]
    patch: str


@dataclass
class AutoRespondRule:
    regex: re.Pattern[str]
    response: str


@dataclass
class Rules:
    server_msg_modifier: List[ModifierRule] = field(default_factory=list)
    client_msg_modifier: List[ModifierRule] = field(default_factory=list)
    auto_respond: List[AutoRespondRule] = field(default_factory=list)


def _load_structured(path: str) -> dict:
    lower = path.lower()
    if lower.endswith((".yaml", ".yml")):
        try:
            import yaml  # type: ignore
        except ImportError:
            sys.stderr.write("PyYAML required for YAML rules; pip install netconf-tools[yaml]\n")
            sys.exit(2)
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_path(base: str, rel: str) -> str:
    if os.path.isabs(rel):
        return rel
    candidate = os.path.join(os.path.dirname(base), rel)
    if os.path.isfile(candidate):
        return candidate
    return rel


def load_rules(path: str) -> Rules:
    data = _load_structured(path)
    rules = Rules()

    def modifiers(key: str) -> List[ModifierRule]:
        out: List[ModifierRule] = []
        for item in data.get(key, []):
            patch = item.get("patch", "")
            if "patch-file" in item:
                with open(_resolve_path(path, item["patch-file"]), encoding="utf-8") as pf:
                    patch = pf.read()
            out.append(ModifierRule(regex=re.compile(item["match"], re.DOTALL), patch=patch))
        return out

    def auto() -> List[AutoRespondRule]:
        out: List[AutoRespondRule] = []
        for item in data.get("auto-respond", []):
            response = item.get("response", "")
            if "response-file" in item:
                with open(_resolve_path(path, item["response-file"]), encoding="utf-8") as rf:
                    response = rf.read()
            out.append(
                AutoRespondRule(regex=re.compile(item["match"], re.DOTALL), response=response)
            )
        return out

    rules.server_msg_modifier = modifiers("server-msg-modifier")
    rules.client_msg_modifier = modifiers("client-msg-modifier")
    rules.auto_respond = auto()
    return rules


def apply_modifiers(msg: bytes, modifiers: List[ModifierRule]) -> bytes:
    text = msg.decode("utf-8", errors="surrogateescape")
    for rule in modifiers:
        text = rule.regex.sub(rule.patch, text)
    return text.encode("utf-8", errors="surrogateescape")


@dataclass
class ProxyConfig:
    hostname: str
    port: int
    listen_port: int
    bind_addr: str
    rules: Rules
    host_key_path: Optional[str]
    serverlog: BinaryIO
    clientlog: BinaryIO
    log_level: int = logging.WARNING
    paramiko_log_level: int = logging.NOTSET


def _listen_socket(bind_addr: str, port: int) -> socket.socket:
    """Bind a listening TCP socket (IPv4 or IPv6)."""
    if bind_addr in ("::", "::0") or ":" in bind_addr:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except OSError:
            pass
        sock.bind((bind_addr, port, 0, 0))
        return sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((bind_addr, port))
    return sock


def _recv_available(channel: paramiko.Channel) -> bytes:
    chunks: List[bytes] = []
    while channel.recv_ready():
        data = channel.recv(65535)
        if not data:
            break
        chunks.append(data)
    return b"".join(chunks)


def _send_all(channel: paramiko.Channel, data: bytes) -> None:
    view = memoryview(data)
    while len(view):
        sent = channel.send(view)
        if sent == 0:
            raise OSError("SSH channel closed during send")
        view = view[sent:]


def _connect_upstream(hostname: str, port: int, username: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )  # lab tool: upstream host keys not verified
    client.connect(
        hostname=hostname,
        port=port,
        username=username,
        password=password,
        timeout=30,
        allow_agent=False,
        look_for_keys=False,
    )
    return client


def _count_to_level(count: Optional[int], default: int) -> int:
    if count is None:
        return default
    levels = [
        logging.CRITICAL,
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
    ]
    idx = min(max(count - 1, 0), len(levels) - 1)
    return levels[idx]


class NetconfSubsystemHandler(paramiko.SubsystemHandler):
    def __init__(
        self,
        channel: paramiko.Channel,
        name: str,
        server: paramiko.ServerInterface,
        srv_transport: paramiko.Transport,
        config: ProxyConfig,
        log: logging.Logger,
    ) -> None:
        super().__init__(channel, name, server)
        self.srv_transport = srv_transport
        self.config = config
        self.log = log

    def start_subsystem(
        self, name: str, transport: paramiko.Transport, channel: paramiko.Channel
    ) -> None:
        try:
            srv_channel = self.srv_transport.open_session()
            srv_channel.invoke_subsystem("netconf")
        except Exception as exc:
            self.log.warning("NETCONF over SSH to %s failed: %s", self.config.hostname, exc)
            channel.close()
            return

        self.log.info("NETCONF messaging capture")
        serverlog = self.config.serverlog
        clientlog = self.config.clientlog
        rules = self.config.rules
        client_msgs = 0
        server_msgs = 0
        srv_framer = NetconfFramer()
        ncc_framer = NetconfFramer()

        def pump_server_to_client() -> None:
            nonlocal server_msgs
            for msg, srv_framing in srv_framer.feed(_recv_available(srv_channel)):
                if not msg:
                    continue
                msg = apply_modifiers(msg, rules.server_msg_modifier)
                wire = encode_message(msg, srv_framing)
                _send_all(channel, wire)
                serverlog.write(wire)
                serverlog.flush()
                server_msgs += 1

        def pump_client_to_server() -> None:
            nonlocal client_msgs
            for msg, ncc_framing in ncc_framer.feed(_recv_available(channel)):
                if not msg:
                    continue
                msg = apply_modifiers(msg, rules.client_msg_modifier)
                sendmsg = True
                for rule in rules.auto_respond:
                    text = msg.decode("utf-8", errors="surrogateescape")
                    if rule.regex.match(text):
                        self.log.info("Auto-response to NETCONF client message")
                        tmp = rule.regex.sub(rule.response, text).encode(
                            "utf-8", errors="surrogateescape"
                        )
                        wire = encode_message(tmp, ncc_framing)
                        _send_all(channel, wire)
                        serverlog.write(wire)
                        serverlog.flush()
                        sendmsg = False
                        break
                wire = encode_message(msg, ncc_framing)
                if sendmsg:
                    _send_all(srv_channel, wire)
                    client_msgs += 1
                clientlog.write(wire)
                clientlog.flush()

        while transport.is_active():
            pump_server_to_client()
            pump_client_to_server()
            peer_closed = srv_channel.exit_status_ready() or channel.exit_status_ready()
            if peer_closed and not (
                srv_framer._wire
                or srv_framer._base11_body
                or ncc_framer._wire
                or ncc_framer._base11_body
                or srv_channel.recv_ready()
                or channel.recv_ready()
            ):
                break
            time.sleep(0.01)

        pump_server_to_client()
        pump_client_to_server()
        self.log.info(
            "Relayed %d server message(s) and %d client message(s)",
            server_msgs,
            client_msgs,
        )

        self.log.info("NETCONF communication finished")
        if srv_channel.exit_status_ready():
            self.log.warning("Connection closed by peer; server down")
        if channel.exit_status_ready():
            self.log.warning("Connection closed by peer; client down")
        srv_channel.close()
        proxy_server = self.get_server()
        if isinstance(proxy_server, ProxyServerInterface):
            proxy_server.close_upstream()


class ProxyServerInterface(paramiko.ServerInterface):
    def __init__(self, config: ProxyConfig, log: logging.Logger) -> None:
        self.config = config
        self.log = log
        self.event = threading.Event()
        self.srv_transport: Optional[paramiko.Transport] = None
        self._upstream: Optional[paramiko.SSHClient] = None

    def close_upstream(self) -> None:
        if self._upstream is not None:
            try:
                self._upstream.close()
            except OSError:
                pass
        self._upstream = None
        self.srv_transport = None

    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username: str, password: str) -> int:
        self.log.debug("check_auth_password(username=%s)", username)
        self.close_upstream()
        try:
            self._upstream = _connect_upstream(
                self.config.hostname, self.config.port, username, password
            )
            self.srv_transport = self._upstream.get_transport()
        except Exception as exc:
            self.log.critical("Server session setup/authentication failed: %s", exc)
            self.log.debug("%s", "".join(traceback.format_exception(*sys.exc_info())))
            self.close_upstream()
            return paramiko.AUTH_FAILED
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        self.log.critical("Public key authentication is NOT supported")
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        return "password"

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        self.log.critical("SHELL request is NOT supported")
        self.event.set()
        return False

    def check_channel_exec_request(self, channel: paramiko.Channel, command: str) -> bool:
        self.log.critical("EXEC request is NOT supported")
        return False

    def check_channel_pty_request(
        self,
        channel: paramiko.Channel,
        term: str,
        width: int,
        height: int,
        pixelwidth: int,
        pixelheight: int,
        modes: str,
    ) -> bool:
        self.log.critical("PTY request is NOT supported")
        return False

    def check_channel_subsystem_request(self, channel: paramiko.Channel, name: str) -> bool:
        if name != "netconf":
            self.log.critical("Subsystem %s is NOT supported", name)
            return False
        if self.srv_transport is None:
            self.log.critical("No upstream SSH session (authentication to device failed?)")
            return False
        return super().check_channel_subsystem_request(channel, name)


class ProxyServer:
    """Embeddable ncproxy listener."""

    def __init__(self, config: ProxyConfig) -> None:
        self.config = config
        self.port = config.listen_port
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._host_key: paramiko.RSAKey

    def _load_host_key(self) -> paramiko.RSAKey:
        if self.config.host_key_path:
            return paramiko.RSAKey.from_private_key_file(self.config.host_key_path)
        return paramiko.RSAKey.generate(2048)

    def _serve(self) -> None:
        log = logging.getLogger("ncproxy")
        log.setLevel(self.config.log_level)
        if not log.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", "%y/%m/%d %H:%M:%S")
            )
            log.addHandler(handler)

        plog = logging.getLogger("paramiko")
        plog.setLevel(self.config.paramiko_log_level)

        class NetconfHandler(NetconfSubsystemHandler):
            def __init__(self, channel, name, server, cfg, proxy_log):
                if not isinstance(server, ProxyServerInterface) or server.srv_transport is None:
                    raise RuntimeError("upstream SSH session is not available")
                super().__init__(channel, name, server, server.srv_transport, cfg, proxy_log)

        while not self._stop.is_set():
            try:
                client, addr = self._sock.accept()  # type: ignore[union-attr]
            except OSError:
                break
            log.info("Incoming client connection from %s (srcport: %d)", addr[0], addr[1])
            try:
                transport = paramiko.Transport(client)
                transport.load_server_moduli()
                transport.add_server_key(self._host_key)
                transport.set_subsystem_handler("netconf", NetconfHandler, self.config, log)
                transport.start_server(server=ProxyServerInterface(self.config, log))
            except Exception as exc:
                log.warning("Connection failed: %s", exc)

    def start(self) -> None:
        self._host_key = self._load_host_key()
        self._sock = _listen_socket(self.config.bind_addr, self.config.listen_port)
        self._sock.listen(100)
        if self.config.listen_port == 0:
            self.port = self._sock.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=5)


def _open_binary(path: str) -> BinaryIO:
    if path == "-":
        return sys.stdout.buffer
    return open(path, "wb", buffering=0)


def _open_log(path: Optional[str]) -> TextIO:
    if path is None:
        return sys.stderr
    return open(path, "w", encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    prog = "ncproxy"
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("--version", action="version", version=f"{prog} {__version__}")
    parser.add_argument("-v", "--verbose", action="count", help="enable logging")
    parser.add_argument("-d", "--debug", action="count", help="enable ssh-lib logging")
    parser.add_argument("--logfile", metavar="filename", help="trace/debug log (default: stderr)")
    parser.add_argument(
        "--serverlog",
        metavar="filename",
        default="-",
        help="server log (default: stdout)",
    )
    parser.add_argument(
        "--clientlog",
        metavar="filename",
        default=None,
        help="client log (default: stderr)",
    )
    parser.add_argument("--patch", metavar="filename", help="patch rules JSON/YAML file")
    parser.add_argument("--port", metavar="tcpport", type=int, default=830, help="listen port")
    parser.add_argument("--bind", metavar="ADDR", default="0.0.0.0", help="bind address")
    parser.add_argument("--host-key", metavar="FILE", help="persistent host key file")
    parser.add_argument(
        "server",
        metavar="netconf://<hostname>[:port]",
        help="upstream NETCONF server",
    )
    options = parser.parse_args(argv)

    log_level = _count_to_level(options.verbose, logging.NOTSET)
    paramiko_level = _count_to_level(options.debug, logging.NOTSET)

    server_arg = options.server
    url = urlparse(server_arg if "://" in server_arg else "netconf://" + server_arg)
    if url.scheme != "netconf":
        print("Connection to NETCONF server(s) only", file=sys.stderr)
        return 2
    hostname = url.hostname or "127.0.0.1"
    port = url.port or 830

    rules = load_rules(options.patch) if options.patch else Rules()

    config = ProxyConfig(
        hostname=hostname,
        port=port,
        listen_port=options.port,
        bind_addr=options.bind,
        rules=rules,
        host_key_path=options.host_key,
        serverlog=_open_binary(options.serverlog),
        clientlog=(
            sys.stderr.buffer if options.clientlog is None else _open_binary(options.clientlog)
        ),
        log_level=log_level if log_level != logging.NOTSET else logging.INFO,
        paramiko_log_level=paramiko_level,
    )

    proxy = ProxyServer(config)
    log = logging.getLogger("ncproxy")
    log.setLevel(config.log_level)
    handler = logging.StreamHandler(_open_log(options.logfile))
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", "%y/%m/%d %H:%M:%S")
    )
    log.addHandler(handler)
    if config.host_key_path is None:
        log.debug(
            "Server Key: %s",
            binascii.hexlify(proxy._load_host_key().get_fingerprint()).decode(),
        )

    try:
        proxy.start()
        log.info(
            "Listening for NETCONF clients on %s:%s (password auth; point client at this host/port)",
            config.bind_addr,
            proxy.port,
        )
        if config.host_key_path is None:
            log.info(
                "Proxy SSH host key is ephemeral; use --host-key FILE for a stable key (required by many clients)"
            )
        while proxy._thread and proxy._thread.is_alive():
            proxy._thread.join(timeout=1)
    except KeyboardInterrupt:
        log.info("ncproxy terminated by user")
    finally:
        proxy.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
