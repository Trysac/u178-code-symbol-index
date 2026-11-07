# Testing

Tests are located in `tests/` and cover the public API behavior and specific edge cases.

## Files

- `tests/test_code_symbol_index.py`: Tests the `index_source` logic, `SymbolIndex` operations (CRUD), search ranking, error handling for bad syntax/decoding, and CLI functionality.

## Coverage

Tests enforce that `index_source` returns correct `Symbol` objects (including signatures/docs), `SymbolIndex` handles file updates correctly based on hashes, and searching returns appropriately ranked matches.
