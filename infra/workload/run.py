import json
import sys
import urllib.error
import urllib.request

GEOCODING = "http://localhost:8000"
ORDER_TRACKING = "http://localhost:8001"
ADDRESS = "http://localhost:8002"

# Must be a row in geocoding's gazetteer, or the geocode call returns NOT_FOUND.
SEED_ADDRESS = {
    "ownerType": "user",
    "ownerId": "1",
    "street": "Skolni",
    "buildingNumber": "2",
    "city": "Krecovice",
    "postalCode": "25756",
}

failures = []


def call(method, url, body=None, expect=200):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
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


def geocoding():
    call("GET", f"{GEOCODING}/health")


def order_tracking():
    call("GET", f"{ORDER_TRACKING}/health")
    call("GET", f"{ORDER_TRACKING}/test")


def address():
    call("GET", f"{ADDRESS}/health")

    created = call("POST", f"{ADDRESS}/addresses", SEED_ADDRESS)
    if not created:
        return
    created_id = created["id"]

    call("GET", f"{ADDRESS}/addresses/{created_id}")
    call("GET", f"{ADDRESS}/addresses?ownerType=user&ownerId=1")
    call(
        "PUT",
        f"{ADDRESS}/addresses/{created_id}",
        SEED_ADDRESS | {"street": "Kostelni", "buildingNumber": "3"},
    )
    call("DELETE", f"{ADDRESS}/addresses/{created_id}")

    call("GET", f"{ADDRESS}/addresses/{created_id}", expect=404)
    call(
        "POST", f"{ADDRESS}/addresses", SEED_ADDRESS | {"street": "Nowhere"}, expect=422
    )


SERVICES = [geocoding, order_tracking, address]


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
