#!/usr/bin/env python3

import argparse
import csv
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

def get_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Build the Material 3 icon theme for Plasma.")
    parser.add_argument("--ci", action="store_true", help="Run in CI mode.")
    parser.add_argument(
        "--material-path",
        type=Path,
        default=Path("material-design-icons"),
        help="Path to the checked-out material-design-icons repository.",
    )
    parser.add_argument(
        "--theme",
        type=str,
        choices=["light", "dark"],
        default="light",
        help="The color variant to build (light or dark).",
    )
    return parser.parse_args()

def normalize_svg(source_path, dest_path, theme="light"):
    """
    Normalize an SVG using Inkscape CLI and set the fill color.
    """
    if not source_path.exists():
        print(f"Warning: Source icon not found: {source_path}")
        return

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "inkscape",
        str(source_path),
        "--export-plain-svg",
        f"--export-filename={dest_path}",
        "--export-area-drawing",
        "--vacuum-defs",
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)

    # Set fill color based on theme
    fill_color = "#232629" if theme == "light" else "#eff0f1" # Breeze light/dark text colors

    tree = ET.parse(dest_path)
    root = tree.getroot()
    ET.register_namespace("", "http://www.w3.org/2000/svg")

    shape_elements = [
        "path", "rect", "circle", "ellipse", "polygon", "polyline", "line"
    ]
    for shape_name in shape_elements:
        for element in root.findall(f".//{{http://www.w3.org/2000/svg}}{shape_name}"):
            element.set("fill", fill_color)

    tree.write(dest_path, xml_declaration=True)

def rasterize_png(source_svg, dest_dir):
    """
    Rasterize an SVG to all required PNG sizes.
    """
    sizes = [16, 22, 24, 32, 48, 64, 96, 128, 256]
    for size in sizes:
        size_dir = dest_dir / f"{size}x{size}"
        size_dir.mkdir(parents=True, exist_ok=True)
        dest_png = size_dir / f"{source_svg.stem}.png"

        command = [
            "rsvg-convert",
            "-w", str(size),
            "-h", str(size),
            str(source_svg),
            "-o", str(dest_png),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)

        # Optimize PNG
        subprocess.run(["optipng", "-o7", "-quiet", str(dest_png)], check=True)

def generate_index_theme(theme_dir, dir_entries, theme="light"):
    """
    Generate the index.theme file.
    """
    theme_name = f"Material 3 (Plasma {theme.capitalize()})"
    content = f"""[Icon Theme]
Name={theme_name}
Comment=Material You symbols adapted for KDE Plasma.
Inherits=breeze
Example=folder
Directories={','.join(sorted(list(dir_entries)))}
"""

    with open(theme_dir / "index.theme", "w") as f:
        f.write(content)

def main():
    """
    Main function to build the Material 3 Plasma icon theme.
    """
    args = get_args()

    mapping_file = Path("tools/mapping.csv")
    if not mapping_file.exists():
        print("Error: mapping.csv not found!")
        return

    material_src_dir = args.material_path
    if not material_src_dir.exists():
        print(f"Error: Material source directory not found at: {material_src_dir}")
        print("Please provide the correct path using --material-path")
        return

    theme_dir = Path(f"material3-plasma-{args.theme}")
    normalized_dir = Path("src/normalized")
    theme_dir.mkdir(exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    # Track directories to add to index.theme
    dir_entries = set()

    with open(mapping_file, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            kde_name, material_id, context = row

            print(f"Processing: {kde_name} ({material_id}) in {context}")

            # Find the source icon directory
            source_icon_dirs = list(material_src_dir.rglob(f"**/{material_id}"))
            if not source_icon_dirs:
                print(f"Warning: Material icon directory '{material_id}' not found.")
                continue

            source_svg = None
            for icon_dir in source_icon_dirs:
                potential_svg = icon_dir / "materialicons" / "24px.svg"
                if potential_svg.exists():
                    source_svg = potential_svg
                    break

            if not source_svg:
                print(f"Warning: Default SVG not found for icon '{material_id}' in any of the found directories.")
                continue

            normalized_svg = normalized_dir / f"{material_id}.svg"

            # 1. Normalize the upstream glyph
            normalize_svg(source_svg, normalized_svg, args.theme)

            # 2. Place scalable icon in theme directory
            scalable_dir = theme_dir / "scalable" / context
            scalable_dir.mkdir(parents=True, exist_ok=True)
            theme_svg = scalable_dir / f"{kde_name}.svg"

            # For now, just copy the normalized svg
            # Later, this might involve color changes etc.
            if normalized_svg.exists():
                theme_svg.write_text(normalized_svg.read_text())
                dir_entries.add(f"scalable/{context}")

                # 3. Rasterize PNGs
                rasterize_png(theme_svg, theme_dir)
                for size in [16, 22, 24, 32, 48, 64, 96, 128, 256]:
                    dir_entries.add(f"{size}x{size}/{context}")


    # 4. Generate index.theme
    generate_index_theme(theme_dir, dir_entries, args.theme)

    print(f"Build complete for {args.theme} theme.")

if __name__ == "__main__":
    main()
