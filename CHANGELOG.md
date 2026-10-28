# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-10-27

### Added

- **project:** `netconf-tools` packaging (`src/ncproxy.py`), Makefile, containers, CI/CD, MkDocs docs.
- **ncproxy:** Python 3 rewrite (bytes-safe framing, `Rules` / `ProxyConfig`, embeddable `ProxyServer`, `--bind`, `--host-key`, YAML rules, auth failure propagation to clients, `re.DOTALL` rule matching).

### Changed

- **ncproxy:** Version 2.0.0; module layout under `src/`; patch samples under `examples/ncproxy/`.

### Historical (pre-2.0.0, monolithic `ncproxy.py`)

- **1.3** — propagate auth errors to client; fix regexp (`re.DOTALL`).
- **1.2** — patch-file support.
- **1.1** — logging, patching, auto-responses.
- **1.0** — initial NETCONF over SSH proxy.
