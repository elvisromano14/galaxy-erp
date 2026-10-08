from datetime import UTC, datetime

from app.core.tiempo import CARACAS_TZ, a_caracas, ahora, hoy


def test_ahora_zona_horaria() -> None:
    dt = ahora()
    assert dt.tzinfo is not None
    assert dt.tzinfo == CARACAS_TZ


def test_hoy_tipo_date() -> None:
    d = hoy()
    assert d == ahora().date()


def test_conversion_a_caracas() -> None:
    dt_utc = datetime(2026, 10, 8, 16, 0, 0, tzinfo=UTC)
    dt_caracas = a_caracas(dt_utc)
    # Caracas es UTC-4 (16:00 UTC = 12:00 Caracas)
    assert dt_caracas.hour == 12
