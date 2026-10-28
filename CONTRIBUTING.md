# Contributing

## Who needs what

| Goal | Setup |
|------|--------|
| Run the package | `pip install -r requirements.txt` or `pip install .` (see README) |
| Change code or docs | Python 3.8+, [uv](https://docs.astral.sh/uv/getting-started/installation/), then below |

## Developer workflow

```bash
make install
uv run pre-commit install   # optional: run checks on each git commit
make check                  # required before a PR (CI also runs packaging build)
```

Before opening a PR, run **`make check`**. CI also runs **`make build`** (packaging smoke test).

Pre-commit is **recommended**, not required: it mirrors `make lint` plus trailing-whitespace and EOF fixes. Install it once with `uv run pre-commit install` after `make install`. CI does not run pre-commit; it runs Ruff and pytest directly.

Note user-visible changes in `CHANGELOG.md` under `[Unreleased]`.

Published docs: [README](../README.md) and [docs/](.) on push to `master` (GitHub Pages).
