"""Pruebas de la valuación relativa y el precio objetivo contra el reporte Banamex."""

import pytest

import modelo as m
import relativa as r


@pytest.fixture(scope="module")
def ctx():
    data = m.cargar_datos()
    est = m.estadisticas_beta(data)
    rel = r.cargar_relativa()
    p = m.parametros_default(data)
    return data, est, rel, p


def test_validacion_reporte_completa(ctx):
    data, est, rel, _ = ctx
    df = r.validacion_reporte(data, est, rel)
    assert len(df) == 18
    fallas = df[df["Estado"] != "PASS"]
    assert fallas.empty, fallas.to_string()


@pytest.mark.parametrize("concepto, esperado, tol", [
    ("DCF base: valor terminal", 130782, 1), ("DCF base: EV", 110206, 1), ("DCF base: Equity", 100041, 1),
    ("DCF base: valor por acción", 55.58, 0.01), ("Escenario pesimista", 37.35, 0.01),
    ("Escenario optimista", 74.01, 0.01), ("Comparables: EV/EBITDA", 40.78, 0.01),
    ("Comparables: EV/Ventas", 64.96, 0.01), ("Comparables: P/U", 24.15, 0.01),
    ("Comparables: promedio", 43.30, 0.01), ("Transacciones: EV/EBITDA", 40.74, 0.01),
    ("Transacciones: EV/Ventas", 31.83, 0.01), ("Transacciones: EV/EBIT", 47.09, 0.01),
    ("Transacciones: promedio", 39.89, 0.01), ("Precio objetivo", 46.25, 0.01), ("Potencial", 0.397, 0.001),
    ("EV/EBITDA al precio de mercado", 5.86, 0.01), ("LSEG: precio implícito", 42.79, 0.01),
])
def test_cada_valor_del_reporte(ctx, concepto, esperado, tol):
    data, est, rel, _ = ctx
    df = r.validacion_reporte(data, est, rel).set_index("Concepto")
    assert df.loc[concepto, "App"] == pytest.approx(esperado, abs=tol)


def test_precio_objetivo_wacc_exacto(ctx):
    data, est, rel, p = ctx
    x = r.valuacion_completa(p, data, est, rel, modo_wacc="exacto")
    assert x["dcf"] == pytest.approx(55.5523, abs=1e-4)
    assert x["precio_objetivo"]["objetivo"] == pytest.approx(46.2456, abs=1e-4)
    assert x["precio_objetivo"]["recomendacion"] == "COMPRAR"


def test_wacc_redondeado_da_55_58(ctx):
    data, est, rel, p = ctx
    x = r.valuacion_completa(p, data, est, rel, modo_wacc="redondeado")
    assert x["wacc"] == pytest.approx(0.0788)
    assert x["dcf"] == pytest.approx(55.58, abs=0.005)


def test_excluir_liverpool(ctx):
    _, _, rel, _ = ctx
    base = r.comparables(rel)
    i = next(i for i, f in enumerate(rel["comparables"]["pares"]) if f["empresa"].startswith("El Puerto"))
    sin = r.comparables(rel, {i: False})
    assert base["estadisticos"].loc["Media", "EV/EBITDA"] == pytest.approx(7.026)
    assert sin["estadisticos"].loc["Media", "EV/EBITDA"] == pytest.approx(7.48, abs=0.005)
    assert sin["valor"] > base["valor"]


def test_transacciones_muestra_completa(ctx):
    _, _, rel, _ = ctx
    t = r.transacciones(rel)
    assert t["n_total"] == 8 and t["n_incluidas"] == 3
    assert t["media_ev_ebitda_muestra_completa"] == pytest.approx(19.505)
    todas = r.transacciones(rel, {i: True for i in range(8)})
    assert todas["estadisticos"].loc["Media", "EV/EBITDA"] == pytest.approx(19.505)
    assert t["media_ev_ebitda_depurada"] == pytest.approx(7.02)


def test_percentiles_como_excel():
    e = r.estadisticos([6.89, 8.23, 5.82, 5.22, 8.97, None])
    # PERCENTILE.INC({5.22, 5.82, 6.89, 8.23, 8.97}, 0.25) = 5.82; 0.75 = 8.23
    assert e["P25"] == pytest.approx(5.82) and e["P75"] == pytest.approx(8.23)
    assert e["Mediana"] == pytest.approx(6.89) and e["n"] == 5
    e2 = r.estadisticos([1, 2, 3, 4])
    assert e2["P25"] == pytest.approx(1.75) and e2["P75"] == pytest.approx(3.25)


def test_ponderacion_100_dcf(ctx):
    data, est, rel, p = ctx
    x = r.valuacion_completa(p, data, est, rel, pond={"dcf": 1.0, "comparables": 0.0, "transacciones": 0.0})
    assert x["precio_objetivo"]["objetivo"] == pytest.approx(x["dcf"])
    assert x["precio_objetivo"]["aviso"] is False


def test_aviso_si_no_suman_100(ctx):
    data, est, rel, p = ctx
    x = r.valuacion_completa(p, data, est, rel, pond={"dcf": 0.5, "comparables": 0.3, "transacciones": 0.1})
    assert x["precio_objetivo"]["aviso"] is True
    assert x["precio_objetivo"]["suma"] == pytest.approx(0.9)


def test_wacc_manual_10(ctx):
    data, est, rel, p = ctx
    antes = r.valuacion_completa(p, data, est, rel)
    q = dict(p, wacc_manual=0.10)
    despues = r.valuacion_completa(q, data, est, rel, modo_wacc="redondeado")
    assert despues["wacc"] == pytest.approx(0.10)  # el manual tiene prioridad sobre el redondeo
    assert despues["dcf"] < antes["dcf"]
    assert despues["precio_objetivo"]["objetivo"] < antes["precio_objetivo"]["objetivo"]
    # La validación usa siempre los valores por defecto
    assert (r.validacion_reporte(data, est, rel)["Estado"] == "PASS").all()


def test_recomendacion_y_umbrales():
    assert r.recomendacion(0.20) == "COMPRAR"
    assert r.recomendacion(0.05) == "MANTENER"
    assert r.recomendacion(-0.20) == "VENDER"
    assert r.recomendacion(0.20, {"comprar": 0.25, "vender": -0.10}) == "MANTENER"


def test_lseg(ctx):
    _, _, rel, _ = ctx
    l = r.contraste_lseg(rel)
    assert len(l["pares"]) == 4
    assert l["media_pares_ev_ebitda"] == pytest.approx(7.33, abs=0.005)
    assert l["precio_implicito"] == pytest.approx(42.79, abs=0.01)
    assert l["mas_barata_p_vl"]["empresa"] == "Soriana"


def test_ajuste_neto(ctx):
    _, _, rel, _ = ctx
    assert r.ajuste_neto(rel) == rel["puente_ev_equity"]["ajuste_neto"] == -10165
