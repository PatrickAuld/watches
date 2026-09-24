#!/usr/bin/env python3
"""Turn AGP's signed output into a resource-only Watch Face Push APK."""

import argparse
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path


def tool(name):
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk:
        raise ValueError("ANDROID_HOME or ANDROID_SDK_ROOT is required")
    versions = sorted(
        (p for p in (Path(sdk) / "build-tools").iterdir() if (p / name).is_file()),
        key=lambda p: tuple(int(n) for n in re.findall(r"\d+", p.name)),
    )
    if not versions:
        raise ValueError(f"Missing Android build tool: {name}")
    return str(versions[-1] / name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as directory:
        unsigned = Path(directory) / "unsigned.apk"
        aligned = Path(directory) / "aligned.apk"
        with zipfile.ZipFile(args.source) as source, zipfile.ZipFile(unsigned, "w") as target:
            for info in source.infolist():
                name = info.filename
                if re.fullmatch(r"classes\d*\.dex", name) or name.startswith("META-INF/"):
                    continue
                if name not in ("AndroidManifest.xml", "resources.arsc") and not name.startswith("res/"):
                    raise ValueError(f"Unexpected watch face APK entry: {name}")
                target.writestr(info, source.read(info))

        subprocess.run([tool("zipalign"), "-f", "4", str(unsigned), str(aligned)], check=True)
        keystore = os.environ.get("WATCHES_KEYSTORE")
        if keystore:
            alias = os.environ["WATCHES_KEY_ALIAS"]
            store_password = "env:WATCHES_KEYSTORE_PASSWORD"
            key_password = "env:WATCHES_KEY_PASSWORD"
        else:
            keystore = str(Path.home() / ".android/debug.keystore")
            alias = "androiddebugkey"
            store_password = key_password = "pass:android"
            if not Path(keystore).exists():
                Path(keystore).parent.mkdir(parents=True, exist_ok=True)
                subprocess.run([
                    "keytool", "-genkeypair", "-keystore", keystore,
                    "-alias", alias, "-storepass", "android", "-keypass", "android",
                    "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
                    "-dname", "CN=Android Debug,O=Android,C=US", "-noprompt",
                ], check=True)
        subprocess.run([
            tool("apksigner"), "sign", "--ks", keystore,
            "--ks-key-alias", alias, "--ks-pass", store_password,
            "--key-pass", key_password, "--v1-signing-enabled", "false",
            "--out", str(args.output), str(aligned),
        ], check=True)
        subprocess.run([tool("apksigner"), "verify", str(args.output)], check=True)


if __name__ == "__main__":
    main()
