"""Motor de cálculo del modelo de valuación de Organización Soriana (SORIANA B).

Funciones puras que reproducen las fórmulas de `Estudio_Financiero_Soriana.xlsx`.
La cadena completa es:

    BETA -> WACC -> FLUJOS -> VALOR TERMINAL -> ENTERPRISE VALUE -> EQUITY VALUE -> VALOR POR ACCIÓN

Cifras financieras en millones de pesos (mdp); tasas en decimales.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

RUTA_DATOS = Path(__file__).parent / "datos_modelo_soriana.json"
RUTA_EXCEL = Path(__file__).parent / "Estudio_Financiero_Soriana.xlsx"

ANIOS_PROYECCION = [2026, 2027, 2028, 2029, 2030]
ESCENARIOS = ["Conservador", "Base", "Optimista"]
META_BANXICO = 0.03
DIAS_HABILES = 252

JUSTIFICACIONES_DEFAULT = {
    "Conservador": (
        "Replica el 1S26, con ingresos −3.7% y tiendas iguales −3.9%. Castiga el WACC "
        "porque la beta diaria puede subestimar el riesgo."
    ),
    "Base": "Usa los supuestos del estudio.",
    "Optimista": "Supone una recuperación del consumo.",
}


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def cargar_datos(ruta: Path | str = RUTA_DATOS) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Estadística tipo Excel (SLOPE, INTERCEPT, RSQ, CORREL)
# ---------------------------------------------------------------------------

def regresion(x, y) -> dict:
    """Mínimos cuadrados ordinarios, idéntico a SLOPE/INTERCEPT/RSQ/CORREL de Excel."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xm, ym = x.mean(), y.mean()
    sxx = np.sum((x - xm) ** 2)
    syy = np.sum((y - ym) ** 2)
    sxy = np.sum((x - xm) * (y - ym))
    pendiente = float(sxy / sxx)
    intercepto = float(ym - pendiente * xm)
    correl = float(sxy / math.sqrt(sxx * syy))
    return {
        "pendiente": pendiente,
        "intercepto": intercepto,
        "r2": correl ** 2,
        "correlacion": correl,
        "n": len(x),
    }


def regresion_exponencial(x, y) -> dict:
    """y = a·e^(b·x), estimada con regresión de LN(y) contra x; a = e^(intercepto)."""
    r = regresion(x, np.log(np.asarray(y, dtype=float)))
    return {"a": math.exp(r["intercepto"]), "b": r["pendiente"], "r2": r["r2"]}


# ---------------------------------------------------------------------------
# 1. Inflación y activo (serie mensual)
# ---------------------------------------------------------------------------

def serie_inflacion(data: dict) -> pd.DataFrame:
    inpc = pd.Series(dict(data["series_mensuales"]["inpc_banxico_sp1"]), dtype=float)
    inpc.index = pd.to_datetime(inpc.index)
    df = pd.DataFrame({"inpc": inpc})
    df["inflacion_anual"] = df["inpc"] / df["inpc"].shift(12) - 1
    df["inflacion_mensual"] = df["inpc"] / df["inpc"].shift(1) - 1
    return df


def serie_mensual_mercado(data: dict) -> pd.DataFrame:
    sm = data["series_mensuales"]
    sor = pd.Series(dict(sm["soriana_cierre_mensual"]), dtype=float)
    ipc = pd.Series(dict(sm["ipc_cierre_mensual"]), dtype=float)
    df = pd.DataFrame({"soriana": sor, "ipc": ipc})
    df.index = pd.to_datetime(df.index)
    return df


def analisis_inflacion(data: dict) -> dict:
    """Precio de SORIANA B vs inflación anual (nov-2021 a sep-2026) y tendencias contra el tiempo."""
    infl = serie_inflacion(data)
    mer = serie_mensual_mercado(data)
    df = mer[["soriana"]].join(infl, how="left")
    comun = df.dropna(subset=["inflacion_anual"]).copy()
    comun["x"] = np.arange(1, len(comun) + 1)

    reg = regresion(comun["inflacion_anual"], comun["soriana"])
    tend_precio_lin = regresion(comun["x"], comun["soriana"])
    tend_precio_exp = regresion_exponencial(comun["x"], comun["soriana"])
    tend_infl_lin = regresion(comun["x"], comun["inflacion_anual"])
    tend_infl_exp = regresion_exponencial(comun["x"], comun["inflacion_anual"])

    # Pronóstico de oct-2026 (x siguiente al último mes con ambos datos)
    x_pron = len(comun) + 1
    fecha_pron = mer.index[-1]
    observado = float(mer["soriana"].iloc[-1])
    ultima_infl = float(comun["inflacion_anual"].iloc[-1])
    pronosticos = {
        "Tendencia lineal": tend_precio_lin["intercepto"] + tend_precio_lin["pendiente"] * x_pron,
        "Tendencia exponencial": tend_precio_exp["a"] * math.exp(tend_precio_exp["b"] * x_pron),
        "Regresión contra inflación (inflación de sep-2026)": reg["intercepto"] + reg["pendiente"] * ultima_infl,
    }
    return {
        "serie": comun,
        "inflacion_completa": infl,
        "correlacion": reg["correlacion"],
        "regresion": {
            "intercepto": reg["intercepto"],
            "pendiente": reg["pendiente"],
            "pendiente_por_pp": reg["pendiente"] / 100,
            "r2": reg["r2"],
        },
        "tendencia_precio_lineal": tend_precio_lin,
        "tendencia_precio_exponencial": tend_precio_exp,
        "tendencia_inflacion_lineal": tend_infl_lin,
        "tendencia_inflacion_exponencial": tend_infl_exp,
        "pronostico": {
            "fecha": fecha_pron,
            "x": x_pron,
            "observado": observado,
            "modelos": pronosticos,
        },
    }


# ---------------------------------------------------------------------------
# 2. Activo vs IPC (serie mensual)
# ---------------------------------------------------------------------------

def analisis_ipc(data: dict) -> dict:
    df = serie_mensual_mercado(data)
    df["rend_soriana"] = df["soriana"] / df["soriana"].shift(1) - 1
    df["rend_ipc"] = df["ipc"] / df["ipc"].shift(1) - 1
    df["base100_soriana"] = df["soriana"] / df["soriana"].iloc[0] * 100
    df["base100_ipc"] = df["ipc"] / df["ipc"].iloc[0] * 100
    r = df.dropna()
    reg = regresion(r["rend_ipc"], r["rend_soriana"])
    return {"serie": df, "regresion": reg}


# ---------------------------------------------------------------------------
# 3. Beta, Rm y Rf (serie diaria)
# ---------------------------------------------------------------------------

def estadisticas_beta(data: dict) -> dict:
    cols = data["serie_diaria_beta"]["columnas"]
    df = pd.DataFrame(data["serie_diaria_beta"]["datos"], columns=cols)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.set_index("fecha")
    df["rend_ipc"] = df["ipc"] / df["ipc"].shift(1) - 1
    df["rend_soriana"] = df["soriana"] / df["soriana"].shift(1) - 1
    df["cambio_bono"] = df["bono_pct"] / df["bono_pct"].shift(1) - 1
    r = df.dropna()
    reg = regresion(r["rend_ipc"], r["rend_soriana"])
    rm = float(r["rend_ipc"].mean() * DIAS_HABILES)
    rf_metodos = {
        1: float(r["cambio_bono"].mean() * DIAS_HABILES),
        2: float(df["bono_pct"].mean() / 100),
        3: float(df["bono_pct"].iloc[-1] / 100),
    }
    return {
        "serie": df,
        "n_rendimientos": len(r),
        "beta": reg["pendiente"],
        "alfa": reg["intercepto"],
        "r2": reg["r2"],
        "correlacion": reg["correlacion"],
        "rm": rm,
        "rf_metodos": rf_metodos,
    }


# ---------------------------------------------------------------------------
# 4. Costo de la deuda y WACC
# ---------------------------------------------------------------------------

def calcular_kd(fuentes: list[dict], gastos_financieros_trim: float) -> dict:
    """Tasa implícita del arrendamiento y Kd como promedio ponderado de las fuentes."""
    deudas = [f for f in fuentes if f["tipo"] != "Arrendamiento"]
    arr = [f for f in fuentes if f["tipo"] == "Arrendamiento"][0]
    costo_anual = gastos_financieros_trim * 4
    interes_deudas = sum(f["monto"] * f["tasa"] for f in deudas)
    tasa_arr = (costo_anual - interes_deudas) / arr["monto"]
    tabla = []
    for f in fuentes:
        tasa = tasa_arr if f is arr else f["tasa"]
        tabla.append({**f, "tasa": tasa, "interes": f["monto"] * tasa})
    total = sum(f["monto"] for f in tabla)
    kd = sum(f["interes"] for f in tabla) / total
    for f in tabla:
        f["peso"] = f["monto"] / total
    return {"tabla": tabla, "tasa_arrendamiento": tasa_arr, "kd": kd, "total": total,
            "costo_anual": costo_anual}


def ajuste_antad(data: dict) -> dict:
    s = data["crecimiento_sector_antad"]
    return regresion_exponencial(s["x"], s["g"])


def _usado(manual, calculado):
    return calculado if manual is None else manual


def parametros_default(data: dict) -> dict:
    """Todas las variables editables del modelo con sus valores del Excel."""
    pd_ = data["parametros_default"]
    h = data["historicos_2021_2025"]
    pu = data["puente_equity_31dic2025"]
    esc = data["ajustes_escenarios"]
    return {
        # Económicas
        "inflacion_lp": META_BANXICO,
        "crec_real": 0.005,
        "antad_a_manual": None,
        "antad_b_manual": None,
        "trasladar_inflacion_rf": False,
        # Mercado
        "precio_mercado": pd_["precio_mercado"],
        "beta_manual": None,
        "metodo_rf": pd_["metodo_rf"],
        "rf_manual": None,
        "rm_manual": None,
        "prima_manual": None,
        # Financieras
        "ingresos_base": h["Total ingresos"][-1],
        "activo_fijo_base": h["Activo fijo neto (inmuebles, equipo y derechos de uso)"][-1],
        "pasivo_arr_base": h["Pasivo por arrendamiento (corto + largo)"][-1],
        "ctno_base": h["Capital de trabajo neto operativo"][-1],
        "margen_ebit": pd_["margen_ebit"],
        "tasa_nopat": pd_["tasa_impuestos_nopat"],
        "capex_ingresos": pd_["capex_sobre_ingresos"],
        "da_activo_fijo": pd_["da_sobre_activo_fijo"],
        "ctno_ingresos": pd_["ctno_sobre_ingresos"],
        "crec_arrendamiento": pd_["crec_pasivo_arrendamiento"],
        "pagos_arr_pasivo": pd_["pagos_arrend_sobre_pasivo"],
        "deuda_wacc": pd_["deuda_con_costo"],
        "capital_wacc": pd_["capital_contable"],
        "kd_manual": None,
        "isr": pd_["isr_wacc"],
        "fuentes_deuda": copy.deepcopy(data["fuentes_deuda_2T26"]),
        "gastos_financieros_trim": data["tasa_arrendamiento_calculo"]["gastos_financieros_1T26"],
        "wacc_manual": None,
        # Modo del WACC: "redondeado" a 4 decimales (7.88%, reporte y presentación Banamex) o "exacto"
        # (7.8819%, Excel integrador). El modo redondeado es el valor por defecto.
        "modo_wacc": "redondeado",
        # Valuación
        "g_manual": None,
        "acciones": pd_["acciones_millones"],
        "efectivo": pu["efectivo"],
        "asociadas": pu["asociadas"],
        "deuda_puente": pu["deuda_bursatil_bancaria"],
        "arrendamiento_puente": pu["pasivo_arrendamiento"],
        "no_controladora": pu["no_controladora"],
        # Escenarios
        "escenarios": {k: {kk: esc[k][kk] for kk in ("d_crec", "d_margen", "d_wacc", "prob")}
                       for k in ESCENARIOS},
        "justificaciones": dict(JUSTIFICACIONES_DEFAULT),
    }


def crecimiento_perpetuo(p: dict) -> dict:
    calculado = p["inflacion_lp"] + p["crec_real"]
    return {"calculado": calculado, "usado": _usado(p["g_manual"], calculado)}


def costo_capital(p: dict, est: dict) -> dict:
    """Beta -> Ke -> Kd -> WACC con el patrón calculado / manual / usado."""
    beta = _usado(p["beta_manual"], est["beta"])
    rf_calc = est["rf_metodos"][int(p["metodo_rf"])]
    traslado = (p["inflacion_lp"] - META_BANXICO) if p["trasladar_inflacion_rf"] else 0.0
    rf = _usado(p["rf_manual"], rf_calc) + traslado
    rm = _usado(p["rm_manual"], est["rm"])
    prima_calc = rm - rf
    prima = _usado(p["prima_manual"], prima_calc)
    ke = rf + beta * prima

    kd_info = calcular_kd(p["fuentes_deuda"], p["gastos_financieros_trim"])
    kd = _usado(p["kd_manual"], kd_info["kd"])
    d, e, t = p["deuda_wacc"], p["capital_wacc"], p["isr"]
    wd, we = d / (d + e), e / (d + e)
    wacc_calc = we * ke + wd * kd * (1 - t)
    # El modo redondeado solo redondea el WACC calculado; un WACC manual siempre tiene prioridad.
    wacc_modo = round(wacc_calc, 4) if p.get("modo_wacc", "exacto") == "redondeado" else wacc_calc
    wacc = _usado(p["wacc_manual"], wacc_modo)

    e_mercado = p["precio_mercado"] * p["acciones"]
    wacc_mercado = (e_mercado / (d + e_mercado)) * ke + (d / (d + e_mercado)) * kd * (1 - t)

    return {
        "beta": {"calculado": est["beta"], "manual": p["beta_manual"], "usado": beta},
        "rf": {"calculado": rf_calc, "manual": p["rf_manual"], "usado": rf, "traslado": traslado},
        "rm": {"calculado": est["rm"], "manual": p["rm_manual"], "usado": rm},
        "prima": {"calculado": prima_calc, "manual": p["prima_manual"], "usado": prima},
        "ke": ke,
        "kd": {"calculado": kd_info["kd"], "manual": p["kd_manual"], "usado": kd},
        "kd_info": kd_info,
        "isr": t,
        "d": d,
        "e": e,
        "wd": wd,
        "we": we,
        "wacc": {"calculado": wacc_calc, "modo": p.get("modo_wacc", "exacto"), "redondeado": round(wacc_calc, 4),
                 "manual": p["wacc_manual"], "usado": wacc},
        "e_mercado": e_mercado,
        "wacc_mercado": wacc_mercado,
    }


# ---------------------------------------------------------------------------
# 5–6. Crecimiento y proyección del FCFF
# ---------------------------------------------------------------------------

def crecimiento_sector(p: dict, data: dict) -> dict:
    ajuste = ajuste_antad(data)
    a = _usado(p["antad_a_manual"], ajuste["a"])
    b = _usado(p["antad_b_manual"], ajuste["b"])
    g = [a * math.exp(b * x) for x in range(6, 11)]
    return {"a_calc": ajuste["a"], "b_calc": ajuste["b"], "r2": ajuste["r2"], "a": a, "b": b, "g": g}


def proyectar_fcff(p: dict, g_sector: list[float], d_crec: float = 0.0, d_margen: float = 0.0) -> pd.DataFrame:
    """Proyección 2026–2030 (columnas = años)."""
    ingresos_ant = p["ingresos_base"]
    af_ant = p["activo_fijo_base"]
    pasivo_ant = p["pasivo_arr_base"]
    ctno_ant = p["ctno_base"]
    margen = p["margen_ebit"] + d_margen
    filas = {}
    for anio, gs in zip(ANIOS_PROYECCION, g_sector):
        crec = gs + d_crec
        ingresos = ingresos_ant * (1 + crec)
        ebit = ingresos * margen
        nopat = ebit * (1 - p["tasa_nopat"])
        pasivo = pasivo_ant * (1 + p["crec_arrendamiento"])
        pagos = pasivo_ant * p["pagos_arr_pasivo"]
        nuevos_du = pasivo - pasivo_ant + pagos
        capex = ingresos * p["capex_ingresos"]
        da = af_ant * p["da_activo_fijo"]
        af = af_ant + capex + nuevos_du - da
        ctno = ingresos * p["ctno_ingresos"]
        dctno = ctno - ctno_ant
        fcff = nopat + da - capex - dctno
        filas[anio] = {
            "Crecimiento de ventas": crec,
            "Ingresos": ingresos,
            "Margen EBIT": margen,
            "EBIT": ebit,
            "Impuestos sobre EBIT": ebit - nopat,
            "NOPAT": nopat,
            "Pasivo por arrendamiento": pasivo,
            "Pagos de arrendamiento": pagos,
            "Nuevos derechos de uso": nuevos_du,
            "CAPEX": capex,
            "D&A": da,
            "Activo fijo neto": af,
            "Capital de trabajo neto operativo": ctno,
            "Δ Capital de trabajo": dctno,
            "FCFF": fcff,
        }
        ingresos_ant, af_ant, pasivo_ant, ctno_ant = ingresos, af, pasivo, ctno
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# 7. Valuación
# ---------------------------------------------------------------------------

def valuar(fcff: list[float], wacc: float, g: float, p: dict) -> dict:
    """FCFF -> VT -> EV -> Equity -> valor por acción. Si WACC <= g no hay valor terminal."""
    fcff = [float(f) for f in fcff]
    factores = [1 / (1 + wacc) ** t for t in range(1, len(fcff) + 1)]
    vp = [f * k for f, k in zip(fcff, factores)]
    suma_vp = sum(vp)
    puente = {
        "efectivo": p["efectivo"],
        "asociadas": p["asociadas"],
        "deuda": -p["deuda_puente"],
        "arrendamiento": -p["arrendamiento_puente"],
        "no_controladora": -p["no_controladora"],
    }
    res = {"wacc": wacc, "g": g, "fcff": fcff, "factores": factores, "vp_fcff": vp,
           "suma_vp_fcff": suma_vp, "puente": puente, "valido": bool(wacc > g)}
    if wacc <= g:
        res.update({"valor_terminal": None, "vp_valor_terminal": None, "enterprise_value": None,
                    "equity_value": None, "valor_por_accion": None, "peso_vt": None,
                    "diferencia_precio": None})
        return res
    vt = fcff[-1] * (1 + g) / (wacc - g)
    vp_vt = vt * factores[-1]
    ev = suma_vp + vp_vt
    equity = ev + sum(puente.values())
    vpa = equity / p["acciones"]
    res.update({
        "valor_terminal": vt,
        "vp_valor_terminal": vp_vt,
        "enterprise_value": ev,
        "equity_value": equity,
        "valor_por_accion": vpa,
        "peso_vt": vp_vt / ev,
        "diferencia_precio": vpa / p["precio_mercado"] - 1,
    })
    return res


def modelo_completo(p: dict, data: dict, est: dict, escenario: str = "Base") -> dict:
    """Recalcula toda la cadena para un escenario."""
    aj = p["escenarios"][escenario]
    cc = costo_capital(p, est)
    gs = crecimiento_sector(p, data)
    g = crecimiento_perpetuo(p)
    proy = proyectar_fcff(p, gs["g"], aj["d_crec"], aj["d_margen"])
    wacc = cc["wacc"]["usado"] + aj["d_wacc"]
    val = valuar(proy.loc["FCFF"].tolist(), wacc, g["usado"], p)
    return {"escenario": escenario, "ajustes": aj, "costo_capital": cc, "sector": gs,
            "g": g, "proyeccion": proy, "valuacion": val}


def todos_escenarios(p: dict, data: dict, est: dict) -> dict:
    res = {e: modelo_completo(p, data, est, e) for e in ESCENARIOS}
    vpas = [res[e]["valuacion"]["valor_por_accion"] for e in ESCENARIOS]
    if any(v is None for v in vpas):
        ponderado = None
    else:
        ponderado = sum(p["escenarios"][e]["prob"] * res[e]["valuacion"]["valor_por_accion"]
                        for e in ESCENARIOS)
    return {"resultados": res, "ponderado": ponderado,
            "suma_prob": sum(p["escenarios"][e]["prob"] for e in ESCENARIOS)}


def tabla_comparativa(p: dict, esc: dict) -> pd.DataFrame:
    filas = {}
    for e in ESCENARIOS:
        r = esc["resultados"][e]
        v = r["valuacion"]
        filas[e] = {
            "Inflación": p["inflacion_lp"],
            "Crecimiento": float(np.mean(r["proyeccion"].loc["Crecimiento de ventas"])),
            "Beta": r["costo_capital"]["beta"]["usado"],
            "WACC": v["wacc"],
            "Crecimiento perpetuo": v["g"],
            "Flujo proyectado (FCFF 2030)": v["fcff"][-1],
            "Valor terminal": v["valor_terminal"],
            "Enterprise Value": v["enterprise_value"],
            "Equity Value": v["equity_value"],
            "Valor por acción": v["valor_por_accion"],
        }
    return pd.DataFrame(filas)


def descomponer_escenarios(p: dict, data: dict, est: dict) -> dict:
    """Impacto aislado de cada ajuste (crecimiento, margen, WACC) en el valor por acción."""
    base = modelo_completo(p, data, est, "Base")["valuacion"]["valor_por_accion"]
    salida = {}
    for e in ("Conservador", "Optimista"):
        aj = p["escenarios"][e]
        impactos = {}
        for clave, nombre in (("d_crec", "Crecimiento de ventas"), ("d_margen", "Margen EBIT"),
                              ("d_wacc", "WACC")):
            q = copy.deepcopy(p)
            q["escenarios"]["_aislado"] = {"d_crec": 0.0, "d_margen": 0.0, "d_wacc": 0.0, "prob": 0}
            q["escenarios"]["_aislado"][clave] = aj[clave]
            v = modelo_completo(q, data, est, "_aislado")["valuacion"]["valor_por_accion"]
            impactos[nombre] = None if (v is None or base is None) else v - base
        salida[e] = impactos
    return {"base": base, "impactos": salida}


def interpretacion_escenarios(p: dict, data: dict, est: dict, esc: dict) -> str:
    desc = descomponer_escenarios(p, data, est)
    if desc["base"] is None:
        return "No es posible interpretar los escenarios porque el WACC no supera al crecimiento perpetuo."
    totales = {}
    for e, imp in desc["impactos"].items():
        for k, v in imp.items():
            if v is not None:
                totales[k] = totales.get(k, 0) + abs(v)
    clave = max(totales, key=totales.get)
    res = esc["resultados"]
    vc = res["Conservador"]["valuacion"]["valor_por_accion"]
    vo = res["Optimista"]["valuacion"]["valor_por_accion"]
    vb = desc["base"]
    partes = [
        f"El valor por acción va de ${vc:,.2f} en el escenario conservador a ${vo:,.2f} en el optimista, "
        f"frente a ${vb:,.2f} en el base." if vc is not None and vo is not None else
        f"El valor por acción del escenario base es ${vb:,.2f}.",
    ]
    detalle = []
    for e, imp in desc["impactos"].items():
        txt = ", ".join(f"{k}: {'+' if v >= 0 else '−'}${abs(v):,.2f}" for k, v in imp.items() if v is not None)
        detalle.append(f"{e} ({txt})")
    partes.append("Aislando cada ajuste contra el escenario base: " + "; ".join(detalle) + ".")
    partes.append(
        f"La variable que más mueve el valor es **{clave}**, porque el valor terminal concentra la mayor "
        f"parte del Enterprise Value y es muy sensible a la diferencia entre el WACC y el crecimiento perpetuo."
        if clave == "WACC" else
        f"La variable que más mueve el valor es **{clave}**."
    )
    if esc["ponderado"] is not None:
        partes.append(f"El valor ponderado por probabilidad es ${esc['ponderado']:,.2f} por acción.")
    return " ".join(partes)


# ---------------------------------------------------------------------------
# Sensibilidad
# ---------------------------------------------------------------------------

def matriz_sensibilidad(p: dict, data: dict, est: dict, escenario: str = "Base",
                        pasos_wacc=(-0.01, -0.005, 0.0, 0.005, 0.01),
                        gs=(0.025, 0.03, 0.035, 0.04, 0.045)) -> pd.DataFrame:
    """Valor por acción para WACC base ±1 pp contra g de 2.5% a 4.5%."""
    r = modelo_completo(p, data, est, escenario)
    fcff = r["proyeccion"].loc["FCFF"].tolist()
    wacc0 = r["valuacion"]["wacc"]
    filas = {}
    for dw in pasos_wacc:
        w = wacc0 + dw
        filas[w] = {g: valuar(fcff, w, g, p)["valor_por_accion"] for g in gs}
    df = pd.DataFrame(filas).T
    df.index.name = "WACC"
    df.columns.name = "g"
    return df.astype(float)


def _con(p: dict, **cambios) -> dict:
    q = copy.deepcopy(p)
    q.update(cambios)
    return q


def curva(p: dict, data: dict, est: dict, escenario: str, variable: str, valores) -> pd.DataFrame:
    """Gráficas de una variable."""
    filas = []
    for v in valores:
        if variable == "inflacion":
            r = modelo_completo(_con(p, inflacion_lp=v), data, est, escenario)
            filas.append({"x": v, "y": r["valuacion"]["valor_por_accion"]})
        elif variable == "wacc":
            r = modelo_completo(p, data, est, escenario)
            val = valuar(r["proyeccion"].loc["FCFF"].tolist(), v, r["g"]["usado"], p)
            filas.append({"x": v, "y": val["valor_por_accion"]})
        elif variable == "crecimiento":
            q = copy.deepcopy(p)
            q["escenarios"][escenario] = {**q["escenarios"][escenario],
                                          "d_crec": q["escenarios"][escenario]["d_crec"] + v}
            r = modelo_completo(q, data, est, escenario)
            filas.append({"x": float(np.mean(r["proyeccion"].loc["Crecimiento de ventas"])),
                          "y": r["valuacion"]["enterprise_value"]})
        elif variable == "beta":
            cc = costo_capital(_con(p, beta_manual=v), est)
            filas.append({"x": v, "y": cc["ke"]})
    return pd.DataFrame(filas)


VARIABLES_TORNADO = [
    ("Beta", "beta"),
    ("Tasa libre de riesgo (Rf)", "rf"),
    ("Rendimiento de mercado (Rm)", "rm"),
    ("Costo de la deuda (Kd)", "kd"),
    ("ISR (WACC)", "isr"),
    ("Inflación de largo plazo", "inflacion_lp"),
    ("Crecimiento real", "crec_real"),
    ("g del sector (a)", "antad_a"),
    ("Margen EBIT", "margen_ebit"),
    ("Tasa NOPAT", "tasa_nopat"),
    ("CAPEX / ingresos", "capex_ingresos"),
    ("D&A / activo fijo", "da_activo_fijo"),
    ("CTNO / ingresos", "ctno_ingresos"),
    ("Ingresos base", "ingresos_base"),
]


def _mover(p: dict, data: dict, est: dict, clave: str, factor: float) -> dict:
    q = copy.deepcopy(p)
    cc = costo_capital(p, est)
    if clave == "beta":
        q["beta_manual"] = cc["beta"]["usado"] * factor
    elif clave == "rf":
        q["rf_manual"] = (cc["rf"]["usado"] - cc["rf"]["traslado"]) * factor
    elif clave == "rm":
        q["rm_manual"] = cc["rm"]["usado"] * factor
    elif clave == "kd":
        q["kd_manual"] = cc["kd"]["usado"] * factor
    elif clave == "antad_a":
        q["antad_a_manual"] = crecimiento_sector(p, data)["a"] * factor
    else:
        q[clave] = p[clave] * factor
    return q


def tornado(p: dict, data: dict, est: dict, escenario: str = "Base", delta: float = 0.10) -> pd.DataFrame:
    """Mueve cada variable ±10% y ordena por impacto en el valor por acción."""
    base = modelo_completo(p, data, est, escenario)["valuacion"]["valor_por_accion"]
    filas = []
    for nombre, clave in VARIABLES_TORNADO:
        baja = modelo_completo(_mover(p, data, est, clave, 1 - delta), data, est, escenario)
        alta = modelo_completo(_mover(p, data, est, clave, 1 + delta), data, est, escenario)
        vb = baja["valuacion"]["valor_por_accion"]
        va = alta["valuacion"]["valor_por_accion"]
        filas.append({
            "Variable": nombre,
            "-10%": vb,
            "+10%": va,
            "Impacto": (abs((va if va is not None else np.nan) - (vb if vb is not None else np.nan))),
        })
    df = pd.DataFrame(filas).sort_values("Impacto", ascending=True, na_position="last")
    df.attrs["base"] = base
    return df


# ---------------------------------------------------------------------------
# Validación contra Excel
# ---------------------------------------------------------------------------

CELDAS_EXCEL = {
    "WACC": ("7 Valuación", "B11"),
    "g": ("7 Valuación", "B12"),
    "Valor terminal": ("7 Valuación", "B16"),
    "Enterprise Value": ("7 Valuación", "B18"),
    "Equity Value": ("7 Valuación", "B24"),
    "Valor por acción": ("7 Valuación", "B26"),
    "Valor por acción – Conservador (Pesimista)": ("9 Escenarios", "B12"),
    "Valor por acción – Base": ("9 Escenarios", "C12"),
    "Valor por acción – Optimista": ("9 Escenarios", "D12"),
}


def valores_excel(data: dict, ruta_excel: Path | str = RUTA_EXCEL) -> tuple[dict, str]:
    """Lee las celdas del Excel (openpyxl, data_only=True). Si el archivo no está, usa el JSON."""
    rv = data["resultados_excel_para_validar"]
    respaldo = {
        "WACC": rv["wacc"],
        "g": rv["g"],
        "Valor terminal": rv["valor_terminal"],
        "Enterprise Value": rv["enterprise_value"],
        "Equity Value": rv["equity_value"],
        "Valor por acción": rv["valor_por_accion"],
        "Valor por acción – Conservador (Pesimista)": rv["escenarios"]["Conservador"]["vpa"],
        "Valor por acción – Base": rv["escenarios"]["Base"]["vpa"],
        "Valor por acción – Optimista": rv["escenarios"]["Optimista"]["vpa"],
    }
    ruta = Path(ruta_excel)
    if not ruta.exists():
        return respaldo, "datos_modelo_soriana.json (resultados_excel_para_validar)"
    try:
        import openpyxl

        wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
        leidos = {}
        for k, (hoja, celda) in CELDAS_EXCEL.items():
            v = wb[hoja][celda].value
            leidos[k] = float(v) if isinstance(v, (int, float)) else respaldo[k]
        wb.close()
        return leidos, f"{ruta.name} (celdas leídas con openpyxl)"
    except Exception as exc:  # noqa: BLE001
        return respaldo, f"datos_modelo_soriana.json (no se pudo leer el Excel: {exc})"


def validacion(data: dict, est: dict, tolerancia: float = 0.0001) -> pd.DataFrame:
    """Compara siempre con los valores default, sin importar lo que el usuario haya movido."""
    p = parametros_default(data)
    p["modo_wacc"] = "exacto"  # el Excel integrador usa el WACC exacto de 7.8819%
    esc = todos_escenarios(p, data, est)
    base = esc["resultados"]["Base"]["valuacion"]
    app = {
        "WACC": base["wacc"],
        "g": base["g"],
        "Valor terminal": base["valor_terminal"],
        "Enterprise Value": base["enterprise_value"],
        "Equity Value": base["equity_value"],
        "Valor por acción": base["valor_por_accion"],
        "Valor por acción – Conservador (Pesimista)": esc["resultados"]["Conservador"]["valuacion"]["valor_por_accion"],
        "Valor por acción – Base": base["valor_por_accion"],
        "Valor por acción – Optimista": esc["resultados"]["Optimista"]["valuacion"]["valor_por_accion"],
    }
    excel, fuente = valores_excel(data)
    filas = []
    for k, ve in excel.items():
        va = app[k]
        dif = va - ve
        difp = dif / ve if ve else 0.0
        filas.append({"Variable": k, "Excel": ve, "App": va, "Diferencia": dif,
                      "Diferencia %": difp, "Estado": "PASS" if abs(difp) < tolerancia else "FAIL"})
    df = pd.DataFrame(filas)
    df.attrs["fuente"] = fuente
    return df


def resumen_modos(data: dict, est: dict) -> dict:
    """WACC y valor por acción base con los valores por defecto en cada modo (para los textos de la app)."""
    salida = {}
    for modo in ("exacto", "redondeado"):
        p = parametros_default(data)
        p["modo_wacc"] = modo
        r = modelo_completo(p, data, est, "Base")
        salida[modo] = {"wacc": r["valuacion"]["wacc"], "vpa": r["valuacion"]["valor_por_accion"]}
    salida["diferencia"] = salida["redondeado"]["vpa"] - salida["exacto"]["vpa"]
    return salida


def nota_modos(rm: dict, fp, fd) -> str:
    """Nota común a las dos validaciones; las cifras salen del cálculo, no están escritas a mano."""
    return (f"El reporte y la presentación usan el WACC redondeado a {fp(rm['redondeado']['wacc'])} "
            f"({fd(rm['redondeado']['vpa'])}); el Excel integrador usa el WACC exacto de {fp(rm['exacto']['wacc'], 4)} "
            f"({fd(rm['exacto']['vpa'])}). La diferencia de {fd(abs(rm['diferencia']))} viene solo del redondeo.")


def efecto_redondeo_wacc(data: dict, est: dict, decimales: int = 4) -> dict:
    """Valor por acción si el WACC se redondea (p. ej. 7.88%)."""
    p = parametros_default(data)
    p["modo_wacc"] = "exacto"
    cc = costo_capital(p, est)
    w = round(cc["wacc"]["calculado"], decimales)
    r = modelo_completo(_con(p, wacc_manual=w), data, est, "Base")
    return {"wacc_redondeado": w, "valor_por_accion": r["valuacion"]["valor_por_accion"]}
