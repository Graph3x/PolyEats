import os
from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException
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


def verify(authorization: str = Header("")) -> Caller:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, headers=BEARER_CHALLENGE)
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
        raise HTTPException(503)
    except PyJWTError:
        raise HTTPException(401, headers=BEARER_CHALLENGE)
    return Caller(claims["sub"], token)
