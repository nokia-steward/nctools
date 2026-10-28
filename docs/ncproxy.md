# ncproxy

Transparent NETCONF over SSH proxy (Paramiko). The client connects to ncproxy; ncproxy connects upstream with the same credentials. Hello messages, RPCs, replies, and notifications can be logged. JSON or YAML rules can patch traffic in flight or auto-answer selected RPCs.

## Requirements

- SSH from the NETCONF client to ncproxy, and from ncproxy to the upstream server
- [Paramiko](https://pypi.org/project/paramiko/) (included with `netconf-tools`)
- Optional: [PyYAML](https://pypi.org/project/PyYAML/) for YAML rules (`pip install "netconf-tools[yaml]"`)

## Quick example

```bash
ncproxy --host-key ./ncproxy-hostkey.pem --bind 127.0.0.1 --port 8300 -v \
  --patch examples/ncproxy/patch03.json \
  netconf://192.0.2.10:830
```

## Upstream address

The last argument is the **upstream** NETCONF server (where ncproxy connects as an SSH client). Form: `netconf://<host>[:port]`. If `:port` is omitted, **830** is used. The `netconf://` prefix is optional.

| Target | Example |
|--------|---------|
| IPv4 | `netconf://192.0.2.10:830` |
| Hostname | `netconf://router.example.com` |
| IPv6 | `netconf://[2001:db8::1]:830` (brackets required, as in any URL) |

Use an address your machine can reach over SSH. The NETCONF **client** connects to ncproxy’s listen address (`--bind` / `--port`), not this upstream URL.

## Usage

```
$ ncproxy --help
usage: ncproxy [-h] [--version] [-v] [-d] [--logfile filename]
               [--serverlog filename] [--clientlog filename]
               [--patch filename] [--port tcpport] [--bind ADDR]
               [--host-key FILE]
               netconf://<hostname>[:port]

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v, --verbose         enable logging
  -d, --debug           enable ssh-lib logging
  --logfile filename    trace/debug log (default: stderr)
  --serverlog filename  server log (default: stdout)
  --clientlog filename  client log (default: stdout)
  --patch filename      patch rules JSON/YAML file
  --port tcpport        listen port (default: 830)
  --bind ADDR           bind address (default: ::)
  --host-key FILE       persistent host key file
  netconf://<hostname>[:port]
                        upstream NETCONF server
```

Example with patching and verbose logging:

```bash
ncproxy --patch examples/ncproxy/patch03.json -vvvvv netconf://192.0.2.10:830
```

Standalone script:

```bash
python src/ncproxy.py --patch examples/ncproxy/patch03.json -v netconf://192.0.2.10:830
```

## Patch rules

Rule files define `server-msg-modifier`, `client-msg-modifier`, and `auto-respond` lists. Each rule has a regex `match` and a `patch` or `response` (or `patch-file` / `response-file` for multi-line XML).

Sample files: [examples/ncproxy/](../examples/ncproxy/).

**patch01** — remove selected capabilities during `<hello>`:

```javascript
{
  "server-msg-modifier": [
    {
      "match": "<capability>urn:ietf:params:netconf:capability:writable-running:1.0</capability>",
      "patch": "<!-- writable-running removed -->"
    },
    {
      "match": "<capability>urn:ietf:params:netconf:base:1.1</capability>",
      "patch": "<!-- base:1.1 removed -->"
    }
  ],
  "client-msg-modifier": [
    {
      "match": "<capability>urn:ietf:params:netconf:base:1.1</capability>",
      "patch": "<!-- base:1.1 removed -->"
    }
  ],
  "auto-respond": []
}
```

**patch02** — replace `rpc-error` with `rpc-reply` ok:

```javascript
{
  "server-msg-modifier": [
    {
      "match": "[\\s\\S]+(message-id=\"\\d+\")[\\s\\S]+<rpc-error>[\\s\\S]+",
      "patch": "<rpc-reply \\1 xmlns=\"urn:ietf:params:xml:ns:netconf:base:1.0\"><ok/></rpc-reply>"
    }
  ],
  "client-msg-modifier": [],
  "auto-respond": []
}
```

**patch03** — auto-respond ok to `copy-config`:

```javascript
{
  "server-msg-modifier": [],
  "client-msg-modifier": [],
  "auto-respond": [
    {
      "match": "[\\s\\S]+(message-id=\"\\d+\")[\\s\\S]+<copy-config>[\\s\\S]+",
      "response": "<rpc-reply \\1 xmlns=\"urn:ietf:params:xml:ns:netconf:base:1.0\"><ok/></rpc-reply>"
    }
  ]
}
```

## Troubleshooting

| Symptom | What to check |
|--------|----------------|
| Client refuses SSH to the proxy | Use a **stable** proxy host key: `ncproxy --host-key ./ncproxy-hostkey.pem ...` (many clients reject a new key every restart). |
| Auth fails immediately | The proxy reuses the **same username/password** toward the device; wrong creds fail before NETCONF starts. |
| Only XML on the terminal | That is `--serverlog` (default stdout). Client traffic is on stderr unless you set `--clientlog`. |
| Client target | Connect to the **proxy** (`127.0.0.1` and `--port`, e.g. `8300`), not the device port `830`. |

ncproxy is a deliberate man-in-the-middle tool for labs. See the [security policy](https://github.com/nokia-steward/netconf-tools/blob/master/SECURITY.md).
