from __future__ import annotations
from dataclasses import dataclass
import os
from typing import Optional


def _env_str(key: str, default: Optional[str] = None) -> str:
    val = os.getenv(key, default)
    if val is None:
        return ""
    val = val.strip()
    if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
        val = val[1:-1]
    return val


def _env_int(key: str, default: int) -> int:
    return int(_env_str(key, str(default)))


def _env_float(key: str, default: float) -> float:
    return float(_env_str(key, str(default)))


@dataclass(frozen=True)
class Settings:

    env: str
    token_url: str
    max_body_bytes: int
    upstream_connect_timeout: float
    upstream_read_timeout: float
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    refresh_hash_secret: str
    swagger_user: str
    swagger_pass: str
    mongo_host: str
    mongo_port: int
    mongo_root_username: str
    mongo_root_password: str
    mongo_db_name: str
    mongodb_uri: str
    redis_url: str

    @classmethod
    def from_env(cls) -> "Settings":

        token_expire_minutes = _env_int("TOKEN_EXPIRE", "")
        access_ttl_seconds = token_expire_minutes * 60

        refresh_expire_days = _env_int("REFRESH_EXPIRE_DAYS", "")
        refresh_ttl_seconds = refresh_expire_days * 24 * 60 * 60

        return cls(
            env=_env_str("ENV", "dev"),

            token_url=_env_str("TOKEN_URL", "/login"),
            max_body_bytes=_env_int("MAX_BODY_BYTES", ""),

            upstream_connect_timeout=_env_float("UPSTREAM_CONNECT_TIMEOUT", ""),
            upstream_read_timeout=_env_float("UPSTREAM_READ_TIMEOUT", ""),

            jwt_secret_key=_env_str("SECRET_KEY", "dev-secret"),
            jwt_algorithm=_env_str("ALGORITHM", "HS256"),
            access_token_ttl_seconds=access_ttl_seconds,
            refresh_token_ttl_seconds=refresh_ttl_seconds,

            refresh_hash_secret=_env_str("HASH_PEPPER", "refresh-dev-secret"),

            swagger_user=_env_str("SWAGGER_USER", ""),
            swagger_pass=_env_str("SWAGGER_PASS", ""),

            mongo_host=_env_str("MONGO_HOST", ""),
            mongo_port=_env_int("MONGO_PORT", ""),
            mongo_root_username=_env_str("MONGO_INITDB_ROOT_USERNAME", ""),
            mongo_root_password=_env_str("MONGO_INITDB_ROOT_PASSWORD", ""),
            mongo_db_name=_env_str("MONGO_DB_NAME", ""),
            mongodb_uri=_env_str("MONGODB_URI", ""),

            redis_url=_env_str("REDIS_URL", ""),
        )
