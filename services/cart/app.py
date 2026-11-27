import json
import os
from typing import Annotated, Any
from urllib.parse import quote

import httpx
import redis
import uvicorn
from auth import Caller, verify
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

TTL = 7 * 24 * 60 * 60
MENU_URL = os.environ["MENU_URL"]
PRICING_URL = os.environ["PRICING_URL"]

app = FastAPI()
store = redis.Redis.from_url(os.environ["VALKEY_URL"], decode_responses=True)
client = httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0))


class Line(BaseModel):
    quantity: int = Field(ge=1, strict=True)


def key(account_id: str) -> str:
    return f"cart:{account_id}"


def require_owner(caller: Caller, account_id: str) -> None:
    if caller.subject != account_id:
        raise HTTPException(403)


def call(method: str, url: str, caller: Caller, **kwargs: Any) -> Any:
    response = client.request(
        method, url, headers={"Authorization": f"Bearer {caller.token}"}, **kwargs
    )
    response.raise_for_status()
    return response.json()


def price(caller: Caller, restaurant_id: str, lines: list[dict[str, Any]]) -> Any:
    body = {"restaurantId": restaurant_id, "lines": lines}
    return call("POST", f"{PRICING_URL}/price", caller, json=body)


@app.exception_handler(RequestValidationError)
def invalid_request(request: Request, e: RequestValidationError):
    return Response(status_code=400)


@app.exception_handler(httpx.HTTPStatusError)
def dependency_rejected(request: Request, e: httpx.HTTPStatusError):
    return Response(status_code=422 if e.response.status_code in (404, 422) else 502)


@app.exception_handler(httpx.TimeoutException)
def dependency_timed_out(request: Request, e: httpx.TimeoutException):
    return Response(status_code=504)


@app.exception_handler(httpx.HTTPError)
def dependency_failed(request: Request, e: httpx.HTTPError):
    return Response(status_code=502)


@app.get("/health")
def health():
    return Response(status_code=200)


@app.get("/carts/{account_id}")
def get_cart(account_id: str, caller: Annotated[Caller, Depends(verify)]):
    require_owner(caller, account_id)
    groups: dict[str, list[dict[str, Any]]] = {}
    for item_id, stored in store.hgetall(key(account_id)).items():
        line = json.loads(stored)
        groups.setdefault(line["restaurantId"], []).append(
            {"itemId": item_id, "quantity": line["quantity"]}
        )

    restaurants = [
        price(caller, restaurant_id, lines)
        for restaurant_id, lines in sorted(groups.items())
    ]
    return {
        "accountId": account_id,
        "restaurants": restaurants,
        "total": sum(restaurant["total"] for restaurant in restaurants),
    }


@app.put("/carts/{account_id}/items/{item_id}")
def put_item(
    account_id: str,
    item_id: str,
    line: Line,
    caller: Annotated[Caller, Depends(verify)],
):
    require_owner(caller, account_id)
    item = call("GET", f"{MENU_URL}/items/{quote(item_id, safe='')}", caller)
    if not item["available"]:
        raise HTTPException(409)

    stored = json.dumps(
        {"restaurantId": item["restaurantId"], "quantity": line.quantity}
    )
    with store.pipeline() as transaction:
        transaction.hset(key(account_id), item_id, stored)
        transaction.expire(key(account_id), TTL)
        transaction.execute()
    return Response(status_code=200)


@app.delete("/carts/{account_id}/items/{item_id}")
def delete_item(
    account_id: str, item_id: str, caller: Annotated[Caller, Depends(verify)]
):
    require_owner(caller, account_id)
    store.hdel(key(account_id), item_id)
    return Response(status_code=200)


@app.delete("/carts/{account_id}")
def delete_cart(account_id: str, caller: Annotated[Caller, Depends(verify)]):
    require_owner(caller, account_id)
    store.delete(key(account_id))
    return Response(status_code=200)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
