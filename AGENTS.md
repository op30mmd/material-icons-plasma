# AGENTS.md  
**Project:** “Material 3 for Plasma” – a KDE Plasma icon theme generated from Google’s Material 3 (Material You) symbols  
**Audience:** An autonomous AI agent with shell / scripting capability, vector-graphics tooling (e.g. Inkscape CLI, rsvg-convert, or librsvg), and Internet access for open-source assets.  

---

## 0. Success Criteria  
1. A fully installable KDE icon theme that passes `xdg-icon-resource validate` and Plasma’s internal icon-fallback checks.  
2. 100 % coverage of the FreeDesktop Icon Naming Specification **core** contexts (`actions`, `apps`, `devices`, `mimetypes`, `places`, `status`) plus Plasma-specific extras.  
3. Every icon provided as:  
   • 1 × scalable SVG (single-color, currentColor driven)  
   • PNG raster variants for 16, 22, 24, 32, 48, 64, 96, 128, 256 px  
4. No license conflicts: all upstream glyphs are Apache-2.0; our theme ships under the same.  
5. Deliverables:  
   • `material3-plasma/` theme directory ready for `~/.local/share/icons/`  
   • `index.theme` metadata file  
   • Build scripts and asset-map (`mapping.csv`) committed to `tools/`  
   • Release archive `material3-plasma-vX.Y.tar.xz`  

---

## 1. Environment Preparation  

| Task | Command / Tool | Notes |
|------|----------------|-------|
|Install dependencies|`sudo apt install inkscape librsvg2-bin optipng imagemagick jq python3-pip libxi6`|Inkscape ≥ 1.3 CLI is required for SVG preprocessing.|
|Fetch Material Symbols repo|`git clone https://github.com/google/material-design-icons.git`|Contains `symbols` and variable icons.|
|Create project skeleton|`mkdir -p build src tools material3-plasma`|Keep generated art out of git history until final.|
|Install Python helpers|`pip install pyyaml pillow cairosvg`|Needed for color swapping and CI.|  

---

## 2. Directory Layout Convention  

```
material3-plasma/
 ├── index.theme
 ├── scalable/
 │    └── <context>/icon-name.svg
 ├── 16x16/…                (repeat for 22x22, 24x24, … 256x256)
 └── LICENSE                (Apache-2.0)
tools/
 ├── build.py               (or build.sh) – main orchestrator
 ├── fetch_material.py      – pulls latest glyphs
 ├── generate_pngs.py
 └── mapping.csv            – rows: kde_name, material_id, context
docs/
 └── CHANGELOG.md
```  

---

## 3. Detailed Workflow (Agent Action Plan)  

### 3.1 Gather & Normalize Upstream Glyphs  
a. Call `tools/fetch_material.py` to copy the latest **variable** Material Symbols (`symbols` directory) into `src/raw/`.  
b. Use Inkscape CLI:  
```
inkscape src/raw/heart.svg --export-plain-svg --export-filename=src/normalized/heart.svg \
    --export-area-drawing --vacuum-defs
```  
c. Strip unneeded metadata, enforce `width="24"` / `height="24"`, and replace hard-coded fills with `fill="currentColor"`.  

### 3.2 Map Material ➞ KDE Names  
1. Seed `tools/mapping.csv` with common pairs, e.g.  
```
edit-copy,content_copy,actions
list-add,add,actions
go-home,home,places
```
2. When a KDE name lacks an obvious Material equivalent, create a **composed** draft by duplicating and rotating/combining paths (Inkscape `--actions="select-all;object-rotate90;export-filename=…"`) or fall back to `material_filled_unknown.svg`.  
3. Programmatically verify coverage:  
```
python - << 'EOF'
import csv, json, subprocess, pathlib, sys
needed = set(json.load(open('spec/kde_core_names.json')))
have = {r[0] for r in csv.reader(open('tools/mapping.csv'))}
print("Missing:", needed-have); sys.exit(len(needed-have)>0)
EOF
```  

### 3.3 Build Scalable Icons  
Loop over mapping:  
```
inkscape src/normalized/{material_id}.svg \
  --export-plain-svg \
  --export-filename=material3-plasma/scalable/{context}/{kde_name}.svg
optipng -quiet material3-plasma/scalable/{context}/{kde_name}.svg
```

### 3.4 Color & Style Variants (Optional)  
Material 3 offers Filled, Outlined, Rounded, Two-Tone. Provide one Plasma variant, default to Filled. Allow `--style=<variant>` arg in build script.

### 3.5 Rasterize PNG Sizes  
Use rsvg-convert for sharp hinting:  
```
for size in 16 22 24 32 48 64 96 128 256; do
  mkdir -p material3-plasma/${size}x${size}/${context}
  rsvg-convert -w $size -h $size \
     material3-plasma/scalable/${context}/${kde_name}.svg \
     -o material3-plasma/${size}x${size}/${context}/${kde_name}.png
  optipng -o7 -quiet material3-plasma/${size}x${size}/${context}/${kde_name}.png
done
```  

### 3.6 Generate `index.theme`  
Template partial:  
```ini
[Icon Theme]
Name=Material 3 (Plasma)
Comment=Material You symbols adapted for KDE Plasma.
Inherits=breeze
Example=folder
# Automatically filled by build.py:
Directories=scalable/actions,16x16/actions,…
```
Script should auto-append each generated size/context directory.

### 3.7 QA & Validation  
1. `kbuildsycoca5 --noincremental` then preview in `systemsettings5 > Icons`.  
2. Run KDE test script: `tests/plasma_theme_sanity.py` (copy from Breeze repo).  
3. Ensure fallback chain: if icon missing, Plasma pulls from `Inherits=breeze`.  

### 3.8 Packaging & Release  
```
tar -C material3-plasma -caf material3-plasma-v$VERSION.tar.xz .
sha256sum material3-plasma-v$VERSION.tar.xz > SHA256SUMS
```
Attach archive to GitHub release and optionally upload to KDE Store with tags `icon-theme`, `MaterialYou`.  

---

## 4. Continuous Integration  

GitHub Actions `ci.yml` skeleton:  
```yaml
name: Build & Lint
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update && sudo apt-get install inkscape librsvg2-bin optipng -y
      - run: ./tools/build.py --ci
      - name: Validate icons
        run: |
          for s in 16 22 24 32 48; do
            if [ ! -d material3-plasma/${s}x${s} ]; then exit 1; fi
          done
      - uses: actions/upload-artifact@v4
        with:
          name: material3-plasma
          path: material3-plasma
```  

---

## 5. License Compliance  

• Upstream Material Icons: Apache-2.0  
• Our glue code & artwork: Apache-2.0 (include full text in root `LICENSE`)  
• Mention Google trademark attribution:  
  “Material is a trademark of Google LLC.”  

---

## 6. Agent Execution Checklist  

- [ ] Dependencies installed  
- [ ] Upstream glyphs cloned & normalized  
- [ ] `mapping.csv` covers 100 % core spec  
- [ ] SVGs generated in `scalable/`  
- [ ] PNGs generated for all required resolutions  
- [ ] `index.theme` auto-filled and passes `desktop-file-validate`  
- [ ] Theme installs and displays in Plasma  
- [ ] Archive packaged and checksummed  
- [ ] CI workflow green  

If any step fails, halt, report the error, and await manual mapping fixes instead of guessing.  

---

## 7. Extensibility Notes  

1. Colorful accent variant: produce “Material3-Accent” using `accentColor` token reads from `plasma-org.kde.plasma.desktop` color scheme.  
2. Symbol weight support (300, 400, 500) can be added by parameterizing stroke width in Inkscape’s `--export-overwrite`.  
3. Future Plasma 6 will look for `scalable@2x`; reserve roadmap ticket.  

---

Happy creating!
