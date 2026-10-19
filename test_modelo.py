"""Pruebas en modo exacto (WACC 7.8819%): la app reproduce el Excel integrador con tolerancia de 0.01%."""

import pytest

import modelo as m

TOL = 1e-4  # 0.01 %


@pytest.fixture(scope="module")
def ctx():
    data = m.cargar_datos()
    est = m.estadisticas_beta(data)
    p = m.parametros_default(data)
    # Estas pruebas reproducen el Excel integrador: corren explícitamente con el WACC exacto (7.8819%).
    p["modo_wacc"] = "exacto"
    esc = m.todos_escenarios(p, data, est)
    return data, est, p, esc


def cerca(app, esperado):
    return app == pytest.approx(esperado, rel=TOL)


def test_beta(ctx):
    _, est, _, _ = ctx
    assert est["n_rendimientos"] == 1117
    assert cerca(est["beta"], 0.184577)
    assert cerca(est["r2"], 0.01134)
    assert cerca(est["rm"], 0.097389)


def test_rf_metodos(ctx):
    _, est, _, _ = ctx
    assert cerca(est["rf_metodos"][1], 0.077817)
    assert cerca(est["rf_metodos"][2], 0.087811)
    assert cerca(est["rf_metodos"][3], 0.0916)


def test_ke_kd_wacc(ctx):
    _, est, p, _ = ctx
    cc = m.costo_capital(p, est)
    assert cerca(cc["ke"], 0.0814298286333906)
    assert cerca(cc["kd_info"]["tasa_arrendamiento"], 0.119271046387957)
    assert cerca(cc["kd"]["usado"], 0.099144290351136)
    assert cerca(cc["wacc"]["usado"], 0.078819)


def test_antad(ctx):
    data, _, p, _ = ctx
    s = m.crecimiento_sector(p, data)
    assert cerca(s["a"], 0.0854716297626613)
    assert cerca(s["b"], -0.0831549503419064)


def test_fcff(ctx):
    data, _, _, esc = ctx
    fcff = esc["resultados"]["Base"]["proyeccion"].loc["FCFF"].tolist()
    for a, e in zip(fcff, data["resultados_excel_para_validar"]["fcff_2026_2030"]):
        assert cerca(a, e)
    for a, e in zip(fcff, [4868.2, 5023.0, 5186.3, 5357.0, 5534.5]):
        assert a == pytest.approx(e, abs=0.05)


def test_valuacion_base(ctx):
    _, _, _, esc = ctx
    v = esc["resultados"]["Base"]["valuacion"]
    assert cerca(v["g"], 0.035)
    assert cerca(v["valor_terminal"], 130725.8)
    assert cerca(v["enterprise_value"], 110159.1)
    assert cerca(v["equity_value"], 99994.1)
    assert cerca(v["valor_por_accion"], 55.5523)
    assert v["peso_vt"] == pytest.approx(0.812, abs=0.0005)
    assert v["diferencia_precio"] == pytest.approx(0.678, abs=0.0005)


def test_escenarios(ctx):
    _, _, _, esc = ctx
    r = esc["resultados"]
    assert cerca(r["Conservador"]["valuacion"]["valor_por_accion"], 37.3382)
    assert cerca(r["Optimista"]["valuacion"]["valor_por_accion"], 73.9676)
    assert cerca(esc["ponderado"], 55.6026)


def test_escenarios_detalle(ctx):
    data, _, _, esc = ctx
    rv = data["resultados_excel_para_validar"]["escenarios"]
    for e in ("Conservador", "Base", "Optimista"):
        v = esc["resultados"][e]["valuacion"]
        assert cerca(v["wacc"], rv[e]["wacc"])
        assert cerca(v["fcff"][-1], rv[e]["fcff_2030"])
        assert cerca(v["valor_terminal"], rv[e]["vt"])
        assert cerca(v["enterprise_value"], rv[e]["ev"])
        assert cerca(v["equity_value"], rv[e]["equity"])


def test_sensibilidad(ctx):
    data, est, p, _ = ctx
    mat = m.matriz_sensibilidad(p, data, est)
    excel = data["resultados_excel_para_validar"]["sensibilidad_wacc_g"]
    for i, fila in enumerate(excel[1:]):
        for j, v in enumerate(fila[1:]):
            assert cerca(mat.iloc[i, j], v)
    assert mat.iloc[-1, 0] == pytest.approx(37.82, abs=0.005)
    assert mat.iloc[0, -1] == pytest.approx(102.88, abs=0.005)


def test_inflacion(ctx):
    data, _, _, _ = ctx
    a = m.analisis_inflacion(data)
    rv = data["resultados_excel_para_validar"]
    assert len(a["serie"]) == 59
    assert cerca(a["correlacion"], rv["correlacion_precio_inflacion"])
    assert cerca(a["regresion"]["intercepto"], rv["regresion_precio_inflacion"]["intercepto"])
    assert cerca(a["regresion"]["pendiente_por_pp"], rv["regresion_precio_inflacion"]["pendiente_por_pp"])
    assert cerca(a["regresion"]["r2"], rv["regresion_precio_inflacion"]["r2"])


def test_wacc_menor_que_g(ctx):
    data, est, p, _ = ctx
    q = dict(p, g_manual=0.09)
    v = m.modelo_completo(q, data, est, "Base")["valuacion"]
    assert v["valido"] is False
    assert v["valor_terminal"] is None


def test_traslado_inflacion_rf(ctx):
    data, est, p, _ = ctx
    q = dict(p, inflacion_lp=0.04, trasladar_inflacion_rf=True)
    cc = m.costo_capital(q, est)
    assert cc["rf"]["usado"] == pytest.approx(est["rf_metodos"][1] + 0.01)


def test_validacion_pass(ctx):
    data, est, _, _ = ctx
    df = m.validacion(data, est)
    assert (df["Estado"] == "PASS").all()


def test_redondeo_wacc(ctx):
    data, est, _, _ = ctx
    r = m.efecto_redondeo_wacc(data, est)
    assert r["wacc_redondeado"] == pytest.approx(0.0788)
    assert r["valor_por_accion"] == pytest.approx(55.58, abs=0.01)
