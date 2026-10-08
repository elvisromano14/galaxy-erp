import uuid
from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    cliente: str
    usuario: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    tenant_id: uuid.UUID
    company_id: uuid.UUID
    usuario_id: uuid.UUID
    roles: list[str]
    expira_en: datetime


class RefreshRequest(BaseModel):
    cliente: str
    refresh_token: str


class UserMeResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    nombre_completo: str
    company_id: uuid.UUID
    empresa_razon_social: str
    empresa_rif: str
    roles: list[str]
    permisos: list[str]
