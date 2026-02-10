from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

@dataclass(frozen=True)
class Principal:
    user_id: str
    roles: List[str]
    scopes: List[str]
    claims: Dict[str, Any]


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    access_expires_at: int
    refresh_token: str
    refresh_expires_at: int

class TokenService:

    def __init__(
            self,
            jwt_secret_key: str,
            jwt_algorithm: str,
            access_token_ttl_seconds: int,
            refresh_token_ttl_seconds: int,
            refresh_hash_secret: str,
            issuer: str | None = None,
            audience: str | None = None,
    ):
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.access_token_ttl = access_token_ttl_seconds
        self.refresh_token_ttl = refresh_token_ttl_seconds
        self.refresh_hash_secret = refresh_hash_secret
        self.issuer = issuer
        self.audience = audience


    def issue_acces_token(self, user_id:str, roles:List[str] | None = None, scopes: List[str] | None = None):

        now = datetime.now(datetime.timezone.utc)
        exp_ts = int((now + timedelta(seconds=self.access_token_ttl)).timestamp())
        iat_ts = int(now.timestamp())

        payload: Dict[str, Any] = {
            "sub": user_id,
            "iat": iat_ts,
            "exp": exp_ts,
            "typ": "access",
            "roles": roles,
            "scopes": scopes,
        }
        if self.issuer:
            payload["iss"] = self.issuer
        if self.audience:
            payload["aud"] = self.audience

        token = jwt.encode(payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)
        return token, exp_ts

    def verify_access_token(self, access_token: str) -> Principal:
        try:
            payload = jwt.decode(
                access_token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm],
                issuer=self.issuer if self.issuer else None,
                audience=self.audience if self.audience else None,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": bool(self.issuer),
                    "verify_aud": bool(self.audience),
                },
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="access token expired")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="access token invalid")

        if payload.get("typ") != "access":
            raise HTTPException(status_code=401, detail="access token wrong type")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="access token missing sub")

        roles = payload.get("roles") or []
        scopes = payload.get("scopes") or []

        return Principal(user_id=str(user_id),roles=list(roles),scopes=list(scopes),claims=dict(payload),)

    def extract_bearer_token(self, headers: Dict[str, str]) -> str:
        auth = headers.get("Authorization") or headers.get("authorization")
        if not auth:
            raise HTTPException(status_code=401, detail="authorization header missing")

        parts = auth.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="invalid authorization header format")

        return parts[1]

    def _hmac_hash(self, raw_value: str) -> str:
        return hmac.new(self.refresh_hash_secret.encode("utf-8"),raw_value.encode("utf-8"),hashlib.sha256,).hexdigest()


    def issue_refresh_token(self) -> Tuple[str, str, int]:

        now = datetime.now(timezone.utc)
        exp_ts = int((now + timedelta(seconds=self.refresh_token_ttl)).timestamp())

        raw = secrets.token_urlsafe(64)
        hashed = self._hmac_hash(raw)
        return raw, hashed, exp_ts


    def rotate_refresh_token(self, raw_refresh: str, store: Any, meta: Optional[dict] = None) -> TokenPair:

        old_hash = self._hmac_hash(raw_refresh)
        session = store.get(old_hash)

        if session is None:
            raise HTTPException(status_code=401, detail="refresh token invalid")


        if getattr(session, "revoked_at", None):
            raise HTTPException(status_code=401, detail="refresh token revoked")


        now_ts = int(datetime.now(timezone.utc).timestamp())
        if int(getattr(session, "expires_at", 0)) <= now_ts:
            raise HTTPException(status_code=401, detail="refresh token expired")

        user_id = str(getattr(session, "user_id"))


        new_raw, new_hash, new_exp = self.issue_refresh_token()


        store.revoke(old_hash, replaced_by_hash=new_hash)
        store.save(new_hash, user_id=user_id, expires_at=new_exp, meta=meta)


        access, access_exp = self.issue_access_token(user_id=user_id, roles=[], scopes=[])

        return TokenPair(access_token=access,access_expires_at=access_exp,refresh_token=new_raw,refresh_expires_at=new_exp,)