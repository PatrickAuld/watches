#!/usr/bin/env python3

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://androidpublisher.googleapis.com/androidpublisher/v3"
UPLOAD_API = "https://androidpublisher.googleapis.com/upload/androidpublisher/v3"


def release_body(track, version_code, version_name, release_notes, rollout_percent):
    if not 1 <= rollout_percent <= 100:
        raise ValueError("rollout-percent must be between 1 and 100")
    if track != "production" and rollout_percent != 100:
        raise ValueError("rollout-percent applies only to the production track")
    release = {
        "name": version_name,
        "versionCodes": [str(version_code)],
        "status": "inProgress" if track == "production" and rollout_percent < 100 else "completed",
        "releaseNotes": [{"language": "en-US", "text": release_notes}],
    }
    if track == "production" and rollout_percent < 100:
        release["userFraction"] = rollout_percent / 100
    return {"releases": [release]}


def api_request(method, url, token, body=None, content_type="application/json"):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    data = body
    if isinstance(body, (dict, list)):
        data = json.dumps(body).encode()
        headers["Content-Type"] = content_type
    elif body is not None:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google Play API returned HTTP {error.code}: {detail}") from error
    if not payload:
        return {}
    return json.loads(payload)


def publish(args):
    token = os.environ.get("PLAY_ACCESS_TOKEN")
    if not token:
        raise ValueError("PLAY_ACCESS_TOKEN is required")
    bundle = Path(args.bundle)
    if not bundle.is_file() or bundle.stat().st_size == 0:
        raise ValueError(f"A non-empty app bundle is required: {bundle}")
    if bundle.suffix != ".aab":
        raise ValueError("The Play release artifact must be an .aab")

    package = urllib.parse.quote(args.package_name, safe=".")
    base = f"{API}/applications/{package}/edits"
    edit = api_request("POST", base, token, {})
    edit_id = urllib.parse.quote(edit["id"], safe="")
    edit_url = f"{base}/{edit_id}"
    try:
        uploaded = api_request(
            "POST",
            f"{UPLOAD_API}/applications/{package}/edits/{edit_id}/bundles?uploadType=media",
            token,
            bundle.read_bytes(),
            "application/octet-stream",
        )
        version_code = uploaded["versionCode"]
        track = urllib.parse.quote(args.track, safe="")
        api_request(
            "PUT",
            f"{edit_url}/tracks/{track}",
            token,
            release_body(args.track, version_code, args.version_name, args.release_notes, args.rollout_percent),
        )
        api_request("POST", f"{edit_url}:commit", token, {})
    except Exception:
        try:
            api_request("DELETE", edit_url, token)
        except Exception:
            pass
        raise
    print(f"Submitted {args.package_name} version {args.version_name} (versionCode {version_code}) to {args.track}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--track", choices=("internal", "alpha", "beta", "production"), required=True)
    parser.add_argument("--version-name", required=True)
    parser.add_argument("--release-notes", required=True)
    parser.add_argument("--rollout-percent", type=int, default=100)
    args = parser.parse_args()
    try:
        publish(args)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
