#!/usr/bin/env python3
"""Validate canonical faces and assemble the static preview site.

The site has a gallery at the root and one directly linkable page per face at
faces/<slug>/, generated from preview/templates/.
"""

import argparse
import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parents[1]
FACES = ROOT / "faces"
PREVIEW = ROOT / "preview"
TEMPLATES = PREVIEW / "templates"
EXTENSIONS = (".png", ".webp", ".jpg", ".jpeg")
BASE_URL = "https://patrickauld.github.io/watches/"
STATUS_ORDER = {"promoted": 0, "draft": 1}


def face_metadata(path):
    """Read top-level scalars and folded/literal blocks from a face.yaml."""
    lines = path.read_text().splitlines()
    result = {}
    index = 0
    while index < len(lines):
        match = re.match(r"^([A-Za-z][\w-]*):\s*(.*?)\s*$", lines[index])
        index += 1
        if not match:
            continue
        key, value = match.groups()
        if value in (">", ">-", "|", "|-"):
            block = []
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith((" ", "\t"))):
                block.append(lines[index].strip())
                index += 1
            joiner = " " if value.startswith(">") else "\n"
            result[key] = joiner.join(line for line in block if line)
        elif value:
            result[key] = value.strip('"\'')
    for key in ("id", "name", "status"):
        if key not in result:
            raise ValueError(f"{path}: missing {key}")
    return result


def discover():
    faces = []
    for directory in sorted(FACES.iterdir()):
        if not directory.is_dir() or not (directory / "face.yaml").exists():
            continue
        metadata = face_metadata(directory / "face.yaml")
        slug = directory.name
        if not re.fullmatch(r"[a-z][a-z0-9-]*", slug) or metadata["id"] != slug:
            raise ValueError(f"{slug}: id must match a lower-case face directory")
        xml_file = directory / "watchface.xml"
        assets = {}
        if xml_file.exists():
            root = ET.parse(xml_file).getroot()
            if root.tag != "WatchFace":
                raise ValueError(f"{xml_file}: expected WatchFace root")
            for element in root.iter():
                resource = element.get("resource")
                if not resource:
                    continue
                if not re.fullmatch(r"[a-z][a-z0-9_]*", resource):
                    raise ValueError(f"{xml_file}: invalid Android resource {resource}")
                candidates = [directory / "assets" / f"{resource}{ext}" for ext in EXTENSIONS]
                matches = [path for path in candidates if path.is_file()]
                if len(matches) != 1:
                    raise ValueError(f"{xml_file}: resource {resource} must resolve to exactly one image")
                assets[resource] = matches[0]
        previews = sorted(p for p in (directory / "previews").glob("*") if p.suffix.lower() in EXTENSIONS) \
            if (directory / "previews").is_dir() else []
        faces.append({"dir": directory, "slug": slug, "meta": metadata, "xml": xml_file.exists(),
                      "assets": assets, "previews": previews})
    faces.sort(key=lambda f: (not f["xml"], STATUS_ORDER.get(f["meta"]["status"], 9), f["meta"]["name"].lower()))
    return faces


def render(template, **values):
    return Template((TEMPLATES / template).read_text()).safe_substitute(values)


def summary(face):
    return face["meta"].get("description") or f"{face['meta']['name']} watch face."


def face_page(face, base_url):
    url = f"{base_url}faces/{face['slug']}/"
    og_image = ""
    if face["previews"]:
        names = [p.name for p in face["previews"]]
        chosen = next((n for n in ("day.png", "default.png") if n in names), names[0])
        og_image = f'    <meta property="og:image" content="{html.escape(url)}previews/{html.escape(chosen)}" />'
    return render("face.html", name=html.escape(face["meta"]["name"]), slug=face["slug"],
                  status=html.escape(face["meta"]["status"]), description=html.escape(summary(face)),
                  url=html.escape(url), og_image=og_image)


def gallery_card(face):
    name = html.escape(face["meta"]["name"])
    status = html.escape(face["meta"]["status"])
    if face["xml"]:
        thumb = f'<canvas data-face="{face["slug"]}" width="450" height="450" aria-label="{name} preview"></canvas>'
    else:
        thumb = '<div class="thumb-empty">In design</div>'
    return (f'        <a class="face-card" href="faces/{face["slug"]}/">\n'
            f'          <div class="thumb">{thumb}</div>\n'
            f'          <div>\n'
            f'            <h2>{name}<span class="badge status-{status}">{status}</span></h2>\n'
            f'            <p>{html.escape(summary(face))}</p>\n'
            f'          </div>\n'
            f'        </a>')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/") + "/"
    faces = discover()
    if not any(face["xml"] for face in faces):
        raise ValueError("No buildable XML faces found")
    if args.check:
        print(f"Validated {sum(f['xml'] for f in faces)} canonical watch faces ({len(faces)} pages)")
        return
    output = args.output.resolve()
    if output == ROOT or ROOT not in output.parents:
        raise ValueError("Output must be a subdirectory of the repository")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(PREVIEW, output, ignore=shutil.ignore_patterns("templates"))
    catalog = []
    for face in faces:
        directory, slug = face["dir"], face["slug"]
        target = output / "faces" / slug
        target.mkdir(parents=True)
        shutil.copy2(directory / "face.yaml", target / "face.yaml")
        if face["xml"]:
            shutil.copy2(directory / "watchface.xml", target / "watchface.xml")
        if (directory / "strings.xml").exists():
            shutil.copy2(directory / "strings.xml", target / "strings.xml")
        for asset in face["assets"].values():
            (target / "assets").mkdir(exist_ok=True)
            shutil.copy2(asset, target / "assets" / asset.name)
        for preview in face["previews"]:
            (target / "previews").mkdir(exist_ok=True)
            shutil.copy2(preview, target / "previews" / preview.name)
        (target / "index.html").write_text(face_page(face, base_url))
        catalog.append({"slug": slug, "name": face["meta"]["name"], "status": face["meta"]["status"],
                        "xml": face["xml"], "description": summary(face),
                        "assets": {name: asset.name for name, asset in face["assets"].items()}})
    (output / "faces.json").write_text(json.dumps(catalog, indent=2) + "\n")
    cards = "\n".join(gallery_card(face) for face in faces)
    (output / "index.html").write_text(render("index.html", cards=cards, base_url=html.escape(base_url)))
    print(f"Built {len(faces)} face pages at {output}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, ET.ParseError) as error:
        sys.exit(str(error))
