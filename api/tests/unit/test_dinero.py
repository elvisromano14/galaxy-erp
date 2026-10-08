from decimal import Decimal

import pytest

from app.core.dinero import (
    a_decimal,
    redondear_cantidad,
    redondear_monto,
    redondear_precio,
    redondear_tasa,
)


def test_no_permite_floats() -> None:
    with pytest.raises(TypeError, match="No se permite crear Decimal a partir de float"):
        a_decimal(10.5)  # type: ignore[arg-type]


def test_conversion_correcta_str_e_int() -> None:
    assert a_decimal("150.25") == Decimal("150.25")
    assert a_decimal(100) == Decimal("100")


def test_redondeo_monto() -> None:
    # 2 decimales, ROUND_HALF_UP
    assert redondear_monto(Decimal("10.555")) == Decimal("10.56")
    assert redondear_monto(Decimal("10.554")) == Decimal("10.55")


def test_redondeo_precio_y_costo() -> None:
    # 4 decimales
    assert redondear_precio(Decimal("10.12345")) == Decimal("10.1235")
    assert redondear_precio(Decimal("10.12344")) == Decimal("10.1234")


def test_redondeo_cantidad() -> None:
    # 4 decimales
    assert redondear_cantidad(Decimal("5.00001")) == Decimal("5.0000")
    assert redondear_cantidad(Decimal("5.00005")) == Decimal("5.0001")


def test_redondeo_tasa() -> None:
    # 6 decimales
    assert redondear_tasa(Decimal("36.1234567")) == Decimal("36.123457")
