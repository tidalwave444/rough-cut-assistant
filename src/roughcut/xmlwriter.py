"""A minimal XML document builder.

Hand-rolled rather than `xml.etree` because the output is a contract with Premiere:
the renderer must reproduce a hand-verified file exactly, down to indentation and
self-closing tags, and a diff against that file is the project's strongest test.
"""

from dataclasses import dataclass, field
from xml.sax.saxutils import escape, quoteattr

INDENT = "  "


@dataclass(frozen=True)
class Element:
    tag: str
    text: str | None = None
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Element"] = field(default_factory=list)


def el(tag: str, *children: Element, **attrs: object) -> Element:
    """An element containing other elements — or, with neither, an empty one."""
    return Element(
        tag, attrs={k: str(v) for k, v in attrs.items()}, children=list(children)
    )


def leaf(tag: str, value: object) -> Element:
    """An element containing text."""
    return Element(tag, text=str(value))


def to_xml(root: Element, *, doctype: str | None = None) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    if doctype is not None:
        lines.append(f"<!DOCTYPE {doctype}>")
    _write(root, depth=0, lines=lines)
    return "\n".join(lines) + "\n"


def _write(element: Element, *, depth: int, lines: list[str]) -> None:
    pad = INDENT * depth
    attrs = "".join(f" {k}={quoteattr(v)}" for k, v in element.attrs.items())
    if element.children:
        lines.append(f"{pad}<{element.tag}{attrs}>")
        for child in element.children:
            _write(child, depth=depth + 1, lines=lines)
        lines.append(f"{pad}</{element.tag}>")
    elif element.text is not None:
        lines.append(f"{pad}<{element.tag}{attrs}>{escape(element.text)}</{element.tag}>")
    else:
        lines.append(f"{pad}<{element.tag}{attrs}/>")
