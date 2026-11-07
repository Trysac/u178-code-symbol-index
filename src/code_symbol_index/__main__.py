"""CLI interface for code_symbol_index."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from code_symbol_index import (
    IndexFormatError,
    SymbolIndex,
    SymbolIndexError,
    SymbolKind,
    build_index,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the code_symbol_index CLI."""
    parser = argparse.ArgumentParser(prog="code_symbol_index", description="Python Symbol Indexer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build subcommand
    build_parser = subparsers.add_parser("build", help="Build a symbol index")
    build_parser.add_argument("root", type=str, help="Root directory to index")
    build_parser.add_argument("-o", "--output", type=str, required=True, help="Output JSON file")

    # query subcommand
    query_parser = subparsers.add_parser("query", help="Query an index")
    query_parser.add_argument("index_file", type=str, help="Path to index JSON file")
    query_parser.add_argument("query", type=str, help="Search query string")
    query_parser.add_argument("--kind", type=str, default=None, help="Filter symbol kind")
    query_parser.add_argument("--limit", type=int, default=20, help="Maximum results (1-1000)")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code != 0 else 0

    if args.command == "build":
        root_path = Path(args.root)
        if not root_path.exists():
            sys.stderr.write(f"Error: root path does not exist: {args.root}\n")
            return 2
        try:
            idx = build_index(root_path)
            Path(args.output).write_text(idx.to_json(), encoding="utf-8")
            return 0
        except (SymbolIndexError, OSError) as e:
            sys.stderr.write(f"Error during build: {e}\n")
            return 2

    if args.command == "query":
        index_path = Path(args.index_file)
        if not index_path.is_file():
            sys.stderr.write(f"Error: index file not found: {args.index_file}\n")
            return 2
        try:
            raw = index_path.read_text(encoding="utf-8")
            idx = SymbolIndex.from_json(raw)
        except (IndexFormatError, OSError, UnicodeDecodeError) as e:
            sys.stderr.write(f"Error reading index: {e}\n")
            return 2

        kind_arg: SymbolKind | None = args.kind
        try:
            matches = idx.search(args.query, kind=kind_arg, limit=args.limit)
        except SymbolIndexError as e:
            sys.stderr.write(f"Error: {e}\n")
            return 2

        if not matches:
            return 1

        for m in matches:
            sym = m.symbol
            print(f"{sym.path}:{sym.line} {sym.kind} {sym.qualname}")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
