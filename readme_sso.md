# SSO Configuration

## Supported authentication flows

Neo4j does not store or manage refresh tokens. Token lifecycle management is the responsibility of the client.

Neo4j Enterprise supports OIDC-based SSO. 

The following flows are supported:

| Flow | Use case |
|------|----------|
| **PKCE** (`auth_flow=pkce`) | Interactive browser login (Neo4j Browser, Bloom) |
| **Implicit** (`auth_flow=implicit`) | Legacy browser clients — not recommended |
| **External token** (bearer) | Programmatic access — client acquires a token externally and passes it to Neo4j |

Neo4j acts as a **resource server**: it validates incoming tokens (signature, issuer, audience, expiry) and maps claims (e.g. `email`, group membership) to internal users and roles. It does **not** issue tokens itself.

---

## Scenarios

### 1. Neo4j Browser / Bloom (web UI)
- Flow: **PKCE**
- The browser redirects the user to the IdP login page.
- After login, the IdP sends back an authorization code; the browser computes the PKCE verifier/challenge using crypto.subtle, then exchanges the code for tokens via a secure fetch call.
- The `id_token` or `access_token` is then sent to Neo4j as a bearer token.
- Requires **HTTPS** (or `http://localhost` for local dev) because of crypto.subtle usage.

### 2. Python / CLI / automation scripts
- Flow: Authorization Code + PKCE (executed by the script)
- The script opens the browser only for the interactive user authentication against the IdP.
- The authorization code exchange is done entirely in Python — not by the browser.
- The resulting `id_token` is passed directly to the Neo4j driver as a bearer token.
- Works without HTTPS on the Neo4j HTTP endpoint because no browser-based PKCE is involved. However, TLS for Bolt is still strongly recommended in production.

### 3. Server-to-server / service accounts
- Flow: **Client credentials** (token acquired outside Neo4j, passed as bearer)
- No user interaction required.
- There is not ID token, only acces token, sub usually represent the application, not a human user
- The application authenticates to the IdP with a client ID + secret (or certificate) and passes the resulting access token to Neo4j.

---


### Why browsers require a secure context

PKCE requires generating a code verifier/challenge pair. Browsers implement this using the `crypto.subtle` Web Crypto API, which is **only available in secure contexts**:
- `https://` — any HTTPS origin
- `http://localhost` — localhost is special-cased as secure by all modern browsers

Older browsers may not implement this restriction consistently, which explains the different error behavior observed.

### Why Python is not affected

In a Python-based PKCE flow:
- The browser is used **only** for the interactive user login against the IdP (it just opens a URL).
- The **authorization code exchange** — including the PKCE verifier — is performed directly by the Python code via an HTTP POST to the IdP token endpoint.
- `crypto.subtle` is never involved; Python handles all cryptographic operations natively.
- As a result, the secure-context requirement does not apply, and the Neo4j connection itself can use plain `bolt://` or `neo4j://`.