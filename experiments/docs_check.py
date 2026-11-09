"""Check HTML references, CLI coverage and literal source examples offline."""

import argparse
import contextlib
import io
import json
import re
import shlex
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from jupyhop.cli import _parser
from jupyhop.config import parse_config


def check_examples(source):
    """Parse standalone fenced examples without executing a command or shell."""
    counts = {"commands": 0, "toml": 0, "json": 0}
    parser = _parser()
    commands = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    for path in sorted(source.glob("*.md")):
        markdown = path.read_text(encoding="utf-8")
        for block in re.finditer(
            r"^```(console|toml|json)[ \t]*\n(.*?)^```[ \t]*$", markdown, re.M | re.S
        ):
            language, content = block.groups()
            line = markdown.count("\n", 0, block.start()) + 1
            try:
                if language == "toml":
                    parse_config(content.encode("utf-8"))
                    counts["toml"] += 1
                elif language == "json":
                    json.loads(content)
                    counts["json"] += 1
                else:
                    for command in content.replace("\\\n", "").splitlines():
                        tokens = shlex.split(command, comments=True)
                        if not tokens or tokens[0] != "jupyhop":
                            continue
                        tokens = tokens[1:]
                        # The password example redirects one protected input file.
                        # Parse only its CLI argv, never read that file.
                        if "<" in tokens:
                            position = tokens.index("<")
                            if len(tokens) != position + 2:
                                raise ValueError
                            tokens = tokens[:position]
                        if any(token in {";", "|", "||", "&&", ">", ">>", "&"} for token in tokens):
                            raise ValueError
                        selected = commands.choices.get(tokens[0]) if tokens else None
                        flags = set(parser._option_string_actions)
                        if selected is not None:
                            flags.update(selected._option_string_actions)
                        if any(
                            token.startswith("--") and token.split("=", 1)[0] not in flags
                            for token in tokens
                        ):
                            raise ValueError
                        with (
                            contextlib.redirect_stdout(io.StringIO()),
                            contextlib.redirect_stderr(io.StringIO()),
                        ):
                            try:
                                parser.parse_args(tokens)
                            except SystemExit as error:
                                if error.code != 0:
                                    raise ValueError from None
                        counts["commands"] += 1
            except (ValueError, TypeError):
                raise ValueError(f"Invalid {language} example at {path}:{line}") from None
    if not all(counts.values()):
        raise ValueError("Expected CLI, TOML and JSON examples in the documentation source")
    return counts


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.references = []
        self.text = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("name"):
            self.ids.add(values["name"])
        self.references.extend(
            value for key, value in attributes if key in {"href", "src", "action"} and value
        )

    def handle_data(self, value):
        self.text.append(value)


def check(root):
    root = root.resolve(strict=True)
    if any(root.rglob("*.doctree")) or (root / ".doctrees").exists():
        raise ValueError("Keep Sphinx build caches outside published HTML")
    # Theme resources can include unrendered HTML/Jinja fragments. Only source
    # documents become site pages; resources are checked when pages reference them.
    pages = {
        path.resolve(): Page(path)
        for path in root.rglob("*.html")
        if path.relative_to(root).parts[0] != "_static"
    }
    required = {
        "index.html",
        "installation.html",
        "quickstart.html",
        "existing-servers.html",
        "managed-sessions.html",
        "cli.html",
    }
    if not required <= {path.name for path in pages}:
        raise ValueError("Built site is missing a required user guide")
    checked = 0
    for path, page in pages.items():
        for reference in page.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc:
                continue
            local = unquote(parsed.path)
            if local.startswith("/"):
                raise ValueError(f"Project site needs relative links: {reference}")
            target = (path.parent / local).resolve() if local else path
            if target.is_dir():
                target = target / "index.html"
            if not target.is_relative_to(root) or not target.is_file():
                raise ValueError(f"Missing site target in {path.name}: {reference}")
            if (
                parsed.fragment
                and target in pages
                and unquote(parsed.fragment) not in pages[target].ids
            ):
                raise ValueError(f"Missing site fragment in {path.name}: {reference}")
            checked += 1
    parser = _parser()
    commands = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    cli = pages[root / "cli.html"]
    text = "".join(cli.text)
    for name, command in [("jupyhop", parser), *commands.choices.items()]:
        anchor = "jupyhop" if name == "jupyhop" else "jupyhop-" + name
        if anchor not in cli.ids:
            raise ValueError("CLI reference omitted command: " + name)
        for action in command._actions:
            if any(flag not in text for flag in action.option_strings):
                raise ValueError("CLI reference omitted an option for: " + name)
    print(
        f"PASS: {len(pages)} HTML pages, {checked} local links/resources/fragments and all CLI commands/options"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source", type=Path, default=Path("docs"))
    args = parser.parse_args()
    check(args.directory)
    counts = check_examples(args.source)
    print(
        f"PASS: {counts['commands']} standalone CLI examples, {counts['toml']} TOML configs and {counts['json']} JSON examples (no commands executed)"
    )


if __name__ == "__main__":
    main()
