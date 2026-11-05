"""Tests for the command-line interface."""

from __future__ import annotations

import hashlib
import json
import runpy
import sys
from pathlib import Path

import pytest

from prompt_registry.__main__ import main

HEADER = "---\ndescription: d\nvars.name: str\nvars.n: int\n---\n"
GREET_V1 = HEADER + "Hi {{ name }} x{{n}}\n"
GREET_V2 = HEADER + "Hello {{ name }} x{{n}}\n"
TAG_LINES = [
    "---",
    "description: t",
    "vars.items: list[str]",
    "vars.flag: bool?",
    "vars.ratio: float?",
    "---",
    "{{items}}|{{flag}}|{{ratio}}",
]
TAGS = "\n".join(TAG_LINES) + "\n"


def write(root: Path, name: str, version: int, content: str | bytes) -> None:
    """Write a prompt file."""
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"v{version}.prompt.md"
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    """Run the CLI and return exit code, stdout and stderr."""
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def root(tmp_path: Path) -> str:
    write(tmp_path, "greet", 1, GREET_V1)
    return str(tmp_path)


def test_render_prints_text_and_returns_zero(root: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--root", root, "render", "greet", "--var", "name=Ana", "--var", "n=2"])
    assert code == 0
    assert capsys.readouterr().out == "Hi Ana x2\n"


def test_missing_variable_returns_one(root: str, capsys: pytest.CaptureFixture[str]) -> None:
    code, _out, err = run(capsys, "--root", root, "render", "greet", "--var", "name=Ana")
    assert code == 1
    assert "missing_variable" in err


def test_unknown_subcommand_returns_two(root: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", root, "bogus"]) == 2
    assert main(["--root", root]) == 2
    assert main(["--root", root, "show"]) == 2
    capsys.readouterr()


def test_help_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _err = run(capsys, "--help")
    assert code == 0
    assert "prompt-registry" in out


def test_list_show_and_hash(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "greet", 1, GREET_V1)
    write(tmp_path, "greet", 2, GREET_V2)
    write(tmp_path, "greet", 10, GREET_V2)
    write(tmp_path, "alpha", 1, GREET_V1)
    base = ["--root", str(tmp_path)]
    assert run(capsys, *base, "list") == (0, "alpha 1\ngreet 1 2 10\n", "")
    assert run(capsys, *base, "show", "greet") == (0, "Hello {{ name }} x{{n}}\n", "")
    assert run(capsys, *base, "show", "greet", "--version", "1") == (
        0,
        "Hi {{ name }} x{{n}}\n",
        "",
    )
    digest = hashlib.sha256(GREET_V1.encode("utf-8")).hexdigest()
    assert run(capsys, *base, "hash", "greet", "--version", "1") == (0, digest + "\n", "")
    code, _out, err = run(capsys, *base, "show", "greet", "--version", "9")
    assert code == 1
    assert "not_found" in err


def test_diff_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "greet", 1, GREET_V1)
    write(tmp_path, "greet", 2, GREET_V2)
    base = ["--root", str(tmp_path), "diff", "greet"]
    code, out, _err = run(capsys, *base, "1", "2")
    assert code == 0
    assert out.startswith("--- greet@v1\n+++ greet@v2\n")
    _code, out, _err = run(capsys, *base, "1", "2", "--context", "0")
    assert "@@ -6 +6 @@" in out
    assert run(capsys, *base, "1", "1") == (0, "", "")
    assert run(capsys, *base, "1", "3")[0] == 1
    assert run(capsys, *base, "1", "2", "--context", "-1")[0] == 2


def test_invalid_versions_are_usage_errors(root: str, capsys: pytest.CaptureFixture[str]) -> None:
    for bad in ("0", "abc", "1" * 5000):
        assert run(capsys, "--root", root, "show", "greet", "--version", bad)[0] == 2


def test_empty_and_missing_roots(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(capsys, "--root", str(tmp_path), "list") == (0, "", "")
    code, _out, err = run(capsys, "--root", str(tmp_path / "nope"), "list")
    assert code == 1
    assert "not_found" in err
    plain = tmp_path / "file.txt"
    plain.write_text("x", encoding="utf-8")
    assert run(capsys, "--root", str(plain), "list")[0] == 1


def test_unicode_body(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    body = "Ol\u00e1 \u4e16\u754c \u2603"
    write(tmp_path, "uni", 1, "---\ndescription: d\n---\n" + body + "\n")
    assert run(capsys, "--root", str(tmp_path), "show", "uni") == (0, body + "\n", "")


def test_var_errors(root: str, capsys: pytest.CaptureFixture[str]) -> None:
    base = ["--root", root, "render", "greet"]
    assert run(capsys, *base, "--var", "novalue")[0] == 2
    assert run(capsys, *base, "--var", "=x")[0] == 2
    assert run(capsys, *base, "--var", "n=1", "--var", "n=2")[0] == 2
    code, _out, err = run(capsys, *base, "--var", "name=Ana", "--var", "n=abc")
    assert code == 1
    assert "variable_type" in err
    code, _out, err = run(capsys, *base, "--var", "name=Ana", "--var", "n=2", "--var", "zzz=1")
    assert code == 1
    assert "unexpected_variable" in err
    assert run(capsys, *base, "--var", "name=Ana", "--var", "n=" + "9" * 5000)[0] == 1


def test_var_values_keep_equals_signs(root: str, capsys: pytest.CaptureFixture[str]) -> None:
    base = ["--root", root, "render", "greet", "--var", "n=-3"]
    assert run(capsys, *base, "--var", "name=a=b") == (0, "Hi a=b x-3\n", "")


def test_scalar_coercion_and_vars_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "tags", 1, TAGS)
    data = tmp_path / "vars.json"
    data.write_text(json.dumps({"items": ["a", "b"], "flag": True, "ratio": 2.5}), encoding="utf-8")
    base = ["--root", str(tmp_path), "render", "tags", "--vars-json", str(data)]
    assert run(capsys, *base) == (0, "a\nb|true|2.5\n", "")
    assert run(capsys, *base, "--var", "flag=false") == (0, "a\nb|false|2.5\n", "")
    assert run(capsys, *base, "--var", "ratio=2") == (0, "a\nb|true|2.0\n", "")
    assert run(capsys, *base, "--var", "ratio=abc")[0] == 1
    assert run(capsys, *base, "--var", "flag=maybe")[0] == 1
    assert run(capsys, *base, "--var", "items=a")[0] == 1


def test_vars_json_failures(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "tags", 1, TAGS)
    data = tmp_path / "vars.json"
    base = ["--root", str(tmp_path), "render", "tags", "--vars-json", str(data)]
    for content in (b"{", b"[]", b"[" * 100_000, b"\xff"):
        data.write_bytes(content)
        assert run(capsys, *base)[0] == 2
    assert run(capsys, *base[:-1], str(tmp_path / "missing.json"))[0] == 2
    assert run(capsys, *base[:-1], str(tmp_path))[0] == 2


def test_vars_json_size_limit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "tags", 1, TAGS)
    data = tmp_path / "vars.json"
    base = ["--root", str(tmp_path), "render", "tags", "--vars-json", str(data)]
    payload = b'{"items": ["a"]}'
    data.write_bytes(payload + b" " * (1_048_576 - len(payload)))
    assert run(capsys, *base) == (0, "a||\n", "")
    data.write_bytes(payload + b" " * (1_048_576 - len(payload) + 1))
    code, _out, err = run(capsys, *base)
    assert code == 1
    assert "too_large" in err


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_module_entry_point(
    root: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["prompt-registry", "--root", root, "list"])
    with pytest.raises(SystemExit) as info:
        runpy.run_module("prompt_registry.__main__", run_name="__main__")
    assert info.value.code == 0
    assert capsys.readouterr().out == "greet 1\n"
