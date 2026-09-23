#!/usr/bin/env python3
"""Validate canonical faces and assemble the static preview site."""

import argparse
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACES = ROOT / "faces"
EXTENSIONS = (".png", ".webp", ".jpg", ".jpeg")


def face_metadata(path):
    source = path.read_text()
    result = {}
    for key in ("id", "name", "status"):
        match = re.search(rf"^{key}:\s*(.+?)\s*$", source, re.MULTILINE)
        if not match:
            raise ValueError(f"{path}: missing {key}")
        result[key] = match.group(1).strip('"\'')
    return result


def discover():
    faces = []
    for directory in sorted(FACES.iterdir()):
        xml_file = directory / "watchface.xml"
        if not directory.is_dir() or not xml_file.exists():
            continue
        metadata = face_metadata(directory / "face.yaml")
        slug = directory.name
        if not re.fullmatch(r"[a-z][a-z0-9-]*", slug) or metadata["id"] != slug:
            raise ValueError(f"{slug}: id must match a lower-case face directory")
        root = ET.parse(xml_file).getroot()
        if root.tag != "WatchFace":
            raise ValueError(f"{xml_file}: expected WatchFace root")
        assets = {}
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
        faces.append((directory, metadata, assets))
    return faces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    faces = discover()
    if not faces:
        raise ValueError("No buildable XML faces found")
    if args.check:
        print(f"Validated {len(faces)} canonical watch faces")
        return
    output = args.output.resolve()
    if output == ROOT or ROOT not in output.parents:
        raise ValueError("Output must be a subdirectory of the repository")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(ROOT / "preview", output)
    catalog = []
    for directory, metadata, assets in faces:
        slug = directory.name
        target = output / "faces" / slug
        target.mkdir(parents=True)
        shutil.copy2(directory / "watchface.xml", target / "watchface.xml")
        shutil.copy2(directory / "face.yaml", target / "face.yaml")
        for name, asset in assets.items():
            (target / "assets").mkdir(exist_ok=True)
            shutil.copy2(asset, target / "assets" / asset.name)
        catalog.append({"slug": slug, "name": metadata["name"], "status": metadata["status"],
                        "assets": {name: asset.name for name, asset in assets.items()}})
    (output / "faces.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"Built {len(faces)} faces at {output}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, ET.ParseError) as error:
        sys.exit(str(error))
