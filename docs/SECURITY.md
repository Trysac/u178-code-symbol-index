# Security notes

## Threat Model

- **Defended**: The library handles untrusted source strings via `ast.parse` and catch-all exceptions for syntax errors, preventing crashes. It uses pure functions where possible and validates query parameters (`limit` must be 1-1000; query length 1-200).
- **Not defended**: No persistent I/O security (the library reads files provided by the user). It does not sanitize the contents of docstrings or signatures beyond truncation.

## Limits

- `MAX_NESTING_DEPTH = 32`: Prevents deep recursion in pathological files.
- `MAX_FILES = 20_000` (default in `build_index`): Limits memory usage during walk.
- `MAX_FILE_BYTES = 1_000_000` (default in `build_index`): Rejects extremely large files.
