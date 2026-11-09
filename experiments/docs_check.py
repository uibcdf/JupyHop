"""Check built HTML links, resources and CLI coverage without network access."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from jupyhop.cli import _parser


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
    check(parser.parse_args().directory)


if __name__ == "__main__":
    main()
