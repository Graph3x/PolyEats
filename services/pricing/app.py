import os
from typing import Any

import httpx
from auth import Caller, verify
from flask import Flask, Response, request

MENU_URL = os.environ["MENU_URL"]
PROMOTION_URL = os.environ["PROMOTION_URL"]

app = Flask(__name__)
client = httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0))


def fetch(url: str, caller: Caller, restaurant_id: str) -> Any:
    response = client.get(
        url,
        params={"restaurantId": restaurant_id},
        headers={"Authorization": f"Bearer {caller.token}"},
    )
    response.raise_for_status()
    return response.json()


def valid_line(line: Any) -> bool:
    return (
        isinstance(line, dict)
        and isinstance(line.get("itemId"), str)
        and type(line.get("quantity")) is int
        and line["quantity"] >= 1
    )


def valid(body: Any) -> bool:
    if not isinstance(body, dict):
        return False
    restaurant_id, lines = body.get("restaurantId"), body.get("lines")
    return (
        isinstance(restaurant_id, str)
        and restaurant_id != ""
        and isinstance(lines, list)
        and len(lines) > 0
        and all(valid_line(line) for line in lines)
    )


def priced(line: dict[str, Any], item: dict[str, Any] | None) -> dict[str, Any]:
    available = item is not None and item["available"]
    return {
        "itemId": line["itemId"],
        "name": item["name"] if item else None,
        "unitPrice": item["price"] if item else None,
        "quantity": line["quantity"],
        "lineTotal": item["price"] * line["quantity"] if available else 0,
        "available": available,
    }


@app.errorhandler(httpx.HTTPStatusError)
def dependency_rejected(e: httpx.HTTPStatusError):
    return Response(status=422 if e.response.status_code in (404, 422) else 502)


@app.errorhandler(httpx.TimeoutException)
def dependency_timed_out(e: httpx.TimeoutException):
    return Response(status=504)


@app.errorhandler(httpx.HTTPError)
def dependency_failed(e: httpx.HTTPError):
    return Response(status=502)


@app.get("/health")
def health():
    return Response(status=200)


@app.post("/price")
def price():
    caller = verify()
    body = request.get_json(silent=True)
    if not valid(body):
        return Response(status=400)
    restaurant_id = body["restaurantId"]

    items = fetch(f"{MENU_URL}/items", caller, restaurant_id)
    menu = {item["id"]: item for item in items}
    lines = [priced(line, menu.get(line["itemId"])) for line in body["lines"]]
    subtotal = sum(line["lineTotal"] for line in lines)

    promotion = None
    if any(line["available"] for line in lines):
        offers = fetch(f"{PROMOTION_URL}/promotions/eligible", caller, restaurant_id)
        promotion = min(offers, key=lambda p: (-p["percent"], p["code"]), default=None)
    discount = subtotal * promotion["percent"] // 100 if promotion else 0

    return {
        "restaurantId": restaurant_id,
        "lines": lines,
        "subtotal": subtotal,
        "promotion": promotion,
        "discount": discount,
        "total": subtotal - discount,
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
