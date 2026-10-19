"""Pruebas del modo por defecto (WACC redondeado a 7.88%): la app reproduce el reporte y la presentación Banamex."""

import pytest

import modelo as m
import relativa as r


@pytest.fixture(scope="module")
def ctx():
    data = m.cargar_datos()
    est = m.estadisticas_beta(data)
    rel = r.cargar_relativa()
    p = m.parametros_default(data)  # sin tocar nada: modo por defecto
    esc = m.todos_escenarios(p, data, est)
    return data, est, rel, p, esc


def test_el_modo_por_defecto_es_redondeado(ctx):
    _, _, _, p, _ = ctx
    assert p["modo_wacc"] == "redondeado"


def test_wacc_ke_g(ctx):
    _, est, _, p, esc = ctx
    cc = m.costo_capital(p, est)
    assert cc["wacc"]["usado"] == pytest.approx(0.0788, abs=1e-12)
    assert cc["wacc"]["calculado"] == pytest.approx(0.0788187237, abs=1e-9)  # el calculado no cambia
    assert cc["ke"] == pytest.approx(0.0814, abs=5e-5)
    assert esc["resultados"]["Base"]["valuacion"]["g"] == pytest.approx(0.035)


def test_fcff(ctx):
    *_, esc = ctx
    fcff = esc["resultados"]["Base"]["valuacion"]["fcff"]
    for a, e in zip(fcff, [4868, 5023, 5186, 5357, 5535]):
        assert round(a) == e


def test_valuacion_base(ctx):
    *_, esc = ctx
    v = esc["resultados"]["Base"]["valuacion"]
    assert round(v["valor_terminal"]) == 130782
    assert round(v["enterprise_value"]) == 110206
    assert round(v["equity_value"]) == 100041
    assert round(v["valor_por_accion"], 2) == 55.58


def test_escenarios(ctx):
    *_, esc = ctx
    res = esc["resultados"]
    assert round(res["Conservador"]["valuacion"]["valor_por_accion"], 2) == 37.35
    assert round(res["Conservador"]["valuacion"]["enterprise_value"]) == 77401
    assert round(res["Base"]["valuacion"]["valor_por_accion"], 2) == 55.58
    assert round(res["Optimista"]["valuacion"]["valor_por_accion"], 2) == 74.01
    assert round(res["Optimista"]["valuacion"]["enterprise_value"]) == 143376
    assert round(esc["ponderado"], 2) == 55.63
    # Los ajustes de escenario se suman al WACC base redondeado
    assert res["Conservador"]["valuacion"]["wacc"] == pytest.approx(0.0888)
    assert res["Optimista"]["valuacion"]["wacc"] == pytest.approx(0.0738)


def test_matriz_sensibilidad(ctx):
    data, est, _, p, _ = ctx
    mat = m.matriz_sensibilidad(p, data, est)
    assert round(mat.iloc[2, 2], 2) == 55.58
    assert round(mat.iloc[0, -1], 2) == 102.97  # WACC 6.88%, g 4.5%
    assert round(mat.iloc[-1, 0], 2) == 37.83  # WACC 8.88%, g 2.5%
    assert [round(v, 2) for v in mat.iloc[2]] == [45.94, 50.27, 55.58, 62.26, 70.91]
    assert mat.index[2] == pytest.approx(0.0788)


def test_precio_objetivo(ctx):
    data, est, rel, p, _ = ctx
    x = r.valuacion_completa(p, data, est, rel)
    po = x["precio_objetivo"]
    assert round(x["comparables"]["valor"], 2) == 43.30
    assert round(x["transacciones"]["valor"], 2) == 39.89
    assert round(po["objetivo"], 2) == 46.25
    assert round(po["potencial"], 3) == 0.397
    assert po["recomendacion"] == "COMPRAR"


def test_wacc_manual_10(ctx):
    data, est, _, p, _ = ctx
    q = dict(p, wacc_manual=0.10)
    v = m.modelo_completo(q, data, est, "Base")["valuacion"]
    assert v["wacc"] == pytest.approx(0.10)
    assert round(v["valor_por_accion"], 2) == 35.62


def test_validaciones_independientes_del_modo(ctx):
    data, est, rel, _, _ = ctx
    excel = m.validacion(data, est)  # siempre en modo exacto
    assert (excel["Estado"] == "PASS").all()
    assert excel.set_index("Variable").loc["Valor por acción", "App"] == pytest.approx(55.5523, abs=1e-4)
    assert (r.validacion_reporte(data, est, rel)["Estado"] == "PASS").all()


def test_modo_exacto_sigue_disponible(ctx):
    data, est, _, p, _ = ctx
    q = dict(p, modo_wacc="exacto")
    esc = m.todos_escenarios(q, data, est)
    assert esc["resultados"]["Base"]["valuacion"]["valor_por_accion"] == pytest.approx(55.5523, abs=1e-4)
    assert esc["resultados"]["Conservador"]["valuacion"]["valor_por_accion"] == pytest.approx(37.3382, abs=1e-4)
    assert esc["resultados"]["Optimista"]["valuacion"]["valor_por_accion"] == pytest.approx(73.9676, abs=1e-4)
