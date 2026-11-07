# code-symbol-index

Finding where a function or class is defined in a large Python repository often means grep noise or an IDE that is not available in CI, scripts, or LLM agents. Language servers are heavy to embed and their indexes are not portable files. `code-symbol-index` is a pure-library, standard-library-only indexer that builds a small, deterministic symbol index from the `ast` module, persists it as stable JSON, and answers ranked fuzzy queries.

## Installation

```bash
pip install trysac-code-symbol-index
```

## Usage

```python
from pathlib import Path
from code_symbol_index import build_index

# Build index for a directory
idx = build_index(Path("."))

# Search symbols
matches = idx.search("Repo", limit=5)
for match in matches:
    print(f"{match.symbol.path}:{match.symbol.line} {match.symbol.qualname}")
```

## API Summary

- `index_source(path: str, text: str) -> list[Symbol]`: Parses a source string into a list of symbols.
- `build_index(root: Path, ...) -> SymbolIndex`: Walks a directory tree to produce an index. Reuses previous index entries if file SHA-256 matches.
- `SymbolIndex`: Holds symbols in memory. Methods: `update_file(path, text)`, `remove_file(path)`, `search(query, kind=None, limit=20)`, `to_json()`, `from_json(text)`.
- Errors: `SymbolIndexError` (codes: `too_many_files`, `invalid_query`, `invalid_option`, `unsupported_format`) and `IndexFormatError`.

## Why not LSP or ctags?

- **Zero install**: No binary dependencies or complex setup; it uses only the Python standard library.
- **Portable**: The index is a stable JSON file that CI scripts and LLM agents can easily read and transport.
- **Agent-ready**: Ranked fuzzy search (exact, prefix, camel, substring, subsequence) is tailored for non-interactive lookup.

## Security

See [docs/SECURITY.md](docs/SECURITY.md) for the threat model and constraints.
