import time, requests
from neo4j import GraphDatabase, bearer_auth

TENANT_ID = "2b0d1330-312c-497a-a034-f2374ee0be2a"
CLIENT_ID = "277d91dc-0278-48fd-bdb0-ab8b93087291"

ISSUER     = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
WELL_KNOWN = f"{ISSUER}/.well-known/openid-configuration"

SCOPES    = "openid profile email offline_access"
NEO4J_URI = "neo4j://34.22.141.54:7687"


def get_well_known():
    r = requests.get(WELL_KNOWN, timeout=20)
    r.raise_for_status()
    return r.json()


def get_id_token_via_device_flow():
    wk = get_well_known()

    device_authz_endpoint = wk.get("device_authorization_endpoint")
    if not device_authz_endpoint:
        raise RuntimeError("IDP does not advertise device_authorization_endpoint in OIDC discovery.")
    token_endpoint = wk["token_endpoint"]

    r = requests.post(
        device_authz_endpoint,
        data={"client_id": CLIENT_ID, "scope": SCOPES},
        timeout=20,
    )
    r.raise_for_status()
    device = r.json()

    print("Go to      :", device["verification_uri"])
    print("Enter code :", device["user_code"])
    if "verification_uri_complete" in device:
        print("Direct link:", device["verification_uri_complete"])

    device_code = device["device_code"]
    interval    = int(device.get("interval", 5))
    deadline    = time.time() + int(device["expires_in"])

    token = None
    while time.time() < deadline:
        resp = requests.post(
            token_endpoint,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": CLIENT_ID,
                "device_code": device_code,
            },
            headers={"Accept": "application/json"},
            timeout=20,
        )

        if resp.status_code == 200:
            token = resp.json()
            break

        data = resp.json()
        err  = data.get("error")
        if err == "authorization_pending":
            time.sleep(interval)
            continue
        if err == "slow_down":
            interval += 5
            time.sleep(interval)
            continue

        raise RuntimeError(f"Device flow error: {data}")

    if not token:
        raise TimeoutError("Device code expired before authentication completed.")

    id_token = token.get("id_token")
    if not id_token:
        raise RuntimeError("No id_token returned. Check scopes (openid) and IDP configuration.")

    return id_token


id_token = get_id_token_via_device_flow()

print(id_token)

with GraphDatabase.driver(NEO4J_URI, auth=bearer_auth(id_token)) as driver:
    with driver.session() as s:
        print("Current user:", s.run("SHOW CURRENT USER").single())