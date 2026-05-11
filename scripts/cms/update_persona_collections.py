"""Update persona multiCollections via Payload CMS REST API.

Usage:
  uv run python scripts/cms/update_persona_collections.py --add ca_federal_data
  uv run python scripts/cms/update_persona_collections.py --slug live-study-immigration --add ca_federal_data
  uv run python scripts/cms/update_persona_collections.py --slug live-study-immigration --set ca_federal,ca_federal_data,ca_edu_algonquin
"""
from __future__ import annotations

import argparse
import json
import sys

import requests

# ── Config (same as backfill_tasks.py) ──
PAYLOAD_URL = "http://localhost:3001"
EMAIL = "402707192@qq.com"
PASSWORD = "123123"


def login() -> tuple[str, dict]:
    r = requests.post(
        f"{PAYLOAD_URL}/api/users/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    token = r.json().get("token")
    if not token:
        print("Login failed:", r.text)
        sys.exit(1)
    headers = {"Authorization": f"JWT {token}", "Content-Type": "application/json"}
    print("✅ Logged in")
    return token, headers


def main():
    p = argparse.ArgumentParser(description="Update persona multiCollections")
    p.add_argument("--slug", default="live-study-immigration")
    p.add_argument("--add", help="Collection name to add")
    p.add_argument("--set", help="Full replacement (comma-separated)")
    args = p.parse_args()

    _, headers = login()

    # Get persona
    r = requests.get(
        f"{PAYLOAD_URL}/api/consulting-personas",
        params={"where[slug][equals]": args.slug, "limit": 1},
        headers=headers,
    )
    docs = r.json().get("docs", [])
    if not docs:
        print(f"❌ Persona '{args.slug}' not found")
        return

    persona = docs[0]
    pid = persona["id"]
    raw = persona.get("multiCollections", "[]")
    current = json.loads(raw) if isinstance(raw, str) else (raw or [])
    print(f"Persona: {args.slug} (ID: {pid})")
    print(f"Current: {current}")

    # Compute new
    if args.set:
        new_cols = [c.strip() for c in args.set.split(",") if c.strip()]
    elif args.add:
        new_cols = list(current)
        if args.add not in new_cols:
            try:
                idx = new_cols.index("ca_federal") + 1
            except ValueError:
                idx = 0
            new_cols.insert(idx, args.add)
        else:
            print(f"'{args.add}' already present, no change needed")
            return
    else:
        print("No --add or --set specified")
        return

    print(f"New:     {new_cols}")

    # Update
    r = requests.patch(
        f"{PAYLOAD_URL}/api/consulting-personas/{pid}",
        json={"multiCollections": json.dumps(new_cols)},
        headers=headers,
    )
    r.raise_for_status()
    print(f"✅ Updated!")


if __name__ == "__main__":
    main()
