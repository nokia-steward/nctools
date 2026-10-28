# netconf-tools

[![Build Status](https://github.com/nokia-steward/netconf-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/nokia-steward/netconf-tools/actions)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://nokia-steward.github.io/netconf-tools/)
[![License](https://img.shields.io/badge/license-BSD%203--Clause-blue.svg)](https://github.com/nokia-steward/netconf-tools/blob/master/LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)

Python utilities for NETCONF integration and lab troubleshooting.

---

## Tools

| Tool | Purpose |
|------|---------|
| [**ncproxy**](ncproxy.md) | Transparent NETCONF over SSH proxy (logging, patching, auto-respond) |

---

## Requirements

- **Python**: 3.8 or newer
- **Network**: SSH/NETCONF between client, ncproxy, and upstream server (see [ncproxy](ncproxy.md))
- **Python libraries**: [Paramiko](https://pypi.org/project/paramiko/) (installed with the package)

---

## Installation

**Package:**

```bash
pip install .
ncproxy --help
```

Optional extra for YAML patch rules: `pip install "netconf-tools[yaml]"`.

**From source** (minimal deps in [requirements.txt](https://github.com/nokia-steward/netconf-tools/blob/master/requirements.txt)):

```bash
pip install -r requirements.txt
python src/ncproxy.py --help
```

---

## Quick example

Lab proxy in front of a device (connect your NETCONF client to `127.0.0.1:8300`):

```bash
ncproxy --host-key ./ncproxy-hostkey.pem --bind 127.0.0.1 --port 8300 -v \
  netconf://192.0.2.10:830
```

More detail: [ncproxy guide](ncproxy.md) and [patch examples on GitHub](https://github.com/nokia-steward/netconf-tools/tree/master/examples/ncproxy).

---

## Documentation

- [ncproxy](ncproxy.md) — usage, patch rules, troubleshooting
- [Examples](https://github.com/nokia-steward/netconf-tools/tree/master/examples/ncproxy) — patch rule samples
- [Contributing](https://github.com/nokia-steward/netconf-tools/blob/master/CONTRIBUTING.md) — development setup
- [Security policy](https://github.com/nokia-steward/netconf-tools/blob/master/SECURITY.md) — reporting vulnerabilities
- [Repository README](https://github.com/nokia-steward/netconf-tools/blob/master/README.md) — overview on GitHub

---

## Features

- **Integration-focused** — Lab troubleshooting when encrypted SSH hides payload from packet capture
- **Traffic control** — Log, patch, or auto-answer NETCONF messages on the wire
- **SSH NETCONF** — Paramiko-based; base 1.0 and 1.1 framing

---

## Support

- [Report issues](https://github.com/nokia-steward/netconf-tools/issues)
- [Changelog](https://github.com/nokia-steward/netconf-tools/blob/master/CHANGELOG.md)

---

## License

BSD 3-Clause License (see [LICENSE](https://github.com/nokia-steward/netconf-tools/blob/master/LICENSE))

---

**Version**: 2.0.0 | **License**: BSD 3-Clause
