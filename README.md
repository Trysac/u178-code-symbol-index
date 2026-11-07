# code-symbol-index

[![PyPI version](https://img.shields.io/pypi/v/trysac-code-symbol-index)](https://pypi.org/project/trysac-code-symbol-index/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-code-symbol-index)](LICENSE)
[![CI](https://github.com/Trysac/u178-code-symbol-index/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u178-code-symbol-index/actions/workflows/ci.yml)

Symbol index for Python codebases built from ast: definitions with signatures, ranked fuzzy search, incremental updates by hash and a stable JSON format

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-code-symbol-index
# or
uv add trysac-code-symbol-index
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import code_symbol_index

# normalize() trims surrounding whitespace and lower-cases the text.
print(code_symbol_index.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    code_symbol_index.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
