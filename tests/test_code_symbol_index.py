"""Unit tests for code_symbol_index."""

from __future__ import annotations

from pathlib import Path

import pytest

from code_symbol_index import (
    IndexFormatError,
    SymbolIndex,
    SymbolIndexError,
    build_index,
    index_source,
)
from code_symbol_index.__main__ import main


def test_acceptance_item_1() -> None:
    # index_source('m.py', ...) returns Repo and Repo.get_file_name
    src = 'class Repo:\n    def get_file_name(self, p: str) -> str:\n        "Return name."\n'
    symbols = index_source("m.py", src)
    assert len(symbols) == 2

    repo = symbols[0]
    assert repo.name == "Repo"
    assert repo.kind == "class"
    assert repo.line == 1
    assert repo.signature is None
    assert repo.doc is None

    fn = symbols[1]
    assert fn.name == "get_file_name"
    assert fn.qualname == "Repo.get_file_name"
    assert fn.kind == "method"
    assert fn.line == 2
    assert fn.signature == "def get_file_name(self, p: str) -> str"
    assert fn.doc == "Return name."


def test_acceptance_item_2() -> None:
    # 'async def f(): pass' gives kind 'async_function'
    src1 = "async def f(): pass"
    syms1 = index_source("f.py", src1)
    assert len(syms1) == 1
    assert syms1[0].name == "f"
    assert syms1[0].kind == "async_function"
    assert syms1[0].signature == "async def f()"

    # module-level 'X: int = 1', 'a = b = 2' and 'c, d = 1, 2' give variables
    # while 'x.y = 3' gives none
    src2 = "X: int = 1\na = b = 2\nc, d = 1, 2\nx.y = 3\n"
    syms2 = index_source("vars.py", src2)
    names = [s.name for s in syms2]
    assert names == ["X", "a", "b", "c", "d"]
    assert all(s.kind == "variable" for s in syms2)

    # function nested in a function has qualname 'outer.inner' and kind 'function'
    src3 = "def outer():\n    def inner():\n        pass\n"
    syms3 = index_source("nested.py", src3)
    assert len(syms3) == 2
    assert syms3[1].name == "inner"
    assert syms3[1].qualname == "outer.inner"
    assert syms3[1].kind == "function"


def test_acceptance_item_3() -> None:
    # With symbols get_file_name, GetFileName, file_name_get and filename indexed,
    # search('gfn') returns get_file_name and GetFileName with reason 'camel' and score 70,
    # and search('file_name') returns file_name_get (reason 'prefix', score 80) before get_file_name (reason 'substring', score 60)
    src = (
        "def get_file_name(): pass\n"
        "class GetFileName: pass\n"
        "def file_name_get(): pass\n"
        "def filename(): pass\n"
    )
    idx = SymbolIndex()
    idx.update_file("symbols.py", src)

    res_camel = idx.search("gfn")
    assert len(res_camel) == 2
    assert {m.symbol.name for m in res_camel} == {"get_file_name", "GetFileName"}
    for m in res_camel:
        assert m.reason == "camel"
        assert m.score == 70

    res_fn = idx.search("file_name")
    # file_name_get has prefix (80), get_file_name has substring (60)
    names_res = [m.symbol.name for m in res_fn]
    assert "file_name_get" in names_res
    assert "get_file_name" in names_res
    idx_fng = names_res.index("file_name_get")
    idx_gfn = names_res.index("get_file_name")
    assert idx_fng < idx_gfn
    assert res_fn[idx_fng].reason == "prefix"
    assert res_fn[idx_fng].score == 80
    assert res_fn[idx_gfn].reason == "substring"
    assert res_fn[idx_gfn].score == 60


def test_acceptance_item_4() -> None:
    # search('Repo') returns reason 'exact' score 100 first; search('repo') gives reason 'exact_ci' score 90;
    # results tie-break by shorter qualname, then path, then line; search('x', kind='method') returns only methods
    src = (
        "class Repo: pass\n"
        "class RepoExtension:\n"
        "    def repo(self): pass\n"
        "    def x(self): pass\n"
        "def x(): pass\n"
    )
    idx = SymbolIndex()
    idx.update_file("a.py", src)

    # search('Repo')
    res = idx.search("Repo")
    assert res[0].symbol.name == "Repo"
    assert res[0].reason == "exact"
    assert res[0].score == 100

    # search('repo') gives exact_ci
    res_ci = idx.search("repo")
    exact_ci_matches = [m for m in res_ci if m.reason == "exact_ci"]
    assert len(exact_ci_matches) >= 1
    assert any(m.symbol.name == "Repo" and m.score == 90 for m in exact_ci_matches)

    # search('x', kind='method')
    res_methods = idx.search("x", kind="method")
    assert len(res_methods) == 1
    assert res_methods[0].symbol.kind == "method"
    assert res_methods[0].symbol.qualname == "RepoExtension.x"

    # Tie-breaking test: shorter qualname, then path, then line
    src_tb = "def target(): pass\n"
    src_tb2 = "class C:\n    def target(self): pass\n"
    idx2 = SymbolIndex()
    idx2.update_file("z.py", src_tb)  # qualname 'target'
    idx2.update_file("a.py", src_tb2)  # qualname 'C.target'
    res_tb = idx2.search("target")
    assert res_tb[0].symbol.qualname == "target"
    assert res_tb[1].symbol.qualname == "C.target"


def test_acceptance_item_5() -> None:
    # A file 'bad.py' containing 'def (' is skipped with index.errors == {'bad.py': 'syntax_error at line 1'}
    # while other files are indexed; undecodable bytes give 'decode_error'
    idx = SymbolIndex()
    idx.update_file("bad.py", "def (")
    idx.update_file("good.py", "def ok(): pass")
    assert idx.errors == {"bad.py": "syntax_error at line 1"}
    assert "good.py" in idx._files


def test_acceptance_item_6() -> None:
    # update_file('m.py', same_text) returns False without reparsing,
    # update_file with changed text returns True and replaces every symbol of that path,
    # and remove_file('m.py') removes them
    idx = SymbolIndex()
    txt1 = "def alpha(): pass"
    txt2 = "def beta(): pass"
    assert idx.update_file("m.py", txt1) is True
    assert idx.update_file("m.py", txt1) is False
    assert len(idx.search("alpha")) == 1

    assert idx.update_file("m.py", txt2) is True
    assert len(idx.search("alpha")) == 0
    assert len(idx.search("beta")) == 1

    idx.remove_file("m.py")
    assert len(idx.search("beta")) == 0
    assert "m.py" not in idx._files


def test_acceptance_item_7() -> None:
    # SymbolIndex.from_json(idx.to_json()).to_json() == idx.to_json() byte for byte,
    # the JSON contains '"format":"code-symbol-index/1"',
    # and from_json('{"format":"other"}') raises IndexFormatError with code 'unsupported_format'
    idx = SymbolIndex()
    idx.update_file("sample.py", "def fn(a: int) -> str:\n    'docstring'\n    pass\n")
    serialized = idx.to_json()
    assert '"format":"code-symbol-index/1"' in serialized
    idx2 = SymbolIndex.from_json(serialized)
    assert idx2.to_json() == serialized

    with pytest.raises(IndexFormatError) as exc_info:
        SymbolIndex.from_json('{"format":"other"}')
    assert exc_info.value.code == "unsupported_format"

    with pytest.raises(IndexFormatError) as exc_invalid_json:
        SymbolIndex.from_json("not json")
    assert exc_invalid_json.value.code == "unsupported_format"


def test_acceptance_item_8(tmp_path: Path) -> None:
    # build_index(root) over a tree with '.git/x.py', 'node_modules/y.py', '.venv/z.py' and 'pkg/a.py' indexes only 'pkg/a.py' (posix path);
    # a 1_000_001-byte file is recorded with error 'too_large' while 1_000_000 bytes is indexed
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "x.py").write_text("def x(): pass", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "y.py").write_text("def y(): pass", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "z.py").write_text("def z(): pass", encoding="utf-8")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("def a(): pass", encoding="utf-8")

    idx = build_index(tmp_path)
    assert list(idx._files.keys()) == ["pkg/a.py"]

    # Size limits test
    (tmp_path / "large.py").write_bytes(b"#" * 1_000_001)
    (tmp_path / "limit.py").write_bytes(b"#" * 1_000_000)
    idx_size = build_index(tmp_path)
    assert idx_size.errors.get("large.py") == "too_large"
    assert "large.py" not in idx_size._files
    assert "limit.py" in idx_size._files


def test_acceptance_item_9(tmp_path: Path) -> None:
    # build_index(root, max_files=2) over three .py files raises SymbolIndexError with code 'too_many_files';
    # search with a 201-character query raises code 'invalid_query'; limit=0 raises code 'invalid_option'
    (tmp_path / "f1.py").write_text("x = 1")
    (tmp_path / "f2.py").write_text("x = 2")
    (tmp_path / "f3.py").write_text("x = 3")

    with pytest.raises(SymbolIndexError) as exc_too_many:
        build_index(tmp_path, max_files=2)
    assert exc_too_many.value.code == "too_many_files"

    idx = SymbolIndex()
    with pytest.raises(SymbolIndexError) as exc_invalid_q:
        idx.search("a" * 201)
    assert exc_invalid_q.value.code == "invalid_query"

    with pytest.raises(SymbolIndexError) as exc_empty_q:
        idx.search("")
    assert exc_empty_q.value.code == "invalid_query"

    with pytest.raises(SymbolIndexError) as exc_invalid_limit:
        idx.search("x", limit=0)
    assert exc_invalid_limit.value.code == "invalid_option"

    with pytest.raises(SymbolIndexError) as exc_invalid_limit2:
        idx.search("x", limit=1001)
    assert exc_invalid_limit2.value.code == "invalid_option"

    with pytest.raises(SymbolIndexError) as exc_invalid_kind:
        idx.search("x", kind="not_a_kind")  # type: ignore[arg-type]
    assert exc_invalid_kind.value.code == "invalid_option"


def test_acceptance_item_10(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # CLI: main(['build', 'ROOT', '-o', 'index.json']) returns 0;
    # main(['query', 'index.json', 'gfn', '--kind', 'method']) prints 'pkg/a.py:2 method Repo.get_file_name' and returns 0,
    # returns 1 when nothing matches, and returns 2 for an unreadable or invalid index
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "a.py").write_text(
        'class Repo:\n    def get_file_name(self, p: str) -> str:\n        "Return name."\n',
        encoding="utf-8",
    )
    index_file = tmp_path / "index.json"

    # build
    assert main(["build", str(tmp_path), "-o", str(index_file)]) == 0
    assert index_file.is_file()

    # query found
    capsys.readouterr()
    ret = main(["query", str(index_file), "gfn", "--kind", "method"])
    out = capsys.readouterr().out.strip()
    assert ret == 0
    assert out == "pkg/a.py:2 method Repo.get_file_name"

    # query nothing matches
    assert main(["query", str(index_file), "nonexistent"]) == 1

    # query invalid / unreadable index
    invalid_index = tmp_path / "invalid.json"
    invalid_index.write_text("not json")
    assert main(["query", str(invalid_index), "gfn"]) == 2
    assert main(["query", str(tmp_path / "no_such_file.json"), "gfn"]) == 2


def test_subsequence_scoring() -> None:
    idx = SymbolIndex()
    idx.update_file("t.py", "def calculate_symbol_index(): pass")
    res = idx.search("csndx")
    assert len(res) == 1
    assert res[0].reason == "subsequence"
    assert res[0].score == 40


def test_caching_and_previous_reuse(tmp_path: Path) -> None:
    (tmp_path / "file1.py").write_text("def func1(): pass", encoding="utf-8")
    idx1 = build_index(tmp_path)
    assert "file1.py" in idx1._files

    # Rebuild with previous
    idx2 = build_index(tmp_path, previous=idx1)
    assert idx2._files["file1.py"] == idx1._files["file1.py"]


def test_undecodable_bytes_error(tmp_path: Path) -> None:
    (tmp_path / "bad_utf8.py").write_bytes(b"\xff\xfe invalid utf")
    idx = build_index(tmp_path)
    assert idx.errors.get("bad_utf8.py") == "decode_error"


def test_class_inheritance_signature() -> None:
    src = "class Derived(Base, Mixin): pass"
    syms = index_source("inherit.py", src)
    assert len(syms) == 1
    assert syms[0].signature == "class Derived(Base, Mixin)"


def test_class_level_variables() -> None:
    src = "class Config:\n    TIMEOUT: int = 10\n    NAME = 'app'\n"
    syms = index_source("cfg.py", src)
    names = [s.name for s in syms]
    assert "Config" in names
    assert "TIMEOUT" in names
    assert "NAME" in names
    v_timeout = next(s for s in syms if s.name == "TIMEOUT")
    assert v_timeout.qualname == "Config.TIMEOUT"
    assert v_timeout.kind == "variable"


def test_max_nesting_depth() -> None:
    # Generate deep nesting
    indent = ""
    lines = []
    for i in range(35):
        lines.append(f"{indent}def f{i}():")
        indent += "    "
    lines.append(f"{indent}pass")
    src = "\n".join(lines)
    syms = index_source("deep.py", src)
    # Symbols beyond depth 32 are ignored
    assert any(s.name == "f32" for s in syms)
    assert not any(s.name == "f33" for s in syms)


def test_cli_errors(tmp_path: Path) -> None:
    assert main(["build", str(tmp_path / "missing"), "-o", str(tmp_path / "out.json")]) == 2
    # CLI argument error
    assert main(["invalid_cmd"]) == 2
