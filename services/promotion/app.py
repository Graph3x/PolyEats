import os
from typing import Any
from urllib.parse import quote

import psycopg
import requests
from auth import Caller, verify
from flask import Flask, Response, request
from psycopg.rows import dict_row

TIMEOUT = (2, 5)
USER_URL = os.environ["USER_URL"]
RESTAURANT_URL = os.environ["RESTAURANT_URL"]

app = Flask(__name__)


def connect() -> psycopg.Connection:
    return psycopg.connect(
        os.environ["POSTGRES_URL"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        row_factory=dict_row,
    )


def fetch(url: str, caller: Caller) -> Any:
    response = requests.get(
        url, headers={"Authorization": f"Bearer {caller.token}"}, timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def cities(addresses: list[dict[str, Any]]) -> list[str]:
    return [address["city"] for address in addresses]


@app.errorhandler(requests.HTTPError)
def dependency_rejected(e: requests.HTTPError):
    return Response(status=422 if e.response.status_code == 404 else 502)


@app.errorhandler(requests.Timeout)
def dependency_timed_out(e: requests.Timeout):
    return Response(status=504)


@app.errorhandler(requests.RequestException)
def dependency_failed(e: requests.RequestException):
    return Response(status=502)


@app.get("/health")
def health():
    return Response(status=200)


@app.get("/promotions/eligible")
def eligible():
    caller = verify()
    restaurant_id = quote(request.args["restaurantId"], safe="")
    restaurant = f"{RESTAURANT_URL}/restaurants/{restaurant_id}"
    cuisine = fetch(restaurant, caller)["cuisine"]
    restaurant_cities = cities(fetch(f"{restaurant}/addresses", caller))
    customer_cities = cities(fetch(f"{USER_URL}/users/{caller.subject}/addresses", caller))

    with connect() as connection:
        return connection.execute(
            """
            SELECT code, name, percent FROM promotions
            WHERE (cuisine IS NULL OR cuisine = %s)
              AND (restaurant_city IS NULL OR restaurant_city = ANY(%s))
              AND (customer_city IS NULL OR customer_city = ANY(%s))
            """,
            (cuisine, restaurant_cities, customer_cities),
        ).fetchall()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
