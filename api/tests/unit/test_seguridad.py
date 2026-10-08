import uuid

import jwt
import pytest

from app.core.seguridad import (
    crear_access_token,
    decodificar_access_token,
    hashear_password,
    verificar_password,
)


def test_hashing_argon2() -> None:
    password = "SuperPasswordSeguro123!"
    hash_str = hashear_password(password)

    assert hash_str.startswith("$argon2id$")
    assert verificar_password(hash_str, password) is True
    assert verificar_password(hash_str, "PasswordErroneo") is False


def test_jwt_creacion_y_decodificacion() -> None:
    tid = uuid.uuid4()
    cid = uuid.uuid4()
    uid = uuid.uuid4()
    roles = ["administrador", "vendedor"]

    token = crear_access_token(
        tenant_id=tid,
        company_id=cid,
        usuario_id=uid,
        roles=roles,
    )

    data = decodificar_access_token(token)
    assert data.tid == tid
    assert data.cid == cid
    assert data.uid == uid
    assert data.roles == roles


def test_jwt_expirado_falla() -> None:
    tid = uuid.uuid4()
    cid = uuid.uuid4()
    uid = uuid.uuid4()

    # Expiración negativa
    token = crear_access_token(
        tenant_id=tid,
        company_id=cid,
        usuario_id=uid,
        roles=[],
        minutos_expiracion=-5,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decodificar_access_token(token)
