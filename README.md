# netconf-tools

[![Build Status](https://github.com/nokia-steward/netconf-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/nokia-steward/netconf-tools/actions)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://nokia-steward.github.io/netconf-tools/)
[![License](https://img.shields.io/badge/license-BSD%203--Clause-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)

Python utilities for NETCONF integration and lab troubleshooting.

---

## Tools

| Tool | Purpose |
|------|---------|
| [**ncproxy**](docs/ncproxy.md) | Transparent NETCONF over SSH proxy (logging, patching, auto-respond) |

---

## Requirements

- **Python**: 3.8 or newer
- **Network**: SSH/NETCONF between client, ncproxy, and upstream server (see [ncproxy](docs/ncproxy.md))
- **Python libraries**: [Paramiko](https://pypi.org/project/paramiko/) (installed with the package)

---

## Installation

**Package:**

```bash
pip install .
ncproxy --help
```

Optional extra for YAML patch rules: `pip install "netconf-tools[yaml]"`.

**From source** (minimal deps in [requirements.txt](requirements.txt)):

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

More detail: [ncproxy guide](docs/ncproxy.md) and [examples/ncproxy/](examples/ncproxy/).

---

## Documentation

- [Documentation site](https://nokia-steward.github.io/netconf-tools/) — MkDocs (Home + tool pages)
- [ncproxy](docs/ncproxy.md) — usage, patch rules, troubleshooting
- [Examples](examples/README.md) — patch rule samples
- [Contributing](CONTRIBUTING.md) — development setup and pull requests
- [Security policy](SECURITY.md) — reporting vulnerabilities

---

## Features

- **Integration-focused** — Lab troubleshooting when encrypted SSH hides payload from packet capture
- **Traffic control** — Log, patch, or auto-answer NETCONF messages on the wire
- **SSH NETCONF** — Paramiko-based; base 1.0 and 1.1 framing

---

## Support

- [Documentation](https://nokia-steward.github.io/netconf-tools/)
- [Report issues](https://github.com/nokia-steward/netconf-tools/issues)
- [Changelog](CHANGELOG.md)

---

## License

BSD 3-Clause License (see [LICENSE](LICENSE))

---

**Version**: 2.0.0 | **License**: BSD 3-Clause
