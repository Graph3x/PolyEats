import json
import sys
import urllib.error
import urllib.request
import uuid

GATEWAY = "http://localhost:8004"

CUSTOMER = {
    "email": f"customer-{uuid.uuid4().hex[:8]}@polyeats.test",
    "password": "customer",
}
customer_id = None

# Must be a row in geocoding's gazetteer, or the geocode call returns NOT_FOUND.
SEED_ADDRESS = {
    "ownerType": "user",
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


def register():
    global customer_id
    created = call("POST", f"{GATEWAY}/account/accounts", CUSTOMER)
    customer_id = created["accountId"] if created else None


def address():
    tokens = login()
    if not tokens:
        return
    token = tokens["access_token"]

    addresses = f"{GATEWAY}/address/addresses"
    seed = SEED_ADDRESS | {"ownerId": customer_id}
    created = call("POST", addresses, seed, token=token)
    if not created:
        return
    created_id = created["id"]

    call("GET", f"{addresses}/{created_id}", token=token)
    call("GET", f"{addresses}?ownerType=user&ownerId={customer_id}", token=token)
    call(
        "PUT",
        f"{addresses}/{created_id}",
        seed | {"street": "Kostelni", "buildingNumber": "3"},
        token=token,
    )
    call("DELETE", f"{addresses}/{created_id}", token=token)

    call("GET", f"{addresses}/{created_id}", expect=404, token=token)
    call(
        "POST",
        addresses,
        seed | {"street": "Nowhere"},
        expect=422,
        token=token,
    )
    call(
        "POST",
        addresses,
        seed | {"ownerId": "acc-other"},
        expect=403,
        token=token,
    )


def user():
    tokens = login()
    if not tokens:
        return
    token = tokens["access_token"]

    users = f"{GATEWAY}/user/users"
    me = f"{users}/{customer_id}"
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
    mine = f"{restaurants}/{customer_id}"
    profile = {"name": "Bistro", "cuisine": "czech"}

    call("POST", restaurants, profile, token=token)
    call("GET", restaurants, token=token)
    call("GET", mine, token=token)
    call("PUT", mine, profile | {"name": "Renamed"}, token=token)
    call("GET", f"{mine}/addresses", token=token)
    call("DELETE", mine, token=token)


def menu():
    tokens = login()
    if not tokens:
        return
    token = tokens["access_token"]

    items = f"{GATEWAY}/menu/items"
    dish = {"restaurantId": customer_id, "name": "Svickova", "price": 18900}

    created = call("POST", items, dish, token=token)
    call("POST", items, dish | {"price": -1}, expect=400, token=token)
    call("POST", items, dish | {"restaurantId": "acc-other"}, expect=403, token=token)
    if created:
        mine = f"{items}/{created['id']}"
        call("GET", mine, token=token)
        call("PUT", mine, dish | {"available": False}, token=token)
        call("DELETE", mine, token=token)
        call("GET", mine, expect=404, token=token)

    call("GET", f"{items}?restaurantId={customer_id}", token=token)
    call("DELETE", f"{items}?restaurantId={customer_id}", token=token)

    leftover = call("POST", items, dish, token=token)
    call("DELETE", f"{GATEWAY}/restaurant/restaurants/{customer_id}", token=token)
    if leftover:
        call("GET", f"{items}/{leftover['id']}", expect=404, token=token)


def courier_profile():
    tokens = login()
    if not tokens:
        return
    token = tokens["access_token"]

    couriers = f"{GATEWAY}/courier-profile/couriers"
    mine = f"{couriers}/{customer_id}"
    profile = {"name": "Courier", "vehicle": "bike", "status": "offline"}

    call("POST", couriers, profile, token=token)
    call("POST", couriers, profile, expect=409, token=token)
    call("GET", mine, token=token)
    call("PUT", mine, profile | {"vehicle": "car"}, token=token)
    call("PUT", f"{mine}/status", {"status": "online"}, token=token)
    call("DELETE", mine, expect=204, token=token)


def review():
    tokens = login()
    if not tokens:
        return
    token = tokens["access_token"]

    users = f"{GATEWAY}/user/users"
    restaurants = f"{GATEWAY}/restaurant/restaurants"
    call("POST", users, {"name": "Reviewer", "email": CUSTOMER["email"]}, token=token)
    call("POST", restaurants, {"name": "Bistro", "cuisine": "czech"}, token=token)

    reviews = f"{GATEWAY}/review/reviews"
    draft = {"restaurantId": customer_id, "rating": 5, "text": "Great"}
    unknown = draft | {"restaurantId": "acc-other"}

    created = call("POST", reviews, draft, token=token)
    call("POST", reviews, unknown, expect=422, token=token)
    if created:
        mine = f"{reviews}/{created['id']}"
        call("GET", f"{reviews}?restaurantId={customer_id}", token=token)
        call("GET", mine, token=token)
        call("PUT", mine, {"rating": 4, "text": None}, token=token)
        call("DELETE", mine, expect=204, token=token)

    call("DELETE", f"{users}/{customer_id}", token=token)
    call("DELETE", f"{restaurants}/{customer_id}", token=token)


def cart():
    tokens = login()
    if not tokens:
        return
    token = tokens["access_token"]

    users = f"{GATEWAY}/user/users"
    restaurants = f"{GATEWAY}/restaurant/restaurants"
    addresses = f"{GATEWAY}/address/addresses"
    items = f"{GATEWAY}/menu/items"
    mine = f"{GATEWAY}/cart/carts/{customer_id}"
    dish = {"restaurantId": customer_id, "name": "Svickova", "price": 18900}

    call("POST", restaurants, {"name": "Bistro", "cuisine": "czech"}, token=token)
    located = SEED_ADDRESS | {"ownerType": "restaurant", "ownerId": customer_id}
    call("POST", addresses, located, token=token)
    available = call("POST", items, dish, token=token)
    sold_out = call("POST", items, dish | {"available": False}, token=token)
    if not available or not sold_out:
        return
    line = f"{mine}/items/{available['id']}"

    call("PUT", line, {"quantity": 2}, token=token)
    call("GET", mine, expect=422, token=token)

    call("POST", users, {"name": "Customer", "email": CUSTOMER["email"]}, token=token)
    call("POST", addresses, SEED_ADDRESS | {"ownerId": customer_id}, token=token)

    call("PUT", line, {"quantity": 0}, expect=400, token=token)
    unavailable = f"{mine}/items/{sold_out['id']}"
    call("PUT", unavailable, {"quantity": 1}, expect=409, token=token)
    call("PUT", f"{mine}/items/unknown", {"quantity": 1}, expect=422, token=token)
    call(
        "PUT",
        f"{GATEWAY}/cart/carts/acc-other/items/{available['id']}",
        {"quantity": 1},
        expect=403,
        token=token,
    )

    # 2 x 18900 with NEIGHBOUR20, the best of the four promotions that match.
    priced = call("GET", mine, token=token)
    if priced and priced["total"] != 30240:
        failures.append(f"GET {mine} total {priced['total']} (want 30240)")

    call("DELETE", line, token=token)
    call("DELETE", mine, token=token)
    call("GET", mine, token=token)

    call("DELETE", f"{users}/{customer_id}", token=token)
    call("DELETE", f"{restaurants}/{customer_id}", token=token)


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


def account():
    accounts = f"{GATEWAY}/account/accounts"
    me = f"{accounts}/{customer_id}"

    call("POST", accounts, CUSTOMER, expect=409)
    tokens = login()
    if not tokens:
        return

    CUSTOMER["password"] = "changed"
    call(
        "PUT",
        f"{me}/password",
        {"password": "changed"},
        token=tokens["access_token"],
    )
    tokens = login()
    if not tokens:
        return

    call("DELETE", me, token=tokens["access_token"])
    call(
        "POST",
        f"{GATEWAY}/auth/refresh",
        {"refresh_token": tokens["refresh_token"]},
        expect=401,
    )


SERVICES = [
    address,
    user,
    restaurant,
    menu,
    courier_profile,
    review,
    cart,
    gateway,
    account,
]


def main():
    print("register")
    register()

    for service in SERVICES:
        print(service.__name__)
        service()

    if failures:
        print(f"\n{len(failures)} failed")
        sys.exit(1)
    print("\nall ok")


if __name__ == "__main__":
    main()
