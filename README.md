# Valuación de Organización Soriana (SORIANA B)

Aplicación interactiva en Python y Streamlit que valúa a Organización Soriana como en el reporte y la presentación
del **Reto Banamex**, para la materia Valuación de Empresas del Tecnológico de Monterrey. Combina tres métodos:

- **Flujos de caja descontados (DCF)**, que reproduce el modelo de `Estudio_Financiero_Soriana.xlsx`.
- **Empresas comparables** (S&P Capital IQ Pro).
- **Transacciones precedentes** (S&P Capital IQ Pro).

Con ellos calcula un **precio objetivo a 12 meses**, el potencial contra el precio de mercado y una recomendación.

## Equipo

| Nombre | Matrícula |
|---|---|
| Alejandro Ochoa | A01613152 |
| Catherine Daran | A01611885 |
| Dheneb Velazquez | A01614817 |
| Julio Gaspar | A01613250 |

## Resultados con los valores por defecto

Precio de mercado de referencia: $33.10 (cierre del 19-oct-2026). Cifras en millones de pesos (mdp).

| Concepto | Valor |
|---|---|
| WACC (redondeado, como en el reporte) / Ke / g | 7.88% / 8.14% / 3.50% |
| FCFF 2026–2030 | 4,868 / 5,023 / 5,186 / 5,357 / 5,535 |
| Valor terminal / Enterprise Value / Equity Value | 130,782 / 110,206 / 100,041 |
| Valor por acción por DCF | **$55.58** |
| Escenarios pesimista / base / optimista | $37.35 / $55.58 / $74.01 |
| Valor ponderado (25 / 50 / 25) | $55.63 |
| Empresas comparables | $43.30 |
| Transacciones precedentes | $39.89 |
| Precio objetivo (1/3 por método) | **$46.25** |
| Potencial | +39.7% |
| Recomendación | **COMPRAR** |

Cualquier cambio en una variable recalcula toda la cadena:

**Beta → WACC → Flujos → Valor terminal → Enterprise Value → Equity Value → Valor por acción → Precio objetivo**

### WACC exacto y redondeado

El DCF usa siempre el WACC **redondeado a 7.88%** del reporte y la presentación Banamex ($55.58 por acción). El
Excel integrador usa el WACC exacto de 7.8819% ($55.55); la diferencia de $0.03 viene solo del redondeo. En la
barra lateral se puede capturar un WACC manual (Financieras → WACC → Usar valor manual), que tiene prioridad.

## Contenido de la app

**Barra lateral**
- Selección del escenario: conservador, base u optimista.
- Variables agrupadas: Económicas, Mercado, Financieras, Valuación y Ajustes de escenarios.
- Las variables calculadas siguen el patrón calculado / manual / usado.
- Botones Restablecer valores del Excel, Descargar reporte PDF y Ver tutorial.
- Al cerrarla queda una barra de íconos para abrir cada sección.

**Pestañas**
1. **Dashboard**: tarjetas del DCF, precio objetivo, potencial, recomendación y valor de cada método; gráficas de
   inflación, IPC, escenarios y sensibilidad.
2. **DCF**, con cinco subpestañas:
   - **Inflación y mercado**: INPC, regresión precio vs inflación, tendencias lineal y exponencial y pronóstico.
   - **Beta y WACC**: regresión de rendimientos diarios, métodos de Rf, costo de la deuda y cálculo paso a paso.
   - **Proyección y valuación**: FCFF 2026–2030 y cascada de Enterprise Value a Equity Value.
   - **Escenarios**: justificación editable, tabla comparativa e interpretación automática.
   - **Sensibilidad**: matriz WACC × g, gráficas de una variable y tornado ±10%.
3. **Valuación relativa**:
   - **Empresas comparables** y **Transacciones precedentes**, con casillas para incluir o excluir cada par u
     operación.
   - Estadísticos calculados como PERCENTILE.INC de Excel, con selector de estadístico.
   - Precio implícito por múltiplo.
4. **Precio objetivo**:
   - Ponderaciones editables.
   - Regla del equipo para comprar, mantener o vender.
   - Rango de valuación (football field) y contraste con LSEG.
5. **Contexto financiero**: márgenes, razones financieras 2021–2025 y datos clave con su efecto en los supuestos.
6. **Validación**:
   - Contra el Excel integrador, en modo exacto: 9 de 9 en PASS.
   - Contra el reporte Banamex, en modo redondeado: 18 de 18 en PASS.
7. **Reporte PDF**: genera y descarga un reporte de 21 secciones con los valores que estén en pantalla.

Además tiene una pantalla de inicio con el logo de Soriana y un tutorial que se muestra solo la primera vez. El
diseño se adapta a celular, tablet y monitores de distintos tamaños.

## Archivos

| Archivo | Contenido |
|---|---|
| `app.py` | Interfaz de Streamlit: barra lateral, pestañas, tarjetas, tablas y gráficas. |
| `modelo.py` | Motor del DCF con funciones puras: regresiones, beta, WACC, FCFF, valuación, escenarios, sensibilidad y validación contra el Excel. |
| `relativa.py` | Valuación relativa: estadísticos, comparables, transacciones, precio objetivo, recomendación, LSEG y validación contra el reporte Banamex. |
| `reporte_pdf.py` | Reporte PDF con reportlab y gráficas de matplotlib. |
| `interfaz.py` | Pantalla de inicio, tutorial y barra de íconos de la barra lateral cerrada. |
| `datos_modelo_soriana.json` | Datos del DCF extraídos del Excel (series de mercado, históricos, deuda, supuestos). |
| `datos_valuacion_relativa.json` | Comparables, transacciones, LSEG, contexto financiero y valores del reporte para validar. |
| `assets/` | Logotipo e ícono de Soriana. |
| `test_modelo.py` | Pruebas del DCF contra el Excel integrador (WACC exacto). |
| `test_relativa.py` | Pruebas de la valuación relativa y el precio objetivo contra el reporte Banamex. |
| `test_modo_default.py` | Pruebas de los valores por defecto (WACC redondeado). |
| `requirements.txt` | Dependencias, con Streamlit fijado en la versión probada (1.66.0). |
| `.streamlit/config.toml` | Tema de colores y configuración de Streamlit. |

`Estudio_Financiero_Soriana.xlsx` es opcional: si está en la carpeta, la validación lee sus celdas con
`openpyxl`; si no, usa los resultados guardados en `datos_modelo_soriana.json`.

## Correr la app localmente

Requiere Python 3.10 o posterior.

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

La app se abre en `http://localhost:8501`.

## Pruebas

```bash
pytest -q
```

Son 54 pruebas:

| Archivo | Pruebas | Qué revisa |
|---|---|---|
| `test_modelo.py` | 14 | Corre con el WACC exacto y reproduce el Excel con tolerancia de 0.01%: beta 0.184577, WACC 7.8819%, FCFF, VT, EV, Equity, $55.5523, escenarios $37.3382 / $73.9676 y la matriz WACC–g. |
| `test_modo_default.py` | 10 | Revisa los valores por defecto de la tabla de resultados, incluido el WACC manual de 10% ($35.62). |
| `test_relativa.py` | 30 | Revisa los 18 valores del reporte Banamex, el precio objetivo con WACC exacto ($46.2456), que la media suba al excluir Liverpool, la muestra completa de transacciones (19.5x), las ponderaciones y el aviso cuando no suman 100%. |

## Publicar en Streamlit Community Cloud

1. Entra a [share.streamlit.io](https://share.streamlit.io) con la cuenta de GitHub.
2. **Create app** → repositorio `CatherineDaran/Soriana_App`, rama `main`, archivo `app.py` → **Deploy**.
3. Cada `git push` a `main` actualiza la app. Al pie de la barra lateral aparece la versión publicada.
4. Si después de un push sigue la versión anterior, usa **⋮ → Reboot app**.
