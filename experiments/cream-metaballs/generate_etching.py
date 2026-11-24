"""Create local-only recessed glass outlines from the repository's original pattern."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
source = ROOT / "assets" / "bakery-pattern-cream.svg"
original = ET.parse(source).getroot()
result = ET.Element(f"{{{SVG}}}svg", {
    "width": "640", "height": "480", "viewBox": "0 0 640 480", "fill": "none",
})
ET.SubElement(result, f"{{{SVG}}}title").text = "Original bakery outlines etched into glass"
ET.SubElement(result, f"{{{SVG}}}desc").text = (
    "Local material study. Original repository icon geometry with a fine recessed shadow "
    "and offset pale light-catching edge; no reference photograph pixels."
)
definitions = ET.SubElement(result, f"{{{SVG}}}defs")
lines = deepcopy(original.find(f"{{{SVG}}}g"))
lines.set("id", "bakery-etching-lines")
lines.attrib.pop("stroke")
lines.attrib.pop("opacity")
definitions.append(lines)
for name, stroke, opacity, offset in [
    ("etched-recess", "#34483a", ".12", "translate(-.45 -.55)"),
    ("etched-light-edge", "#fffdf3", ".62", "translate(.55 .65)"),
    ("etched-frosted-line", "#fffaf1", ".20", "translate(0 0)"),
]:
    ET.SubElement(result, f"{{{SVG}}}use", {
        "id": name, "href": "#bakery-etching-lines",
        "stroke": stroke, "opacity": opacity, "transform": offset,
    })
ET.indent(result, space="  ")
output = ROOT / "assets" / "bakery-glass-etching.svg"
output.write_bytes(ET.tostring(result, encoding="utf-8", xml_declaration=False) + b"\n")
print(f"Local etching: {output.name}; original-pattern SHA256: {sha256(source.read_bytes()).hexdigest()}")
