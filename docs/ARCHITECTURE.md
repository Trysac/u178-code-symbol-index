# Architecture

`code-symbol-index` processes Python source using the `ast` module and stores symbols in a memory-mapped dictionary for fast search.

## Core Components

- **AST Traversal**: Uses an explicit stack to walk the tree, bounded by `MAX_NESTING_DEPTH = 32` to avoid stack overflows. Symbols discovered include `class`, `function`, `async_function`, `method`, and top-level or class-level `variable` (Assignment and AnnAssignment).
- **Serialization**: `SymbolIndex` serializes the entire state (including error logs) to a stable, deterministic JSON payload via `to_json()`, ensuring reproducible indexes.
- **Ranking Engine**: Scoring is tiered:
  - Exact match (100)
  - Case-insensitive exact match (90)
  - Prefix match (80)
  - Camel/Snake abbreviation match (70)
  - Substring match (60)
  - Subsequence match (40)

## Parsing Details

- Decorators and properties are parsed by the line number of the definition. 
- Signatures are constructed via `ast.unparse`.
- Docstrings are extracted from `ast.get_docstring(clean=True)` and truncated to 120 chars.
