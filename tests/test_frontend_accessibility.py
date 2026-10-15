from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

HTML = Path("dist/index.html")
CSS = Path("dist/styles.css")


class InterfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.labels: set[str] = set()
        self.inputs: list[dict[str, str | None]] = []
        self.buttons: list[dict[str, str | None]] = []
        self.external_assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"] or "")
        if tag == "label" and values.get("for"):
            self.labels.add(values["for"] or "")
        if tag == "input":
            self.inputs.append(values)
        if tag == "button":
            self.buttons.append(values)
        if tag in {"link", "script", "img"}:
            source = values.get("href") or values.get("src") or ""
            if source.startswith(("http://", "https://")):
                self.external_assets.append(source)


def parse_interface() -> InterfaceParser:
    parser = InterfaceParser()
    parser.feed(HTML.read_text(encoding="utf-8"))
    return parser


def _rgb(hex_value: str) -> tuple[int, int, int]:
    value = hex_value.lstrip("#")
    if len(value) == 3:
        value = "".join(character * 2 for character in value)
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def _luminance(hex_value: str) -> float:
    channels = []
    for channel in _rgb(hex_value):
        normalized = channel / 255
        channels.append(
            normalized / 12.92
            if normalized <= 0.04045
            else ((normalized + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_interface_has_keyboard_entry_and_named_controls() -> None:
    parser = parse_interface()
    assert "main-content" in parser.ids
    assert 'href="#main-content"' in HTML.read_text(encoding="utf-8")
    assert all(button.get("aria-label") or button.get("id") for button in parser.buttons)
    assert all(
        item.get("id") in parser.labels or item.get("aria-label") for item in parser.inputs
    )


def test_interface_has_no_external_runtime_assets() -> None:
    assert parse_interface().external_assets == []


def test_primary_text_contrast_passes_wcag_aa_in_both_themes() -> None:
    css = CSS.read_text(encoding="utf-8")
    dark = re.search(r":root\{([^}]+)\}", css)
    light = re.search(r'html\[data-theme="light"\]\{([^}]+)\}', css)
    assert dark and light
    for variables in (dark.group(1), light.group(1)):
        colors = dict(re.findall(r"--([\w-]+):(#[0-9a-fA-F]{3,6})", variables))
        assert _contrast(colors["text"], colors["bg"]) >= 4.5
        assert _contrast(colors["muted"], colors["bg"]) >= 4.5


def test_public_brand_is_nadi_hd() -> None:
    content = HTML.read_text(encoding="utf-8")
    assert "NADI-HD" in content
    assert "NEPHRON-1" not in content
