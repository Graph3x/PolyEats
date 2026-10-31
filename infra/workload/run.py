import json
import sys
import urllib.error
import urllib.request

GEOCODING = "http://localhost:8000"
ORDER_TRACKING = "http://localhost:8001"
ADDRESS = "http://localhost:8002"
AUTH = "http://localhost:8003"
GATEWAY = "http://localhost:8004"
USER = "http://localhost:8005"

CUSTOMER = {"email": "customer@polyeats.test", "password": "customer"}
CUSTOMER_ID = "acc-customer"

# Must be a row in geocoding's gazetteer, or the geocode call returns NOT_FOUND.
SEED_ADDRESS = {
    "ownerType": "user",
    "ownerId": CUSTOMER_ID,
    "street": "Skolni",
    "buildingNumber": "2",
    "city": "Krecovice",
    "postalCode": "25756",
}

failures = []


def call(method, url, body=None, expect=200, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request) as response:
            status, payload = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, payload = error.code, error.read()
    except urllib.error.URLError as error:
        status, payload = 0, str(error.reason).encode()

    print(
        f"  {method:6} {url:52} {status}{'' if status == expect else f' (want {expect})'}"
    )
    if status != expect:
        failures.append(f"{method} {url}")

    return json.loads(payload) if payload.startswith(b"{") else None


def login():
    return call("POST", f"{GATEWAY}/auth/login", CUSTOMER)


def geocoding():
    call("GET", f"{GEOCODING}/health")


def order_tracking():
    call("GET", f"{ORDER_TRACKING}/health")


def address():
    call("GET", f"{ADDRESS}/health")

    tokens = login()
    if not tokens:
        return
    token = tokens["access_token"]

    addresses = f"{GATEWAY}/address/addresses"
    created = call("POST", addresses, SEED_ADDRESS, token=token)
    if not created:
        return
    created_id = created["id"]

    call("GET", f"{addresses}/{created_id}", token=token)
    call("GET", f"{addresses}?ownerType=user&ownerId={CUSTOMER_ID}", token=token)
    call(
        "PUT",
        f"{addresses}/{created_id}",
        SEED_ADDRESS | {"street": "Kostelni", "buildingNumber": "3"},
        token=token,
    )
    call("DELETE", f"{addresses}/{created_id}", token=token)

    call("GET", f"{addresses}/{created_id}", expect=404, token=token)
    call(
        "POST",
        addresses,
        SEED_ADDRESS | {"street": "Nowhere"},
        expect=422,
        token=token,
    )
    call(
        "POST",
        addresses,
        SEED_ADDRESS | {"ownerId": "acc-other"},
        expect=403,
        token=token,
    )


def user():
    call("GET", f"{USER}/health")

    tokens = login()
    if not tokens:
        return
    token = tokens["access_token"]

    users = f"{GATEWAY}/user/users"
    me = f"{users}/{CUSTOMER_ID}"
    profile = {"name": "Customer", "email": CUSTOMER["email"]}

    call("POST", users, profile, token=token)
    call("POST", users, profile, expect=409, token=token)
    call("GET", me, token=token)
    call("PUT", me, profile | {"name": "Renamed"}, token=token)
    call("PUT", f"{users}/acc-other", profile, expect=403, token=token)
    call("GET", f"{me}/addresses", token=token)
    call("DELETE", me, token=token)

    call("GET", me, expect=404, token=token)


def restaurant():
    tokens = login()
    if not tokens:
        return
    token = tokens["access_token"]

    restaurants = f"{GATEWAY}/restaurant/restaurants"
    mine = f"{restaurants}/{CUSTOMER_ID}"
    profile = {"name": "Bistro", "cuisine": "czech"}

    call("POST", restaurants, profile, token=token)
    call("GET", restaurants, token=token)
    call("GET", mine, token=token)
    call("PUT", mine, profile | {"name": "Renamed"}, token=token)
    call("GET", f"{mine}/addresses", token=token)
    call("DELETE", mine, token=token)


def auth():
    call("GET", f"{AUTH}/health")
    call("GET", f"{AUTH}/.well-known/jwks.json")


def gateway():
    call("GET", f"{GATEWAY}/health")

    call("POST", f"{GATEWAY}/auth/login", CUSTOMER | {"password": "wrong"}, expect=401)
    tokens = login()
    if not tokens:
        return
    tokens = call(
        "POST", f"{GATEWAY}/auth/refresh", {"refresh_token": tokens["refresh_token"]}
    )
    if not tokens:
        return

    call("GET", f"{GATEWAY}/order-tracking/tracking/1", expect=401)
    call("GET", f"{GATEWAY}/order-tracking/tracking/1", token=tokens["access_token"])

    call("POST", f"{GATEWAY}/auth/logout", {"refresh_token": tokens["refresh_token"]})
    call(
        "POST",
        f"{GATEWAY}/auth/refresh",
        {"refresh_token": tokens["refresh_token"]},
        expect=401,
    )


SERVICES = [geocoding, order_tracking, address, user, restaurant, auth, gateway]


def main():
    for service in SERVICES:
        print(service.__name__)
        service()

    if failures:
        print(f"\n{len(failures)} failed")
        sys.exit(1)
    print("\nall ok")


if __name__ == "__main__":
    main()
