#!/usr/bin/env python3
"""Build and validate each promoted XML face for Watch Face Push."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*command):
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(f"{' '.join(map(str, command))}\n{completed.stdout}\n{completed.stderr}")
    return completed.stdout + completed.stderr


def metadata(file):
    text = file.read_text()
    return {
        key: re.search(rf"^{key}:\s*(.+?)\s*$", text, re.MULTILINE).group(1).strip("'\"")
        for key in ("id", "name", "status")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validator", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dist-release")
    args = parser.parse_args()
    validator = args.validator.resolve()
    if not validator.is_file():
        raise ValueError(f"Missing official Watch Face Push validator: {validator}")
    if not os.environ.get("WATCHES_KEYSTORE"):
        raise ValueError("A stable signing key is required for published watch faces")
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    version = int(os.environ["GITHUB_RUN_NUMBER"])
    faces = []
    for xml in sorted((ROOT / "faces").glob("*/watchface.xml")):
        face = metadata(xml.parent / "face.yaml")
        if face["status"] != "promoted":
            continue
        slug = face["id"]
        if slug != xml.parent.name or not re.fullmatch(r"[a-z][a-z0-9-]*", slug):
            raise ValueError(f"Invalid face id: {slug}")
        run("./gradlew", ":watchface:assembleDebug", f"-PfaceSlug={slug}")
        source = ROOT / "watchface/build/outputs/apk/debug/watchface-debug.apk"
        filename = f"{slug}-{version}.apk"
        target = output / filename
        run(sys.executable, "scripts/prepare-face-apk.py", source, target)
        package_name = f"com.patrickauld.watches.companion.watchfacepush.{slug.replace('-', '_')}"
        result = run("java", "-jar", str(validator), f"--apk_path={target}",
                     "--package_name=com.patrickauld.watches.companion")
        match = re.search(r"validation\s+token\s*:\s*(\S+)", result, re.IGNORECASE)
        if not match:
            match = re.search(r'"validationToken"\s*:\s*"([^"]+)"', result)
        if not match:
            raise ValueError(f"Validator returned no token for {slug}:\n{result}")
        faces.append({
            "slug": slug,
            "name": face["name"],
            "apk": filename,
            "packageName": package_name,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "validationToken": match.group(1),
            "versionCode": version,
            "versionName": f"0.1.{version}",
        })
    if not faces:
        raise ValueError("No promoted faces with canonical XML")
    catalog = {
        "schemaVersion": 1,
        "commitSha": os.environ["GITHUB_SHA"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "faces": faces,
    }
    (output / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"Validated and packaged {len(faces)} face(s)")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, KeyError) as error:
        sys.exit(str(error))
