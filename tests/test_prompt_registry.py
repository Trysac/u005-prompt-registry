"""Tests for the prompt registry library."""

from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path

import pytest

import prompt_registry
from prompt_registry import (
    MissingVariableError,
    PromptError,
    PromptFormatError,
    PromptNotFoundError,
    PromptVersion,
    UnexpectedVariableError,
    VariableTypeError,
    diff,
    load_registry,
    render,
)
from prompt_registry.errors import clip

HEADER = "---\ndescription: d\nvars.name: str\nvars.n: int\n---\n"
NAME_HEADER = "---\ndescription: d\nvars.name: str\n---\n"
N_HEADER = "---\ndescription: d\nvars.n: int\n---\n"
FLAT_HEADER = "---\ndescription: d\n---\n"

BAD_FILE_NAMES = ["v01.prompt.md", "v0.prompt.md", "latest.prompt.md", "v1.1.prompt.md"]

BAD_FILES = [
    b"",
    b"Hello {{ name }}\n",
    b"---\ndescription: d\n",
    b"---\ndescription d\n---\nHi\n",
    b"---\nauthor: x\n---\nHi\n",
    b"---\nvars.Bad: str\n---\nHi\n",
    b"---\nvars.: str\n---\nHi\n",
    b"---\nvars.a: dict\n---\nHi\n",
    b"---\nvars.a: str??\n---\nHi\n",
    b"---\ndescription: a\ndescription: b\n---\nHi\n",
    b"---\nvars.a: str\nvars.a: int\n---\nHi\n",
    b"---\ndescription: \xff\n---\nHi\n",
]

ADVERSARIAL = [
    ("{{name}}", "Ana"),
    ("{{ name }}", "Ana"),
    ("{{\tname\t}}", "Ana"),
    ("{{name}}{{name}}", "AnaAna"),
    ("a{{name}}b", "aAnab"),
    ("{{name}}2", "Ana2"),
    ("{{{name}}}", "{Ana}"),
    ("{{ na me }}", "{{ na me }}"),
    ("{{Name}}", "{{Name}}"),
    ("{{name", "{{name"),
    ("{name}", "{name}"),
    ("{{ 1name }}", "{{ 1name }}"),
    ("{{name-x}}", "{{name-x}}"),
    ("\\{{name}}", "{{name}}"),
    ("\\\\{{name}}", "\\{{name}}"),
    ("{{n}}0", "20"),
    ("x{{n}}.", "x2."),
]


def write(root: Path, name: str, version: int, content: str | bytes) -> Path:
    """Write a prompt file and return its path."""
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"v{version}.prompt.md"
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def load_one(root: Path, content: str | bytes) -> PromptVersion:
    """Write version 1 of prompt ``p`` and load it."""
    write(root, "p", 1, content)
    return load_registry(root).get("p")


def manual(
    variables: dict[str, prompt_registry.VarSpec] | None = None, body: str = "b"
) -> PromptVersion:
    """Build a prompt without going through the loader."""
    return PromptVersion("p", 1, "d", variables or {}, body, Path("p.md"), "h")


def make_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip the test when the platform cannot."""
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not supported here")


def test_versions_sort_numerically(tmp_path: Path) -> None:
    for version in (1, 2, 10):
        write(tmp_path, "greet", version, HEADER + "Hi\n")
    registry = load_registry(tmp_path)
    assert registry.get("greet").version == 10
    assert registry.versions("greet") == [1, 2, 10]
    assert registry.names() == ["greet"]
    assert registry.get("greet", 2).path == tmp_path / "greet" / "v2.prompt.md"


@pytest.mark.parametrize("filename", BAD_FILE_NAMES)
def test_invalid_version_file_names_raise_format(tmp_path: Path, filename: str) -> None:
    directory = tmp_path / "greet"
    directory.mkdir()
    (directory / filename).write_bytes(b"---\ndescription: d\n---\nHi\n")
    with pytest.raises(PromptError) as info:
        load_registry(tmp_path)
    assert info.value.code == "format"


def test_version_gaps(tmp_path: Path) -> None:
    write(tmp_path, "greet", 1, FLAT_HEADER + "a\n")
    write(tmp_path, "greet", 3, FLAT_HEADER + "b\n")
    registry = load_registry(tmp_path)
    assert registry.versions("greet") == [1, 3]
    assert registry.get("greet").version == 3
    with pytest.raises(PromptNotFoundError) as info:
        registry.get("greet", 2)
    assert info.value.code == "not_found"


def test_empty_registry_and_ignored_entries(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    (tmp_path / "empty" / "README.md").write_text("notes", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")
    registry = load_registry(tmp_path)
    assert registry.names() == []
    with pytest.raises(PromptNotFoundError):
        registry.get("greet")
    with pytest.raises(PromptNotFoundError):
        registry.versions("greet")


def test_names_are_sorted(tmp_path: Path) -> None:
    write(tmp_path, "zeta", 1, FLAT_HEADER + "z\n")
    write(tmp_path, "alpha", 1, FLAT_HEADER + "a\n")
    assert load_registry(str(tmp_path)).names() == ["alpha", "zeta"]


def test_invalid_directory_name_raises_format(tmp_path: Path) -> None:
    write(tmp_path, "Bad Name", 1, FLAT_HEADER + "a\n")
    with pytest.raises(PromptFormatError) as info:
        load_registry(tmp_path)
    assert info.value.path == tmp_path / "Bad Name"


def test_root_errors(tmp_path: Path) -> None:
    with pytest.raises(PromptNotFoundError):
        load_registry(tmp_path / "missing")
    plain = tmp_path / "file.txt"
    plain.write_text("x", encoding="utf-8")
    with pytest.raises(PromptError) as info:
        load_registry(plain)
    assert info.value.code == "invalid_argument"
    with pytest.raises(PromptError) as info:
        load_registry(5)  # type: ignore[arg-type]
    assert info.value.code == "invalid_argument"


INVALID_NAMES = ["Bad", "a/b", "", "x" * 65, 5]
INVALID_VERSIONS = [0, -1, True, "1", 1.5]


@pytest.mark.parametrize("name", INVALID_NAMES)
def test_invalid_names_are_rejected(tmp_path: Path, name: object) -> None:
    registry = load_registry(tmp_path)
    with pytest.raises(PromptError) as info:
        registry.get(name)  # type: ignore[arg-type]
    assert info.value.code == "invalid_argument"
    with pytest.raises(PromptError) as info:
        registry.versions(name)  # type: ignore[arg-type]
    assert info.value.code == "invalid_argument"


@pytest.mark.parametrize("version", INVALID_VERSIONS)
def test_invalid_versions_are_rejected(tmp_path: Path, version: object) -> None:
    write(tmp_path, "greet", 1, FLAT_HEADER + "a\n")
    registry = load_registry(tmp_path)
    with pytest.raises(PromptError) as info:
        registry.get("greet", version)  # type: ignore[arg-type]
    assert info.value.code == "invalid_argument"


def test_render_substitutes_once(tmp_path: Path) -> None:
    prompt = load_one(tmp_path, HEADER + "Hi {{ name }} x{{n}}\n")
    assert prompt.body == "Hi {{ name }} x{{n}}"
    assert render(prompt, {"name": "Ana", "n": 2}) == "Hi Ana x2"
    assert render(prompt, {"name": "{{n}}", "n": 2}) == "Hi {{n}} x2"


def test_escaped_braces_are_literal(tmp_path: Path) -> None:
    prompt = load_one(tmp_path, NAME_HEADER + r"\{{name}} {{name}}" + "\n")
    assert render(prompt, {"name": "Ana"}) == "{{name}} Ana"


@pytest.mark.parametrize(("body", "expected"), ADVERSARIAL)
def test_placeholder_neighbours(tmp_path: Path, body: str, expected: str) -> None:
    prompt = load_one(tmp_path, HEADER + body + "\n")
    assert render(prompt, {"name": "Ana", "n": 2}) == expected


def test_overlong_identifier_stays_literal(tmp_path: Path) -> None:
    body = "{{" + "a" * 65 + "}}"
    prompt = load_one(tmp_path, FLAT_HEADER + body + "\n")
    assert render(prompt, {}) == body


def test_pathological_input_is_handled(tmp_path: Path) -> None:
    prompt = load_one(tmp_path, FLAT_HEADER + "{{ " * 50_000 + "\n")
    assert render(prompt, {}) == prompt.body
    write(tmp_path, "q", 1, FLAT_HEADER + "{{" + " " * 200_000 + "x\n")
    assert render(load_registry(tmp_path).get("q"), {}) == "{{" + " " * 200_000 + "x"


def test_missing_unexpected_and_type_errors(tmp_path: Path) -> None:
    prompt = load_one(tmp_path, HEADER + "x\n")
    with pytest.raises(MissingVariableError) as missing:
        render(prompt, {"name": "Ana"})
    assert missing.value.code == "missing_variable"
    assert missing.value.name == "n"
    with pytest.raises(UnexpectedVariableError) as extra:
        render(prompt, {"name": "Ana", "n": 1, "z": 3})
    assert extra.value.code == "unexpected_variable"
    assert extra.value.name == "z"
    only_n = load_one(tmp_path / "other", N_HEADER + "{{n}}\n")
    with pytest.raises(VariableTypeError) as bad:
        render(only_n, {"n": True})
    assert bad.value.code == "variable_type"
    assert bad.value.expected == "int"
    assert bad.value.actual == "bool"
    assert bad.value.name == "n"


def test_undeclared_placeholder_reports_line(tmp_path: Path) -> None:
    lines = [
        "---",
        "description: d",
        "vars.a: str",
        "vars.b: str?",
        "---",
        "first {{a}}",
        "bad {{ ghost }}",
    ]
    path = write(tmp_path, "p", 1, "\n".join(lines) + "\n")
    with pytest.raises(PromptFormatError) as info:
        load_registry(tmp_path)
    assert info.value.code == "format"
    assert info.value.path == path
    assert info.value.line == 7


def test_hash_normalizes_line_endings_and_whitespace(tmp_path: Path) -> None:
    write(tmp_path / "a", "greet", 1, b"---\r\ndescription: d\r\n---\r\nHi  \r\n\r\n")
    write(tmp_path / "b", "greet", 1, b"---\ndescription: d\n---\nHi\n")
    write(tmp_path / "c", "greet", 1, b"\xef\xbb\xbf---\rdescription: d\r---\rHi\r")
    expected = hashlib.sha256(b"---\ndescription: d\n---\nHi\n").hexdigest()
    for folder in ("a", "b", "c"):
        prompt = load_registry(tmp_path / folder).get("greet")
        assert prompt.sha256 == expected
        assert prompt.body == "Hi"


def test_hash_covers_the_header(tmp_path: Path) -> None:
    write(tmp_path / "a", "p", 1, "---\nvars.n: int\n---\nHi\n")
    write(tmp_path / "b", "p", 1, "---\nvars.n: str\n---\nHi\n")
    first = load_registry(tmp_path / "a").get("p").sha256
    second = load_registry(tmp_path / "b").get("p").sha256
    assert first != second


def test_diff_output(tmp_path: Path) -> None:
    write(tmp_path, "greet", 1, HEADER + "Hi {{name}}\n")
    write(tmp_path, "greet", 2, HEADER + "Hello {{name}}\n")
    registry = load_registry(tmp_path)
    first = registry.get("greet", 1)
    second = registry.get("greet", 2)
    text = diff(first, second)
    assert text.startswith("--- greet@v1\n+++ greet@v2\n")
    assert "\n-Hi {{name}}" in text
    assert "\n+Hello {{name}}" in text
    assert not text.endswith("\n")
    assert "@@ -6 +6 @@" in diff(first, second, context=0)
    assert diff(first, first) == ""


def test_diff_rejects_bad_arguments(tmp_path: Path) -> None:
    write(tmp_path, "greet", 1, FLAT_HEADER + "a\n")
    write(tmp_path, "bye", 1, FLAT_HEADER + "a\n")
    registry = load_registry(tmp_path)
    greet = registry.get("greet")
    with pytest.raises(PromptError) as info:
        diff(greet, registry.get("bye"))
    assert info.value.code == "invalid_argument"
    for bad_context in (-1, True, "3"):
        with pytest.raises(PromptError) as info:
            diff(greet, greet, bad_context)  # type: ignore[arg-type]
        assert info.value.code == "invalid_argument"
    with pytest.raises(PromptError) as info:
        diff("x", greet)  # type: ignore[arg-type]
    assert info.value.code == "invalid_argument"


def test_diff_line_limit() -> None:
    big = PromptVersion("p", 1, "d", {}, "b", Path("p.md"), "h", "x\n" * 20_001)
    with pytest.raises(PromptError) as info:
        diff(big, manual())
    assert info.value.code == "too_large"


def test_diff_falls_back_to_body_without_text() -> None:
    text = diff(manual(body="one"), manual(body="two"))
    assert "-one" in text
    assert "+two" in text


def test_file_size_limit(tmp_path: Path) -> None:
    prefix = b"---\ndescription: d\n---\n"
    write(tmp_path, "p", 1, prefix + b"a" * (262_144 - len(prefix)))
    assert load_registry(tmp_path).get("p").version == 1
    write(tmp_path, "p", 1, prefix + b"a" * (262_144 - len(prefix) + 1))
    with pytest.raises(PromptError) as info:
        load_registry(tmp_path)
    assert info.value.code == "too_large"


def test_symlink_outside_root_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.prompt.md"
    outside.write_bytes(b"---\ndescription: d\n---\nHi\n")
    root = tmp_path / "root"
    (root / "greet").mkdir(parents=True)
    make_symlink(root / "greet" / "v1.prompt.md", outside)
    with pytest.raises(PromptError) as info:
        load_registry(root)
    assert info.value.code == "outside_root"


def test_symlinked_directory_outside_root_is_rejected(tmp_path: Path) -> None:
    write(tmp_path / "elsewhere", "greet", 1, FLAT_HEADER + "a\n")
    root = tmp_path / "root"
    root.mkdir()
    make_symlink(root / "linked", tmp_path / "elsewhere" / "greet")
    with pytest.raises(PromptError) as info:
        load_registry(root)
    assert info.value.code == "outside_root"


def test_symlink_inside_root_is_allowed(tmp_path: Path) -> None:
    write(tmp_path, "other", 1, FLAT_HEADER + "a\n")
    (tmp_path / "greet").mkdir()
    make_symlink(tmp_path / "greet" / "v1.prompt.md", tmp_path / "other" / "v1.prompt.md")
    assert load_registry(tmp_path).names() == ["greet", "other"]


def test_dangling_symlink_and_directory_are_format_errors(tmp_path: Path) -> None:
    (tmp_path / "greet").mkdir()
    make_symlink(tmp_path / "greet" / "v1.prompt.md", tmp_path / "greet" / "missing.md")
    with pytest.raises(PromptFormatError):
        load_registry(tmp_path)
    (tmp_path / "greet" / "v1.prompt.md").unlink()
    (tmp_path / "greet" / "v1.prompt.md").mkdir()
    with pytest.raises(PromptFormatError):
        load_registry(tmp_path)


def test_file_count_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("prompt_registry.loader.MAX_FILES", 2)
    for version in (1, 2, 3):
        write(tmp_path, "greet", version, FLAT_HEADER + "a\n")
    with pytest.raises(PromptError) as info:
        load_registry(tmp_path)
    assert info.value.code == "too_large"


@pytest.mark.parametrize("content", BAD_FILES)
def test_malformed_files_raise_format(tmp_path: Path, content: bytes) -> None:
    path = write(tmp_path, "p", 1, content)
    with pytest.raises(PromptFormatError) as info:
        load_registry(tmp_path)
    assert info.value.code == "format"
    assert info.value.path == path


def test_header_line_limit(tmp_path: Path) -> None:
    write(tmp_path, "p", 1, "---\n" + "\n" * 200 + "---\nbody\n")
    assert load_registry(tmp_path).get("p").body == "body"
    write(tmp_path, "p", 1, "---\n" + "\n" * 201 + "---\nbody\n")
    with pytest.raises(PromptFormatError):
        load_registry(tmp_path)


def test_header_variables_and_optional_markers(tmp_path: Path) -> None:
    lines = [
        "---",
        "description: a: b",
        "",
        "vars.x:   int?",
        "vars.y: list[str]",
        "vars.z: bool  ",
        "---",
        "{{x}}",
    ]
    prompt = load_one(tmp_path, "\n".join(lines) + "\n")
    spec = prompt_registry.VarSpec
    assert prompt.description == "a: b"
    assert dict(prompt.variables) == {
        "x": spec("int", True),
        "y": spec("list[str]", False),
        "z": spec("bool", False),
    }


def test_prompt_version_is_immutable(tmp_path: Path) -> None:
    prompt = load_one(tmp_path, HEADER + "Hi\n")
    with pytest.raises(AttributeError):
        prompt.body = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        prompt.variables["z"] = prompt_registry.VarSpec("str")  # type: ignore[index]


def test_file_without_description_or_body(tmp_path: Path) -> None:
    prompt = load_one(tmp_path, "---\nvars.a: str\n---\n")
    assert prompt.description == ""
    assert prompt.body == ""
    assert render(prompt, {"a": "x"}) == ""


def test_unicode_body(tmp_path: Path) -> None:
    body = "Ol\u00e1 \u4e16\u754c \u2603 {{name}}"
    prompt = load_one(tmp_path, NAME_HEADER + body + "\n")
    assert render(prompt, {"name": "\u00e9"}) == "Ol\u00e1 \u4e16\u754c \u2603 \u00e9"
    assert len(prompt.sha256) == 64


def test_optional_variables(tmp_path: Path) -> None:
    header = "---\ndescription: d\nvars.a: str\nvars.b: str?\n---\n"
    prompt = load_one(tmp_path, header + "[{{a}}][{{b}}]\n")
    assert render(prompt, {"a": "x"}) == "[x][]"
    assert render(prompt, {"a": "x", "b": None}) == "[x][]"
    assert render(prompt, {"a": "x", "b": "y"}) == "[x][y]"
    with pytest.raises(VariableTypeError) as info:
        render(prompt, {"a": None})
    assert info.value.actual == "NoneType"


def test_float_rendering(tmp_path: Path) -> None:
    prompt = load_one(tmp_path, "---\nvars.f: float\n---\n{{f}}\n")
    assert render(prompt, {"f": 2.5}) == "2.5"
    assert render(prompt, {"f": 0.1}) == "0.1"
    assert render(prompt, {"f": 2}) == "2.0"
    assert render(prompt, {"f": 1e22}) == "1e+22"
    with pytest.raises(VariableTypeError) as info:
        render(prompt, {"f": True})
    assert (info.value.expected, info.value.actual) == ("float", "bool")
    with pytest.raises(VariableTypeError):
        render(prompt, {"f": 10**400})
    with pytest.raises(VariableTypeError):
        render(prompt, {"f": "1.5"})


def test_bool_list_and_str_rendering(tmp_path: Path) -> None:
    header = "---\ndescription: d\nvars.flag: bool\nvars.items: list[str]\nvars.s: str\n---\n"
    prompt = load_one(tmp_path, header + "{{flag}}|{{items}}|{{s}}\n")
    assert render(prompt, {"flag": True, "items": ["a", "b"], "s": "x"}) == "true|a\nb|x"
    assert render(prompt, {"flag": False, "items": (), "s": ""}) == "false||"
    assert render(prompt, {"flag": False, "items": ("a",), "s": "x"}) == "false|a|x"
    for bad_flag, actual in (("yes", "str"), (1, "int"), (None, "NoneType")):
        with pytest.raises(VariableTypeError) as info:
            render(prompt, {"flag": bad_flag, "items": [], "s": ""})
        assert info.value.actual == actual
    with pytest.raises(VariableTypeError) as info:
        render(prompt, {"flag": True, "items": ["a", 1], "s": ""})
    assert info.value.actual == "list[int]"
    with pytest.raises(VariableTypeError) as info:
        render(prompt, {"flag": True, "items": "abc", "s": ""})
    assert info.value.actual == "str"
    with pytest.raises(VariableTypeError) as info:
        render(prompt, {"flag": True, "items": [], "s": 3})
    assert (info.value.expected, info.value.actual) == ("str", "int")


@pytest.mark.skipif(not hasattr(sys, "set_int_max_str_digits"), reason="needs int digit limit")
def test_oversized_int_is_a_type_error(tmp_path: Path) -> None:
    prompt = load_one(tmp_path, N_HEADER + "{{n}}\n")
    previous = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(640)
    try:
        with pytest.raises(VariableTypeError):
            render(prompt, {"n": 10**1000})
    finally:
        sys.set_int_max_str_digits(previous)


def test_render_argument_validation(tmp_path: Path) -> None:
    prompt = load_one(tmp_path, NAME_HEADER + "{{name}}\n")
    with pytest.raises(PromptError) as info:
        render("x", {})  # type: ignore[arg-type]
    assert info.value.code == "invalid_argument"
    with pytest.raises(PromptError) as info:
        render(prompt, [1])  # type: ignore[arg-type]
    assert info.value.code == "invalid_argument"
    with pytest.raises(PromptError) as info:
        render(prompt, {1: "a"})  # type: ignore[dict-item]
    assert info.value.code == "invalid_argument"


def test_render_output_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompt = load_one(tmp_path, NAME_HEADER + "{{name}}\n")
    monkeypatch.setattr("prompt_registry.render.MAX_RENDERED_CHARS", 10)
    assert render(prompt, {"name": "x" * 10}) == "x" * 10
    with pytest.raises(PromptError) as info:
        render(prompt, {"name": "x" * 11})
    assert info.value.code == "too_large"


def test_render_rejects_undeclared_placeholder_in_manual_prompt() -> None:
    prompt = manual({"a": prompt_registry.VarSpec("str")}, "{{ghost}}")
    with pytest.raises(PromptFormatError):
        render(prompt, {"a": "x"})


def test_error_types_and_codes() -> None:
    assert PromptError("x").code == "invalid_argument"
    assert PromptError("x", "too_large").code == "too_large"
    assert PromptNotFoundError("x").code == "not_found"
    error = PromptFormatError("bad", Path("f.md"), 3)
    assert (error.code, error.path, error.line, str(error)) == (
        "format",
        Path("f.md"),
        3,
        "bad (line 3)",
    )
    plain = PromptFormatError("bad")
    assert (plain.path, plain.line, str(plain)) == (None, None, "bad")
    typed = VariableTypeError("n", "int", "bool")
    assert (typed.code, typed.name, typed.expected, typed.actual) == (
        "variable_type",
        "n",
        "int",
        "bool",
    )
    for subclass in (
        PromptNotFoundError,
        PromptFormatError,
        MissingVariableError,
        UnexpectedVariableError,
        VariableTypeError,
    ):
        assert issubclass(subclass, PromptError)


def test_error_messages_are_bounded() -> None:
    assert len(str(PromptError("y" * 500))) == 200
    long_name = "z" * 1000
    error = UnexpectedVariableError(long_name)
    assert len(str(error)) <= 200
    assert error.name == long_name
    assert len(str(MissingVariableError(long_name))) <= 200
    assert len(str(VariableTypeError(long_name, long_name, long_name))) <= 200
    assert clip("a\nb") == "a?b"
    assert clip("abcdef", 3) == "abc..."


def test_logging_is_not_configured_and_never_logs_text(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    handlers = logging.getLogger("prompt_registry").handlers
    assert any(isinstance(handler, logging.NullHandler) for handler in handlers)
    write(tmp_path, "greet", 1, HEADER + "confidential body text\n")
    with caplog.at_level(logging.DEBUG, logger="prompt_registry"):
        load_registry(tmp_path)
    assert caplog.records
    assert all("confidential" not in record.getMessage() for record in caplog.records)


def test_version_is_exported() -> None:
    assert prompt_registry.__version__ == "0.1.0"
    assert "load_registry" in prompt_registry.__all__
