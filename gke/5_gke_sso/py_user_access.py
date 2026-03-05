import base64, hashlib, os, secrets, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
import requests
from neo4j import GraphDatabase, bearer_auth

TENANT_ID    = "2b0d1330-312c-497a-a034-f2374ee0be2a"
CLIENT_ID    = "277d91dc-0278-48fd-bdb0-ab8b93087291"

ISSUER       = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
WELL_KNOWN   = f"{ISSUER}/.well-known/openid-configuration"

# Use an Entra SPA redirect URI you configured in the SPA platform
# Example: "http://localhost:8000/callback" (dev) or "https://your-domain/callback" (prod)
REDIRECT_URI = "http://localhost:8000/callback"

# IMPORTANT for Entra SPA token redemption: Origin must match the redirect origin
REDIRECT_ORIGIN = "http://localhost:8000"

# OIDC scopes in the authorize request are fine
SCOPES       = "openid profile email offline_access"

# Neo4j Bolt endpoint (use TLS in real setups)
NEO4J_URI    = "neo4j://34.22.141.54:7687"


def gen_pkce():
    verifier  = base64.urlsafe_b64encode(os.urandom(40)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge

CODE_VERIFIER, CODE_CHALLENGE = gen_pkce()
STATE = secrets.token_urlsafe(24)
NONCE = secrets.token_urlsafe(24)

AUTH_CODE = None
RETURNED_STATE = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global AUTH_CODE, RETURNED_STATE
        qs = parse_qs(urlparse(self.path).query)
        error = qs.get("error", [None])[0]
        if error:
            err_desc = qs.get("error_description", [""])[0]
            self._ok(f"Auth error: {error}. {err_desc}".encode())
            return

        AUTH_CODE = qs.get("code", [None])[0]
        RETURNED_STATE = qs.get("state", [None])[0]
        if not AUTH_CODE:
            self._ok(b"Missing code in redirect.")
            return
        self._ok(b"Login success. You can close this tab.")

    def log_message(self, *args):
        return

    def _ok(self, body: bytes):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

def get_well_known():
    r = requests.get(WELL_KNOWN, timeout=20)
    r.raise_for_status()
    return r.json()

def get_id_token_via_pkce():
    wk = get_well_known()
    auth_endpoint  = wk["authorization_endpoint"]
    token_endpoint = wk["token_endpoint"]

    # Authorization request (browser)
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "code_challenge": CODE_CHALLENGE,
        "code_challenge_method": "S256",
        "state": STATE,
        "nonce": NONCE,
        # Optional but often helpful:
        # "response_mode": "query",
        # "prompt": "select_account",
    }
    url = f"{auth_endpoint}?{urlencode(params)}"
    print("Opening browser for Entra login…")
    webbrowser.open(url)

    # Local callback listener
    server = HTTPServer(("localhost", 8000), Handler)
    while AUTH_CODE is None:
        server.handle_request()

    if RETURNED_STATE != STATE:
        raise RuntimeError(f"State mismatch. Expected {STATE}, got {RETURNED_STATE}")

    # Token request (code redemption)
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "code": AUTH_CODE,
        "code_verifier": CODE_VERIFIER,
    }

    # Entra SPA code redemption requires an Origin header (CORS-style redemption) while Okta may not need it
    headers = {
        "Accept": "application/json",
        "Origin": REDIRECT_ORIGIN,
    }

    resp = requests.post(token_endpoint, data=data, headers=headers, timeout=30)
    if resp.status_code != 200:
        try:
            print("Token error:", resp.json())
        except Exception:
            print("Token error (raw):", resp.text)
        resp.raise_for_status()

    tok = resp.json()

    # Your Neo4j config uses id_token for authentication
    return tok["id_token"]

id_token = get_id_token_via_pkce()

print(id_token)

with GraphDatabase.driver(NEO4J_URI, auth=bearer_auth(id_token)) as driver:
    with driver.session() as s:
        print("Current user:", s.run("SHOW CURRENT USER").single())
