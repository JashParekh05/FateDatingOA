#!/usr/bin/env python3
"""One-time TikTok OAuth helper.

Prints the authorize URL for your developer app; you open it in a browser
logged in as the TikTok account that should own the posts, approve, then
paste the `code` from the redirected URL back here. The script exchanges it
and prints the refresh token to put in .env / GitHub Actions secrets.

Usage:  python scripts/tiktok_auth.py
"""

import os
import secrets
import sys
import urllib.parse

import requests
from dotenv import load_dotenv

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.publish"


def ask(prompt: str, env_var: str) -> str:
    value = os.environ.get(env_var, "").strip()
    if value:
        print(f"{prompt}: using value from {env_var}")
        return value
    return input(f"{prompt}: ").strip()


def main() -> int:
    load_dotenv()
    client_key = ask("Client key", "TIKTOK_CLIENT_KEY")
    client_secret = ask("Client secret", "TIKTOK_CLIENT_SECRET")
    redirect_uri = input(
        "Redirect URI (exactly as registered in your app's Login Kit settings): "
    ).strip()

    state = secrets.token_hex(8)
    url = AUTHORIZE_URL + "?" + urllib.parse.urlencode({
        "client_key": client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
    })

    print(
        "\n1. Open this URL in a browser where you're logged into the TikTok\n"
        "   account that should own the posts:\n\n"
        f"{url}\n\n"
        "2. Approve the permissions. You'll land on your redirect URI — the\n"
        "   page itself can even 404, that's fine.\n"
        "3. Copy the value of the `code` parameter from the address bar.\n"
    )
    code = urllib.parse.unquote(input("Paste the code here: ").strip())

    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    data = resp.json()
    if "refresh_token" not in data:
        print(f"\nToken exchange failed: {data}", file=sys.stderr)
        return 1

    print(
        "\nSuccess! Posting is now bound to TikTok user "
        f"{data.get('open_id', '?')} (scopes: {data.get('scope')}).\n\n"
        "Add these to .env (local) or GitHub Actions secrets:\n\n"
        f"TIKTOK_CLIENT_KEY={client_key}\n"
        f"TIKTOK_CLIENT_SECRET={client_secret}\n"
        f"TIKTOK_REFRESH_TOKEN={data['refresh_token']}\n\n"
        f"(The refresh token is valid for ~1 year; access tokens are minted\n"
        "from it automatically on every run.)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
