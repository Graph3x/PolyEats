import json
import uuid
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

Reply = tuple[int, dict[str, Any] | None]

refundable: dict[str, int] = {}
replies: dict[str, Reply] = {}


def positive(value: Any) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(value)
    return value


def charge(body: dict[str, Any], key: str | None) -> Reply:
    if key in replies:
        return replies[key]
    amount = positive(body["amount"])
    declined = amount % 10 == 1
    charge_id = uuid.uuid4().hex
    refundable[charge_id] = 0 if declined else amount
    reply = 201, {"id": charge_id, "status": "declined" if declined else "authorized"}
    if key:
        replies[key] = reply
    return reply


def refund(body: dict[str, Any], key: str | None) -> Reply:
    charge_id, amount = body["chargeId"], positive(body["amount"])
    if charge_id not in refundable:
        return 404, None
    if amount > refundable[charge_id]:
        return 422, None
    refundable[charge_id] -= amount
    return 201, {"id": uuid.uuid4().hex, "status": "refunded"}


def message(body: dict[str, Any], key: str | None) -> Reply:
    fields = ("recipient", "channel", "body")
    if not all(isinstance(body[field], str) for field in fields):
        raise ValueError(body)
    return 202, {"id": uuid.uuid4().hex}


ROUTES: dict[tuple[str, str], Callable[[dict[str, Any], str | None], Reply]] = {
    ("api.payments.example", "/charges"): charge,
    ("api.payments.example", "/refunds"): refund,
    ("push.notify.example", "/messages"): message,
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.reply(200 if self.path == "/health" else 404, None)

    def do_POST(self) -> None:
        host = self.headers.get("Host", "").partition(":")[0]
        route = ROUTES.get((host, self.path))
        if route is None:
            return self.reply(404, None)
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            status, payload = route(body, self.headers.get("Idempotency-Key"))
        except (KeyError, TypeError, ValueError):
            status, payload = 400, None
        self.reply(status, payload)

    def reply(self, status: int, payload: dict[str, Any] | None) -> None:
        data = json.dumps(payload).encode() if payload is not None else b""
        self.send_response(status)
        if data:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
