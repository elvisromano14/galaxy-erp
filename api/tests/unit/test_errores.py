from app.core.errores import GalaxyERPException


def test_exception_a_problem_detail() -> None:
    exc = GalaxyERPException(
        code="STOCK_INSUFICIENTE",
        title="Stock insuficiente",
        status=409,
        detail="ACEITE-1L en PRINCIPAL: disponible 3, solicitado 5",
        errors=[{"campo": "cantidad", "mensaje": "Supera el stock disponible"}],
    )
    problem = exc.to_problem_detail(trace_id="trace-12345")

    assert problem.status == 409
    assert problem.code == "STOCK_INSUFICIENTE"
    assert problem.title == "Stock insuficiente"
    assert problem.detail == "ACEITE-1L en PRINCIPAL: disponible 3, solicitado 5"
    assert problem.trace_id == "trace-12345"
    assert problem.type == "https://galaxy-erp.local/errores/stock-insuficiente"
    assert len(problem.errors) == 1
    assert problem.errors[0].campo == "cantidad"
