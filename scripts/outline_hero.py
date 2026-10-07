# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools==4.60.2", "uharfbuzz==0.56.3"]
# ///

import argparse
from dataclasses import dataclass
from io import BytesIO
import math
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont, TTLibError
import uharfbuzz as hb


SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
FONT_PROPERTIES = {
    "font-family", "font-size", "font-weight", "text-anchor", "letter-spacing"
}
PAINT_PROPERTIES = {
    "id", "transform", "fill", "stroke", "stroke-width", "fill-opacity",
    "stroke-opacity", "opacity", "role", "aria-label", "aria-hidden",
    "aria-labelledby", "stroke-linecap", "stroke-linejoin", "fill-rule",
}
ALLOWED_ATTRIBUTES = {
    "svg": {"width", "height", "viewBox"} | PAINT_PROPERTIES | FONT_PROPERTIES,
    "title": {"id"},
    "desc": {"id"},
    "g": PAINT_PROPERTIES | FONT_PROPERTIES,
    "rect": {"x", "y", "width", "height", "rx", "ry"} | PAINT_PROPERTIES,
    "text": {"x", "y"} | PAINT_PROPERTIES | FONT_PROPERTIES,
}


def svg(name: str) -> str:
    return f"{{{SVG}}}{name}"


def number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("Non-finite glyph coordinates are unsupported")
    result = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if result in {"", "-0"} else result


def length(value: str | None, name: str) -> float:
    if value is None or not re.fullmatch(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?:px)?", value.strip()
    ):
        raise ValueError(f"{name} must be a single number in SVG units or px, got {value!r}")
    result = float(value.strip().removesuffix("px"))
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass
class FontFace:
    prefix: str
    font: TTFont
    hb_font: hb.Font

    @property
    def upem(self) -> int:
        return self.font["head"].unitsPerEm


def load_font(path: Path, prefix: str) -> FontFace:
    data = path.read_bytes()
    if data[:4] not in {b"\x00\x01\x00\x00", b"OTTO", b"true"}:
        raise ValueError(f"{path.name}: supply a static TTF/OTF, not a font collection or webfont")
    font = TTFont(BytesIO(data))
    if "fvar" in font:
        raise ValueError(f"{path.name}: variable fonts are unsupported; supply a static face")
    hb_font = hb.Font(hb.Face(data))
    hb_font.scale = (font["head"].unitsPerEm, font["head"].unitsPerEm)
    return FontFace(prefix, font, hb_font)


def validate_source(root: ET.Element) -> set[str]:
    if root.tag != svg("svg"):
        raise ValueError("The source must use the default SVG namespace")
    ids: set[str] = set()
    for element in root.iter():
        name = element.tag.removeprefix(f"{{{SVG}}}")
        if element.tag != svg(name) or name not in ALLOWED_ATTRIBUTES:
            raise ValueError(f"Unsupported source element: {name}; plain text only, no tspans or CSS")
        unknown = element.attrib.keys() - ALLOWED_ATTRIBUTES[name]
        if unknown:
            raise ValueError(f"Unsupported {name} attributes: {', '.join(sorted(unknown))}")
        if any("url(" in element.get(paint, "").lower() for paint in ("fill", "stroke")):
            raise ValueError("Paint servers and external resources are unsupported")
        if element.get("id"):
            if element.attrib["id"] in ids:
                raise ValueError(f"Duplicate source id: {element.attrib['id']}")
            ids.add(element.attrib["id"])
    return ids


def outline_text(
    text_element: ET.Element,
    inherited: dict[str, str],
    faces: dict[str, FontFace],
    definitions: ET.Element,
    paths: dict[tuple[str, int], str],
    source_ids: set[str],
) -> ET.Element:
    # ponytail: one horizontal LTR run per text; use an SVG renderer for richer text.
    text = text_element.text or ""
    if len(text_element) or not text or any(char in text for char in "\n\r\t"):
        raise ValueError("Each text element must contain nonempty, single-line plain text")
    if any(unicodedata.bidirectional(char) in {
        "R", "AL", "AN", "RLE", "RLO", "LRE", "LRO", "PDF", "LRI", "RLI", "FSI", "PDI"
    } for char in text):
        raise ValueError(f"Bidirectional text is unsupported: {text!r}")
    properties = inherited | {
        key: value for key, value in text_element.attrib.items() if key in FONT_PROPERTIES
    }
    missing = {"font-family", "font-size", "font-weight"} - properties.keys()
    if missing:
        raise ValueError(f"{text!r} is missing inherited properties: {', '.join(sorted(missing))}")
    size = length(properties["font-size"], "font-size")
    if size <= 0:
        raise ValueError("font-size must be positive")
    weight = properties["font-weight"].strip()
    if not weight.isascii() or not weight.isdigit() or not 1 <= int(weight) <= 1000:
        raise ValueError(f"font-weight must be numeric (1–1000), got {weight!r}")
    family = properties["font-family"].split(",", 1)[0].strip().strip("\"'").casefold()
    if family in {"zedmono", "zed mono", "monospace", "ui-monospace"}:
        face = faces["mono"]
    elif family == "geist":
        face = faces["bold" if int(weight) >= 700 else "medium"]
    else:
        raise ValueError(f"Unknown font family {properties['font-family']!r}; use Geist or ZedMono")
    anchor = properties.get("text-anchor", "start").strip()
    if anchor not in {"start", "middle", "end"}:
        raise ValueError(f"Unsupported text-anchor: {anchor!r}")
    spacing = properties.get("letter-spacing", "0").strip()
    tracking = 0.0 if spacing == "normal" else length(spacing, "letter-spacing")
    x = length(text_element.get("x"), "text x")
    y = length(text_element.get("y"), "text y")

    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.language = "en"
    buffer.guess_segment_properties()
    if buffer.direction != "ltr":
        raise ValueError(f"Only horizontal left-to-right text is supported: {text!r}")
    hb.shape(face.hb_font, buffer, {"liga": 0, "clig": 0} if tracking else {})
    infos = buffer.glyph_infos
    positions = buffer.glyph_positions
    for info in infos:
        if info.codepoint == 0:
            char = text[info.cluster]
            raise ValueError(f"{face.prefix}: missing glyph U+{ord(char):04X} in {text!r}")

    scale = size / face.upem
    tracking_units = tracking / scale
    gaps = sum(left.cluster != right.cluster for left, right in zip(infos, infos[1:]))
    width = (sum(position.x_advance for position in positions) + gaps * tracking_units) * scale
    shift = width * {"start": 0, "middle": 0.5, "end": 1}[anchor]
    attributes = {
        key: value for key, value in text_element.attrib.items()
        if key not in FONT_PROPERTIES | {"x", "y", "aria-label"}
    }
    attributes["aria-label"] = text
    attributes.setdefault("role", "img")
    group = ET.Element(svg("g"), attributes)
    glyph_group = ET.SubElement(group, svg("g"), {
        "transform": f"translate({number(x - shift)} {number(y)}) scale({number(scale)} {number(-scale)})"
    })
    glyph_set = face.font.getGlyphSet()
    glyph_order = face.font.getGlyphOrder()
    pen_x = pen_y = 0.0
    for index, (info, position) in enumerate(zip(infos, positions)):
        key = (face.prefix, info.codepoint)
        if key not in paths:
            path_id = f"outline-{face.prefix}-{info.codepoint}"
            if path_id in source_ids:
                raise ValueError(f"Source id collides with generated glyph: {path_id}")
            pen = SVGPathPen(glyph_set, ntos=number)
            glyph_set[glyph_order[info.codepoint]].draw(pen)
            ET.SubElement(definitions, svg("path"), {"id": path_id, "d": pen.getCommands()})
            paths[key] = path_id
        ET.SubElement(glyph_group, svg("use"), {
            "href": f"#{paths[key]}",
            "transform": f"translate({number(pen_x + position.x_offset)} {number(pen_y + position.y_offset)})",
        })
        pen_x += position.x_advance
        pen_y += position.y_advance
        if index + 1 < len(infos) and info.cluster != infos[index + 1].cluster:
            pen_x += tracking_units
    group.tail = text_element.tail
    return group


def generate(faces: dict[str, FontFace]) -> None:
    assets = Path(__file__).resolve().parents[1] / "assets" / "readme"
    root = ET.parse(assets / "hero.source.svg").getroot()
    source_ids = validate_source(root)
    definitions = ET.Element(svg("defs"))
    paths: dict[tuple[str, int], str] = {}

    def replace(parent: ET.Element, inherited: dict[str, str]) -> None:
        properties = inherited | {
            key: value for key, value in parent.attrib.items() if key in FONT_PROPERTIES
        }
        for index, child in enumerate(list(parent)):
            if child.tag == svg("text"):
                parent[index] = outline_text(child, properties, faces, definitions, paths, source_ids)
            elif child.tag == svg("g"):
                replace(child, properties)
        for key in FONT_PROPERTIES:
            parent.attrib.pop(key, None)

    replace(root, {})
    if not paths:
        raise ValueError("The source contains no text to outline")
    definition_index = 0
    while definition_index < len(root) and root[definition_index].tag in {svg("title"), svg("desc")}:
        definition_index += 1
    root.insert(definition_index, definitions)
    for element in root.iter():
        if element.tag not in {svg("title"), svg("desc")} and element.text and not element.text.strip():
            element.text = None
        if element.tail and not element.tail.strip():
            element.tail = None
    assert not any(element.tag == svg("text") for element in root.iter())
    assert all(element.get("href", "").removeprefix("#") in set(paths.values())
               for element in root.iter(svg("use")))
    ET.ElementTree(root).write(assets / "hero.svg", encoding="utf-8", xml_declaration=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Outline the repo banner using local static Geist and ZedMono fonts.")
    parser.add_argument("--geist-bold", required=True, type=Path)
    parser.add_argument("--geist-medium", required=True, type=Path)
    parser.add_argument("--zed-mono", required=True, type=Path)
    args = parser.parse_args()
    try:
        generate({
            "bold": load_font(args.geist_bold, "gb"),
            "medium": load_font(args.geist_medium, "gm"),
            "mono": load_font(args.zed_mono, "zm"),
        })
    except (OSError, ValueError, ET.ParseError, TTLibError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()
