"""Symbol index for Python codebases built from ast."""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "IndexFormatError",
    "Match",
    "MatchReason",
    "Symbol",
    "SymbolIndex",
    "SymbolIndexError",
    "SymbolKind",
    "__version__",
    "build_index",
    "index_source",
]

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

SymbolKind = Literal["function", "async_function", "class", "method", "variable"]
MatchReason = Literal["exact", "exact_ci", "prefix", "camel", "substring", "subsequence"]

CURRENT_FORMAT = "code-symbol-index/1"
MAX_NESTING_DEPTH = 32


class SymbolIndexError(Exception):
    """Base exception for symbol indexing operations."""

    def __init__(
        self,
        message: str,
        code: Literal["too_many_files", "invalid_query", "invalid_option", "unsupported_format"],
    ) -> None:
        super().__init__(message)
        self.code = code


class IndexFormatError(SymbolIndexError):
    """Raised when the serialized index format is invalid or unsupported."""


@dataclass(frozen=True)
class Symbol:
    """Represents a discovered symbol definition."""

    name: str
    qualname: str
    kind: SymbolKind
    path: str
    line: int
    end_line: int
    signature: str | None
    doc: str | None


@dataclass(frozen=True)
class Match:
    """A search match with ranking information."""

    symbol: Symbol
    score: int
    reason: MatchReason


def _extract_target_names(target: ast.AST) -> list[str]:
    names: list[str] = []
    if isinstance(target, ast.Name):
        names.append(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            names.extend(_extract_target_names(elt))
    return names


def _make_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
    args_str = ast.unparse(node.args)
    ret_str = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix}{node.name}({args_str}){ret_str}"


def _make_class_signature(node: ast.ClassDef) -> str | None:
    if not node.bases:
        return None
    bases_str = ", ".join(ast.unparse(b) for b in node.bases)
    return f"class {node.name}({bases_str})"


def _extract_doc(
    node: ast.AsyncFunctionDef | ast.FunctionDef | ast.ClassDef | ast.Module,
) -> str | None:
    doc = ast.get_docstring(node, clean=True)
    if doc is None:
        return None
    first_line = doc.splitlines()[0] if doc.splitlines() else ""
    return first_line[:120]


def index_source(path: str, text: str) -> list[Symbol]:
    """Parse a Python source string and return discovered symbols."""
    posix_path = Path(path).as_posix()
    root = ast.parse(text, filename=path)

    symbols: list[Symbol] = []

    # Walk the tree with an explicit stack to maintain qualnames, parent kinds and depth.
    # Stack item: (node, parent_qualname, parent_is_class, depth)
    stack: list[tuple[ast.AST, str, bool, int]] = [(root, "", False, 0)]

    while stack:
        current_node, parent_qualname, parent_is_class, depth = stack.pop()

        if depth > MAX_NESTING_DEPTH:
            continue

        for child in ast.iter_child_nodes(current_node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qname = f"{parent_qualname}.{child.name}" if parent_qualname else child.name
                if parent_is_class:
                    kind: SymbolKind = "method"
                elif isinstance(child, ast.AsyncFunctionDef):
                    kind = "async_function"
                else:
                    kind = "function"

                end_line = getattr(child, "end_lineno", child.lineno) or child.lineno
                symbols.append(
                    Symbol(
                        name=child.name,
                        qualname=qname,
                        kind=kind,
                        path=posix_path,
                        line=child.lineno,
                        end_line=end_line,
                        signature=_make_function_signature(child),
                        doc=_extract_doc(child),
                    )
                )
                stack.append((child, qname, False, depth + 1))

            elif isinstance(child, ast.ClassDef):
                qname = f"{parent_qualname}.{child.name}" if parent_qualname else child.name
                end_line = getattr(child, "end_lineno", child.lineno) or child.lineno
                symbols.append(
                    Symbol(
                        name=child.name,
                        qualname=qname,
                        kind="class",
                        path=posix_path,
                        line=child.lineno,
                        end_line=end_line,
                        signature=_make_class_signature(child),
                        doc=_extract_doc(child),
                    )
                )
                stack.append((child, qname, True, depth + 1))

            elif depth == 0 or parent_is_class:
                # Variables are Name targets of module-level and class-level Assign and AnnAssign
                if isinstance(child, ast.Assign):
                    for t in child.targets:
                        for var_name in _extract_target_names(t):
                            qname = f"{parent_qualname}.{var_name}" if parent_qualname else var_name
                            end_line = getattr(child, "end_lineno", child.lineno) or child.lineno
                            symbols.append(
                                Symbol(
                                    name=var_name,
                                    qualname=qname,
                                    kind="variable",
                                    path=posix_path,
                                    line=child.lineno,
                                    end_line=end_line,
                                    signature=None,
                                    doc=None,
                                )
                            )
                elif isinstance(child, ast.AnnAssign):
                    for var_name in _extract_target_names(child.target):
                        qname = f"{parent_qualname}.{var_name}" if parent_qualname else var_name
                        end_line = getattr(child, "end_lineno", child.lineno) or child.lineno
                        symbols.append(
                            Symbol(
                                name=var_name,
                                qualname=qname,
                                kind="variable",
                                path=posix_path,
                                line=child.lineno,
                                end_line=end_line,
                                signature=None,
                                doc=None,
                            )
                        )

    # Sort symbols deterministically by line number then qualname
    symbols.sort(key=lambda s: (s.line, s.qualname))
    return symbols


def _split_words(name: str) -> list[str]:
    """Extract words from snake_case or CamelCase identifiers."""
    parts: list[str] = []
    for chunk in name.split("_"):
        if not chunk:
            continue
        current: list[str] = []
        for char in chunk:
            if char.isupper() and current and not current[-1].isupper():
                parts.append("".join(current))
                current = [char]
            else:
                current.append(char)
        if current:
            parts.append("".join(current))
    return parts


def _camel_initials(name: str) -> str:
    words = _split_words(name)
    return "".join(w[0] for w in words if w).lower()


def _is_subsequence(sub: str, text: str) -> bool:
    if not sub:
        return True
    it = iter(text)
    return all(char in it for char in sub)


class SymbolIndex:
    """In-memory index of symbols across multiple files."""

    def __init__(self) -> None:
        # Map posix_path -> list of symbols
        self._files: dict[str, list[Symbol]] = {}
        # Map posix_path -> sha256 hex
        self._hashes: dict[str, str] = {}
        # Map posix_path -> error message
        self.errors: dict[str, str] = {}

    def update_file(self, path: str, text: str) -> bool:
        """Update symbols for path if content changed. Returns True if reparsed."""
        posix_path = Path(path).as_posix()
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if self._hashes.get(posix_path) == digest and posix_path not in self.errors:
            return False

        self.remove_file(posix_path)
        self._hashes[posix_path] = digest

        try:
            symbols = index_source(posix_path, text)
            self._files[posix_path] = symbols
            return True
        except SyntaxError as e:
            line = e.lineno if e.lineno is not None else 1
            self.errors[posix_path] = f"syntax_error at line {line}"
            return True
        except (RecursionError, MemoryError):
            self.errors[posix_path] = "parse_failed"
            return True

    def remove_file(self, path: str) -> None:
        """Remove all symbols and error entries for the given file path."""
        posix_path = Path(path).as_posix()
        self._files.pop(posix_path, None)
        self._hashes.pop(posix_path, None)
        self.errors.pop(posix_path, None)

    def search(
        self,
        query: str,
        *,
        kind: SymbolKind | None = None,
        limit: int = 20,
    ) -> list[Match]:
        """Search indexed symbols with ranking."""
        if not query or len(query) > 200:
            raise SymbolIndexError("query length must be between 1 and 200", "invalid_query")
        if limit < 1 or limit > 1000:
            raise SymbolIndexError("limit must be between 1 and 1000", "invalid_option")

        valid_kinds = {"function", "async_function", "class", "method", "variable"}
        if kind is not None and kind not in valid_kinds:
            raise SymbolIndexError(f"invalid kind filter: {kind}", "invalid_option")

        matches: list[Match] = []
        query_lower = query.lower()

        for symbols in self._files.values():
            for sym in symbols:
                if kind is not None and sym.kind != kind:
                    continue

                name = sym.name
                name_lower = name.lower()

                score: int
                reason: MatchReason

                if name == query:
                    score = 100
                    reason = "exact"
                elif name_lower == query_lower:
                    score = 90
                    reason = "exact_ci"
                elif name_lower.startswith(query_lower):
                    score = 80
                    reason = "prefix"
                elif _camel_initials(name) == query_lower:
                    score = 70
                    reason = "camel"
                elif query_lower in name_lower:
                    score = 60
                    reason = "substring"
                elif _is_subsequence(query_lower, name_lower):
                    score = 40
                    reason = "subsequence"
                else:
                    continue

                matches.append(Match(symbol=sym, score=score, reason=reason))

        # Sort: descending score, ascending len(qualname), ascending path, ascending line
        matches.sort(key=lambda m: (-m.score, len(m.symbol.qualname), m.symbol.path, m.symbol.line))
        return matches[:limit]

    def to_json(self) -> str:
        """Serialize index to stable deterministic JSON."""
        files_dict: dict[str, dict[str, Any]] = {}
        for path in sorted(self._files.keys()):
            files_dict[path] = {
                "sha256": self._hashes[path],
                "symbols": [asdict(sym) for sym in self._files[path]],
            }

        payload = {
            "errors": self.errors,
            "files": files_dict,
            "format": CURRENT_FORMAT,
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> SymbolIndex:
        """Deserialize index from JSON string."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise IndexFormatError(f"invalid json: {e}", "unsupported_format") from e

        if not isinstance(data, dict) or data.get("format") != CURRENT_FORMAT:
            fmt = data.get("format") if isinstance(data, dict) else None
            raise IndexFormatError(
                f"unsupported format version: {fmt}",
                "unsupported_format",
            )

        idx = cls()
        idx.errors = dict(data.get("errors", {}))
        for path, file_info in data.get("files", {}).items():
            idx._hashes[path] = file_info["sha256"]
            idx._files[path] = [Symbol(**s) for s in file_info["symbols"]]
        return idx


def build_index(
    root: Path,
    *,
    previous: SymbolIndex | None = None,
    max_files: int = 20_000,
    max_file_bytes: int = 1_000_000,
    exclude_dirs: Sequence[str] = (
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "build",
        "dist",
    ),
) -> SymbolIndex:
    """Walk a directory tree, discover Python files and build a SymbolIndex."""
    idx = SymbolIndex()
    exclude_set = set(exclude_dirs)

    py_files: list[tuple[Path, str]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Filter exclude dirs in-place
        dirnames[:] = sorted(d for d in dirnames if d not in exclude_set)
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                full_path = Path(dirpath) / filename
                rel_posix = full_path.relative_to(root).as_posix()
                py_files.append((full_path, rel_posix))

    py_files.sort(key=lambda item: item[1])

    if len(py_files) > max_files:
        raise SymbolIndexError(
            f"file count {len(py_files)} exceeds max_files={max_files}", "too_many_files"
        )

    for full_path, rel_posix in py_files:
        try:
            st = full_path.stat()
            if st.st_size > max_file_bytes:
                idx.errors[rel_posix] = "too_large"
                continue
            raw_bytes = full_path.read_bytes()
        except OSError as e:
            idx.errors[rel_posix] = f"io_error: {e}"
            continue

        if len(raw_bytes) > max_file_bytes:
            idx.errors[rel_posix] = "too_large"
            continue

        digest = hashlib.sha256(raw_bytes).hexdigest()

        # Re-use previous entry if matching SHA-256
        if (
            previous is not None
            and rel_posix in previous._files
            and previous._hashes.get(rel_posix) == digest
        ):
            idx._files[rel_posix] = list(previous._files[rel_posix])
            idx._hashes[rel_posix] = digest
            continue

        try:
            text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            idx.errors[rel_posix] = "decode_error"
            continue

        idx.update_file(rel_posix, text)

    return idx
