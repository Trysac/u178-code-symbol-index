# Project record

## Objective

Symbol index for Python codebases built from ast: definitions with signatures, ranked fuzzy search, incremental updates by hash and a stable JSON format.

## Scope

- **In scope**: The public API documented in `README.md`, including `index_source`, `SymbolIndex` lifecycle, `build_index`, and the command-line interface.
- **Out of scope**: Cross-file references, call graphs, import resolution, support for non-Python languages, language server protocol (LSP) features, and watch modes.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

| Metric | Value |
|---|---|
| Tokens (input / output) | 328111 / 14614 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.1193 |

## Factory run u178 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4699 | 11427 | 0 | 0 | 0.0232 |
| fix-1 | gemini-3.8-flash | no | 14296 | 205 | 0 | 9994 | 0.0122 |
| fix-2 | gemini-3.8-flash | no | 14292 | 249 | 0 | 9955 | 0.0124 |
| fix-3 | gemini-3.8-flash | no | 17349 | 286 | 0 | 21475 | 0.0157 |
| audit | gemini-3.1-flash-lite | no | 38940 | 660 | 0 | 30499 | 0.0115 |
| docs | gemini-3.1-flash-lite | no | 166612 | 1787 | 0 | 0 | 0.0443 |

Total: $0.1193. Prices: Anthropic list prices.
