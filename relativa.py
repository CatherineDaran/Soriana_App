"""Valuación relativa de Organización Soriana: comparables, transacciones, precio objetivo y LSEG.

Funciones puras. Usa los resultados del DCF de `modelo.py` sin modificar sus funciones.
Cifras en millones de pesos (mdp); múltiplos en veces.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

import modelo as m

RUTA_RELATIVA = Path(__file__).parent / "datos_valuacion_relativa.json"

ESTADISTICOS = ["Mínimo", "P25", "Media", "Mediana", "P75", "Máximo"]

# Múltiplo -> (métrica de Soriana, ¿usa el puente EV→Equity?)
METRICA = {
    "ev_ebitda": ("ebitda", True),
    "ev_ventas": ("ingresos", True),
    "ev_ebit": ("ebit", True),
    "p_u": ("utilidad_neta_controladora", False),
}
NOMBRE_MULTIPLO = {"ev_ebitda": "EV/EBITDA", "ev_ventas": "EV/Ventas", "ev_ebit": "EV/EBIT", "p_u": "P/U"}
MULTIPLOS_COMPARABLES = ["ev_ebitda", "ev_ventas", "p_u"]
MULTIPLOS_TRANSACCIONES = ["ev_ventas", "ev_ebitda", "ev_ebit"]

UMBRALES_DEFAULT = {"comprar": 0.15, "vender": -0.10}


def cargar_relativa(ruta: Path | str = RUTA_RELATIVA) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Estadísticos (PERCENTILE.INC de Excel = interpolación lineal inclusiva)
# ---------------------------------------------------------------------------

def estadisticos(valores) -> dict:
    v = np.array([x for x in valores if x is not None and not (isinstance(x, float) and np.isnan(x))], dtype=float)
    if v.size == 0:
        return {k: None for k in ESTADISTICOS} | {"n": 0}
    return {
        "Mínimo": float(v.min()),
        "P25": float(np.percentile(v, 25, method="linear")),
        "Media": float(v.mean()),
        "Mediana": float(np.median(v)),
        "P75": float(np.percentile(v, 75, method="linear")),
        "Máximo": float(v.max()),
        "n": int(v.size),
    }


def tabla_estadisticos(filas: list[dict], multiplos: list[str]) -> pd.DataFrame:
    """Estadísticos por múltiplo usando solo las filas con incluir = true."""
    incluidas = [f for f in filas if f.get("incluir")]
    return pd.DataFrame({NOMBRE_MULTIPLO[k]: estadisticos([f.get(k) for f in incluidas]) for k in multiplos})


# ---------------------------------------------------------------------------
# Precio implícito
# ---------------------------------------------------------------------------

def ajuste_neto(rel: dict) -> float:
    """Efectivo + asociadas − deuda − arrendamiento − no controladora (−10,165 mdp)."""
    pu = rel["puente_ev_equity"]
    return pu["efectivo"] + pu["asociadas"] - pu["deuda_bursatil_bancaria"] - pu["pasivo_arrendamiento"] - pu["no_controladora"]


def precio_implicito(multiplo: str, valor: float | None, rel: dict) -> float | None:
    if valor is None:
        return None
    metrica, con_puente = METRICA[multiplo]
    base = valor * rel["metricas_soriana_2025"][metrica]
    equity = base + ajuste_neto(rel) if con_puente else base
    return float(equity / rel["acciones_millones"])


def valuar_por_multiplos(filas: list[dict], multiplos: list[str], rel: dict, estadistico: str = "Media") -> dict:
    est = tabla_estadisticos(filas, multiplos)
    precios = {}
    for k in multiplos:
        precios[NOMBRE_MULTIPLO[k]] = precio_implicito(k, est.loc[estadistico, NOMBRE_MULTIPLO[k]], rel)
    validos = [v for v in precios.values() if v is not None]
    valor = float(np.mean(validos)) if validos else None
    # Rango para el football field: precios por múltiplo con el estadístico elegido.
    return {"estadisticos": est, "precios": precios, "valor": valor, "estadistico": estadistico,
            "rango": (min(validos), max(validos)) if validos else (None, None)}


def filas_con_inclusion(filas: list[dict], incluir: dict | None) -> list[dict]:
    """Copia de las filas con el campo incluir sustituido según {índice: bool}."""
    salida = copy.deepcopy(filas)
    for i, v in (incluir or {}).items():
        salida[int(i)]["incluir"] = bool(v)
    return salida


def comparables(rel: dict, incluir: dict | None = None, estadistico: str = "Media") -> dict:
    filas = filas_con_inclusion(rel["comparables"]["pares"], incluir)
    r = valuar_por_multiplos(filas, MULTIPLOS_COMPARABLES, rel, estadistico)
    # Rango P25–P75 de EV/EBITDA
    e = r["estadisticos"]["EV/EBITDA"]
    r["rango_ev_ebitda_p25_p75"] = (precio_implicito("ev_ebitda", e["P25"], rel),
                                    precio_implicito("ev_ebitda", e["P75"], rel))
    r["filas"] = filas
    return r


def transacciones(rel: dict, incluir: dict | None = None, estadistico: str = "Media") -> dict:
    filas = filas_con_inclusion(rel["transacciones"]["operaciones"], incluir)
    r = valuar_por_multiplos(filas, MULTIPLOS_TRANSACCIONES, rel, estadistico)
    todas = [dict(f, incluir=True) for f in filas]
    r["media_ev_ebitda_muestra_completa"] = estadisticos([f["ev_ebitda"] for f in todas])["Media"]
    r["media_ev_ebitda_depurada"] = r["estadisticos"].loc["Media", "EV/EBITDA"]
    r["n_total"] = len(filas)
    r["n_incluidas"] = sum(1 for f in filas if f["incluir"])
    r["filas"] = filas
    return r


# ---------------------------------------------------------------------------
# DCF (WACC exacto o redondeado) y precio objetivo
# ---------------------------------------------------------------------------

def con_wacc(p: dict, est: dict, modo: str = "exacto") -> dict:
    """Parámetros con el WACC elegido. 'redondeado' = WACC calculado redondeado a 7.88%.
    Un WACC manual del usuario siempre tiene prioridad."""
    q = copy.deepcopy(p)
    if modo == "redondeado" and q.get("wacc_manual") is None:
        q["wacc_manual"] = round(m.costo_capital(q, est)["wacc"]["calculado"], 4)
    return q


def ponderaciones_validas(pond: dict, tolerancia: float = 1e-4) -> bool:
    return abs(sum(pond.values()) - 1) <= tolerancia


def recomendacion(potencial: float | None, umbrales: dict = UMBRALES_DEFAULT) -> str:
    if potencial is None:
        return "n.d."
    if potencial > umbrales["comprar"]:
        return "COMPRAR"
    if potencial < umbrales["vender"]:
        return "VENDER"
    return "MANTENER"


def precio_objetivo(dcf: float | None, comp: float | None, trans: float | None, pond: dict, precio: float,
                    umbrales: dict = UMBRALES_DEFAULT) -> dict:
    valores = {"dcf": dcf, "comparables": comp, "transacciones": trans}
    if any(valores[k] is None for k, w in pond.items() if w):
        objetivo = None
    else:
        objetivo = sum(pond[k] * (valores[k] or 0) for k in valores)
    potencial = None if objetivo is None else objetivo / precio - 1
    return {"valores": valores, "ponderaciones": pond, "objetivo": objetivo, "potencial": potencial,
            "recomendacion": recomendacion(potencial, umbrales), "aviso": not ponderaciones_validas(pond),
            "suma": sum(pond.values()), "umbrales": umbrales}


def ev_ebitda_al_precio(rel: dict, precio: float | None = None) -> float:
    precio = rel["precio_mercado"] if precio is None else precio
    return (precio * rel["acciones_millones"] - ajuste_neto(rel)) / rel["metricas_soriana_2025"]["ebitda"]


def contraste_lseg(rel: dict) -> dict:
    emp = rel["lseg"]["empresas"]
    pares = [e for e in emp if not e["ric"].startswith("SORIANA")]
    soriana = next(e for e in emp if e["ric"].startswith("SORIANA"))
    media = float(np.mean([e["ev_ebitda"] for e in pares]))
    mas_barata = min(emp, key=lambda e: e["p_vl"])
    return {"empresas": emp, "pares": pares, "soriana": soriana, "media_pares_ev_ebitda": media,
            "precio_implicito": precio_implicito("ev_ebitda", media, rel), "mas_barata_p_vl": mas_barata}


def valuacion_completa(p: dict, data: dict, est: dict, rel: dict, modo_wacc: str = "exacto",
                       incluir_comp: dict | None = None, incluir_trans: dict | None = None,
                       est_comp: str = "Media", est_trans: str = "Media", pond: dict | None = None,
                       umbrales: dict | None = None) -> dict:
    """DCF base (con el WACC elegido) + comparables + transacciones -> precio objetivo."""
    q = con_wacc(p, est, modo_wacc)
    esc = m.todos_escenarios(q, data, est)
    dcf = esc["resultados"]["Base"]["valuacion"]["valor_por_accion"]
    comp = comparables(rel, incluir_comp, est_comp)
    trans = transacciones(rel, incluir_trans, est_trans)
    pond = pond or dict(rel["precio_objetivo"]["ponderaciones_default"])
    umbrales = umbrales or dict(UMBRALES_DEFAULT)
    po = precio_objetivo(dcf, comp["valor"], trans["valor"], pond, q["precio_mercado"], umbrales)
    mat = m.matriz_sensibilidad(q, data, est, "Base")
    vals = mat.values[np.isfinite(mat.values)]
    vpa = [esc["resultados"][e]["valuacion"]["valor_por_accion"] for e in m.ESCENARIOS]
    rangos = {
        "DCF por escenarios": (min(v for v in vpa if v is not None), max(v for v in vpa if v is not None))
        if any(v is not None for v in vpa) else (None, None),
        "DCF por sensibilidad (WACC × g)": (float(vals.min()), float(vals.max())) if vals.size else (None, None),
        "Comparables (múltiplos)": comp["rango"],
        "Comparables EV/EBITDA (P25–P75)": comp["rango_ev_ebitda_p25_p75"],
        "Transacciones (múltiplos)": trans["rango"],
    }
    return {"parametros": q, "escenarios": esc, "dcf": dcf, "comparables": comp, "transacciones": trans,
            "precio_objetivo": po, "rangos": rangos, "lseg": contraste_lseg(rel),
            "ev_ebitda_al_precio": ev_ebitda_al_precio(rel, q["precio_mercado"]),
            "wacc": esc["resultados"]["Base"]["valuacion"]["wacc"]}


# ---------------------------------------------------------------------------
# Validación contra el reporte Banamex (WACC redondeado y valores por defecto)
# ---------------------------------------------------------------------------

def validacion_reporte(data: dict, est: dict, rel: dict) -> pd.DataFrame:
    p = m.parametros_default(data)
    r = valuacion_completa(p, data, est, rel, modo_wacc="redondeado")
    base = r["escenarios"]["resultados"]["Base"]["valuacion"]
    res = r["escenarios"]["resultados"]
    esp = rel["valores_reporte_para_validar"]
    c, t = r["comparables"]["precios"], r["transacciones"]["precios"]
    filas = [
        ("DCF base: valor terminal", esp["dcf"]["Base"]["vt"], base["valor_terminal"], "mdp"),
        ("DCF base: EV", esp["dcf"]["Base"]["ev"], base["enterprise_value"], "mdp"),
        ("DCF base: Equity", esp["dcf"]["Base"]["equity"], base["equity_value"], "mdp"),
        ("DCF base: valor por acción", esp["dcf"]["Base"]["vpa"], base["valor_por_accion"], "$"),
        ("Escenario pesimista", esp["dcf"]["Pesimista"]["vpa"], res["Conservador"]["valuacion"]["valor_por_accion"], "$"),
        ("Escenario optimista", esp["dcf"]["Optimista"]["vpa"], res["Optimista"]["valuacion"]["valor_por_accion"], "$"),
        ("Comparables: EV/EBITDA", esp["comparables"]["ev_ebitda"], c["EV/EBITDA"], "$"),
        ("Comparables: EV/Ventas", esp["comparables"]["ev_ventas"], c["EV/Ventas"], "$"),
        ("Comparables: P/U", esp["comparables"]["p_u"], c["P/U"], "$"),
        ("Comparables: promedio", esp["comparables"]["promedio"], r["comparables"]["valor"], "$"),
        ("Transacciones: EV/EBITDA", esp["transacciones"]["ev_ebitda"], t["EV/EBITDA"], "$"),
        ("Transacciones: EV/Ventas", esp["transacciones"]["ev_ventas"], t["EV/Ventas"], "$"),
        ("Transacciones: EV/EBIT", esp["transacciones"]["ev_ebit"], t["EV/EBIT"], "$"),
        ("Transacciones: promedio", esp["transacciones"]["promedio"], r["transacciones"]["valor"], "$"),
        ("Precio objetivo", esp["precio_objetivo"], r["precio_objetivo"]["objetivo"], "$"),
        ("Potencial", esp["potencial"], r["precio_objetivo"]["potencial"], "%"),
        ("EV/EBITDA al precio de mercado", esp["ev_ebitda_al_precio"], r["ev_ebitda_al_precio"], "x"),
        ("LSEG: precio implícito", esp["lseg"]["precio_implicito"], r["lseg"]["precio_implicito"], "$"),
    ]
    tol = {"mdp": 1.0, "$": 0.01, "%": 0.001, "x": 0.01}
    salida = []
    for concepto, esperado, app, unidad in filas:
        dif = app - esperado
        # El reporte redondea a 2 decimales (o a mdp enteros): se compara con media unidad de tolerancia extra.
        ok = abs(dif) <= tol[unidad] + 1e-9
        salida.append({"Concepto": concepto, "Reporte": esperado, "App": app, "Diferencia": dif, "Unidad": unidad,
                       "Tolerancia": tol[unidad], "Estado": "PASS" if ok else "FAIL"})
    return pd.DataFrame(salida)
