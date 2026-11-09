from unittest.mock import patch

import pytest

from experiments.docs_check import check_examples

GOOD = """# Examples

```console
jupyhop --version
jupyhop start workstation \\
    --server-python /opt/research/bin/python --password-stdin --no-open --json < /nonexistent/password
jupyhop doctor workstation --config '$(touch NEVER_EXECUTE)'
```

```toml
version = 1
[hosts."workstation.example.org"]
remote_python = "python3"
```

```json
{"complete": false, "servers": []}
```
"""


def test_examples_only_parse_without_cli_ssh_or_shell_execution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "guide.md").write_text(GOOD)
    with (
        patch("jupyhop.cli.main", side_effect=AssertionError("Must not execute CLI")),
        patch("jupyhop.ssh.SSHTransport.run", side_effect=AssertionError("Must not use SSH")),
    ):
        assert check_examples(tmp_path) == {"commands": 3, "toml": 1, "json": 1}
    assert not (tmp_path / "NEVER_EXECUTE").exists()


@pytest.mark.parametrize(
    "old,new,language",
    [
        ("--no-open", "--not-an-option", "console"),
        ("--no-open", "--no-op", "console"),
        ("--config", "--runtime-dir", "console"),
        ("--version", "--version && touch NEVER_EXECUTE", "console"),
        ("< /nonexistent/password", "< /nonexistent/password extra", "console"),
        ("version = 1", "version = 2", "toml"),
        ('remote_python = "python3"', 'password = "PRIVATE_SENTINEL"', "toml"),
        ('"servers": []', '"servers": [}', "json"),
    ],
)
def test_invalid_example_fails_with_source_location_without_raw_values(
    tmp_path, old, new, language
):
    path = tmp_path / "guide.md"
    path.write_text(GOOD.replace(old, new))
    with pytest.raises(ValueError, match=f"Invalid {language} example at .*guide.md:") as error:
        check_examples(tmp_path)
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_nonexample_fences_are_not_interpreted_as_commands(tmp_path):
    (tmp_path / "guide.md").write_text(
        GOOD + '\n```text\njupyhop doctor --unsupported "not a command"\n```\n'
    )
    assert check_examples(tmp_path) == {"commands": 3, "toml": 1, "json": 1}


def test_wrong_or_empty_source_path_is_not_a_passing_example_check(tmp_path):
    with pytest.raises(ValueError, match="Expected CLI, TOML and JSON examples"):
        check_examples(tmp_path / "missing")
