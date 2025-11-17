#!/usr/bin/env python3

import argparse
import csv
import os
import subprocess
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
    return parser.parse_args()

def normalize_svg(source_path, dest_path):
    """
    Normalize an SVG using Inkscape CLI.
    - Export as plain SVG
    - Vacuum defs
    - Replace hardcoded fills with 'currentColor'
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

    # Replace fill colors with currentColor
    with open(dest_path, "r") as f:
        content = f.read()

    content = content.replace('fill="#000000"', 'fill="currentColor"')
    content = content.replace('fill="black"', 'fill="currentColor"')

    with open(dest_path, "w") as f:
        f.write(content)

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

def generate_index_theme(theme_dir, dir_entries):
    """
    Generate the index.theme file.
    """
    content = f"""[Icon Theme]
Name=Material 3 (Plasma)
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

    theme_dir = Path("material3-plasma")
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

            # Find the source SVG file
            source_svg_files = list(material_src_dir.rglob(f"**/{material_id}.svg"))
            if not source_svg_files:
                print(f"Warning: Material icon '{material_id}' not found.")
                continue
            source_svg = source_svg_files[0]

            normalized_svg = normalized_dir / f"{material_id}.svg"

            # 1. Normalize the upstream glyph
            normalize_svg(source_svg, normalized_svg)

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
    generate_index_theme(theme_dir, dir_entries)

    print("Build complete.")

if __name__ == "__main__":
    main()
