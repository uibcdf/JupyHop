"""Render CLI help from argparse without invoking a JupyHop command."""

import argparse

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from jupyhop.cli import _parser


class CLIReference(SphinxDirective):
    def run(self):
        parser = _parser()
        subcommands = next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        )
        sections = []
        for name, command in [("jupyhop", parser), *subcommands.choices.items()]:
            title = "jupyhop" if name == "jupyhop" else "jupyhop " + name
            section = nodes.section(ids=[title.replace(" ", "-")])
            section += nodes.title(text=title)
            section += nodes.literal_block(text=command.format_help(), language="text")
            self.state.document.note_explicit_target(section)
            sections.append(section)
        return sections


def setup(app):
    app.add_directive("jupyhop-cli", CLIReference)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
