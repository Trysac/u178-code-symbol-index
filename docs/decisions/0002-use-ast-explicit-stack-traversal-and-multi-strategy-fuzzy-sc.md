# Use AST Explicit Stack Traversal and Multi-Strategy Fuzzy Scoring

Status: accepted (generated, pending human review)

## Context

We need a zero-dependency Python code indexing library capable of extracting classes, functions, methods and variables with signatures and docstrings, supporting incremental updates and fast multi-strategy search.

## Decision

We use Python's standard `ast` module with an explicit stack bounded to 32 levels of nesting to parse code safely without recursion limit issues. Search matches are scored with prioritized tiers: exact (100), exact_ci (90), prefix (80), camel abbreviation (70), substring (60) and subsequence (40), with deterministic tie-breaking. Serialization produces stable, sorted JSON identified by format 'code-symbol-index/1'.

## Consequences

Zero external dependencies are required. Incremental rebuilds re-use matching SHA-256 entries. Per-file issues do not abort full repository indexing.
