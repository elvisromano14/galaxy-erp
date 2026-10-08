import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pydantic import BaseModel

from app.core.config import settings
from app.core.tiempo import ahora

_ph = PasswordHasher()


class TokenData(BaseModel):
    tid: uuid.UUID
    cid: uuid.UUID
    uid: uuid.UUID
    roles: list[str] = []
    exp: datetime


def hashear_password(password: str) -> str:
    """Genera hash seguro de contraseña usando Argon2id."""
    return _ph.hash(password)


def verificar_password(password_hash: str, password: str) -> bool:
    """Verifica una contraseña contra su hash Argon2id."""
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def crear_access_token(
    *,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
    usuario_id: uuid.UUID,
    roles: list[str],
    minutos_expiracion: int | None = None,
) -> str:
    """Emite un token JWT de acceso (por defecto 15 min)."""
    minutos = minutos_expiracion or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expira = ahora() + timedelta(minutes=minutos)
    payload: dict[str, Any] = {
        "jti": uuid.uuid4().hex,
        "tid": str(tenant_id),
        "cid": str(company_id),
        "uid": str(usuario_id),
        "roles": roles,
        "iat": int(ahora().timestamp()),
        "exp": int(expira.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decodificar_access_token(token: str) -> TokenData:
    """Valida y decodifica el token de acceso JWT."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    return TokenData(
        tid=uuid.UUID(payload["tid"]),
        cid=uuid.UUID(payload["cid"]),
        uid=uuid.UUID(payload["uid"]),
        roles=payload.get("roles", []),
        exp=datetime.fromtimestamp(payload["exp"], tz=ahora().tzinfo),
    )
