"""
Get a Google OAuth2 refresh token for the Calendar API.

Prerequisites — do these once in the Google Cloud Console:

  1. Go to https://console.cloud.google.com
  2. Create a project (or select an existing one)
  3. Enable "Google Calendar API"
     (APIs & Services -> Library -> search "Google Calendar API" -> Enable)
  4. Configure the OAuth consent screen
     (APIs & Services -> OAuth consent screen -> External -> fill required fields)
  5. Create an OAuth 2.0 Client ID
     (APIs & Services -> Credentials -> Create Credentials -> OAuth client ID)
     Either "Desktop app" or "Web application" works.
     If Web: add http://localhost:8080/ to Authorized redirect URIs.
  6. Download the JSON -> save as `credentials.json` in the repo root
  7. Run this script:
       python scripts/get_refresh_token.py
  8. A browser window will open for consent. Approve access.
  9. Copy the printed values into /opt/apigame/config/.env on the droplet.

If refresh_token is None, revoke the app at https://myaccount.google.com/permissions
and re-run this script.
"""

import json
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Missing dependency. Install it with:")
    print("  pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Look for credentials.json in repo root (parent of scripts/)
repo_root = Path(__file__).resolve().parent.parent
credentials_path = repo_root / "credentials.json"

if not credentials_path.exists():
    print(f"ERROR: {credentials_path} not found.")
    print("Download it from Google Cloud Console (OAuth 2.0 Client ID -> Download JSON)")
    print("and save it as credentials.json in the repo root.")
    sys.exit(1)

# Detect client type — "web" or "installed" (Desktop app).
# InstalledAppFlow expects "installed" key. If the JSON has "web" instead,
# rewrite it on the fly so the flow works with a local redirect.
with open(credentials_path) as f:
    cred_data = json.load(f)

if "web" in cred_data and "installed" not in cred_data:
    print("Detected 'Web application' client type — adapting for local flow.")
    web = cred_data["web"]
    # Convert to "installed" format so InstalledAppFlow accepts it
    # Note: redirect URI validation happens server-side at Google, not in the JSON file.
    cred_data = {"installed": {
        "client_id": web["client_id"],
        "client_secret": web["client_secret"],
        "auth_uri": web.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": web.get("token_uri", "https://oauth2.googleapis.com/token"),
        "redirect_uris": ["http://localhost"],
    }}
    # Write adapted version to a temp file
    adapted_path = repo_root / ".credentials_adapted.json"
    with open(adapted_path, "w") as f:
        json.dump(cred_data, f)
    credentials_path = adapted_path
    print()

print(f"Using credentials from: {credentials_path}")
print("Opening browser for OAuth consent...")
print()

flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes=SCOPES)
creds = flow.run_local_server(port=8080)

# Extract values
refresh_token = creds.refresh_token
client_id = creds.client_id
client_secret = creds.client_secret

if not refresh_token:
    print("WARNING: refresh_token is None!")
    print("This usually means consent was already granted.")
    print("Go to https://myaccount.google.com/permissions, revoke the app, and re-run.")
    sys.exit(1)

print("=" * 60)
print("SUCCESS — copy these into /opt/apigame/config/.env")
print("=" * 60)
print()
print(f"GOOGLE_CLIENT_ID={client_id}")
print(f"GOOGLE_CLIENT_SECRET={client_secret}")
print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
print()
print("=" * 60)
print()
print("To fill in the droplet .env:")
print(f'  ssh root@162.243.231.61 "nano /opt/apigame/config/.env"')
print()
print("To verify the token works:")
print(f'  curl -s -X POST https://oauth2.googleapis.com/token \\')
print(f'    -d "client_id={client_id}&client_secret={client_secret}'
      f'&refresh_token={refresh_token}&grant_type=refresh_token" \\')
print(f'    | python3 -m json.tool')
