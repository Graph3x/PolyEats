import os
from dataclasses import dataclass

import jwt
from flask import Response, abort, request
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

JWT_ISSUER = "auth"
BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}

jwks = jwt.PyJWKClient(
    os.environ["JWKS_URL"], lifespan=3600, cooldown_duration=10, timeout=5
)


@dataclass(frozen=True)
class Caller:
    subject: str
    token: str


def verify() -> Caller:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        abort(Response(status=401, headers=BEARER_CHALLENGE))
    token = authorization.removeprefix("Bearer ")
    try:
        key = jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "sub"]},
        )
    except PyJWKClientConnectionError:
        abort(Response(status=503))
    except PyJWTError:
        abort(Response(status=401, headers=BEARER_CHALLENGE))
    return Caller(claims["sub"], token)
