# -*- coding: utf-8 -*-
r"""¿Qué variedad tiene mejor potencial de TCH en cada zona agroecológica y en cada sector de Riopaila?

Base: rio_integrado_dataset.pkl (cosechas 2016-2026, TCH de báscula) y la zona agroecológica de cada suerte del Maestro de
Suertes 2026. Sector = los 4 primeros dígitos de la suerte (p. ej. 3501).
Dentro de cada grupo (zona, sector o sector × zona): regresión del log TCH con la variedad y los mismos controles del modelo
de la caída (año, mes, edad, etapa de la soca, cosecha mecanizada, incendio), ponderada por área, errores agrupados por
suerte. Así se comparan variedades en igualdad de condiciones dentro de la misma zona, no la que tocó suertes mejores.
Solo se califica una variedad con al menos MIN_N cosechas en MIN_S suertes del grupo. VARIAS y sin dato no se califican
(no son una variedad que se pueda sembrar).
Prueba de solidez: la misma comparación dentro de la misma suerte (efectos fijos de suerte), que solo usa las suertes que
tuvieron las dos variedades; se da cuando hay al menos 5 suertes así y su error no es enorme.
Mejor contra segunda: diferencia y su p; «clara» si p < 0,10, «probable» si p < 0,30, si no «empate».
Solo TCH: la sacarosa no está en esta base.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe variedad_potencial.py <datos intermedios> <Maestro Suertes 2026.xlsx> <salida.xlsx>
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
PK, MAESTRO, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
MIN_N, MIN_S, DESDE = 15, 3, 2016
CTRL = "C(anio) + C(Mes) + C(edad_b) + C(soca_b) + mec + inc"

M = list(openpyxl.load_workbook(MAESTRO, read_only=True, data_only=True)["MAESTRO"].iter_rows(min_row=5, values_only=True))
pm = pd.DataFrame(M[1:], columns=[str(v).strip() if v is not None else f"c{j}" for j, v in enumerate(M[0])])
pm = pm.loc[:, ~pm.columns.duplicated()]
pm = pm[pm.SUERTE.notna()].assign(ste=lambda t: t.SUERTE.astype(str).str.strip()).drop_duplicates("ste").set_index("ste")

d = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
d = d[(d.anio >= DESDE) & d.tch_calc.between(20, 300)].copy()
d["vp"] = d["Variedad Principal"].astype(str).str.strip().str.upper()
d["zona_agro"] = d.ste.map(pm["Zona Agroecologica"]).astype(str).str.strip().replace({"None": np.nan, "nan": np.nan, "": np.nan})
d["sector"] = d.ste.str[:4]
d["sector_zona"] = d.sector + " · " + d.zona_agro.fillna("?")
d = d[~d.vp.isin(["VARIAS", "#N/A", "NAN", "NONE"])]
d["y"] = np.log(d.tch_calc)
print(f"cosechas {DESDE}-2026 con variedad: {len(d)} · con zona agroecológica {d.zona_agro.notna().sum()}")


def comparar(g):
    """Variedades calificables del grupo: efecto frente a la de más área, IC 90 %, y la prueba dentro de la misma suerte."""
    cnt = g.groupby("vp").agg(n=("ste", "size"), s=("ste", "nunique"), ha=("Area", "sum"))
    ok = cnt[(cnt.n >= MIN_N) & (cnt.s >= MIN_S)].index
    g = g[g.vp.isin(ok)]
    if len(ok) < 2:
        return None, None
    ref = cnt.loc[ok, "ha"].idxmax()
    f = f"y ~ C(vp, Treatment('{ref}')) + {CTRL}"
    mo = smf.wls(f, data=g, weights=g.Area)
    fit = mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.loc[mo.data.row_labels, "ste"])[0]})
    key = lambda v: f"C(vp, Treatment('{ref}'))[T.{v}]"  # noqa: E731
    b = {v: (0.0 if v == ref else fit.params[key(v)]) for v in ok}
    # misma suerte (solo suertes que tuvieron más de una variedad calificable)
    fe = {}
    mix = g.groupby("ste").vp.nunique()
    gm = g[g.ste.isin(mix[mix > 1].index)]
    if gm.ste.nunique() >= 3:
        try:
            m2 = smf.wls(f"y ~ C(vp, Treatment('{ref}')) + C(ste) + {CTRL}", data=gm, weights=gm.Area)
            f2 = m2.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(gm.loc[m2.data.row_labels, "ste"])[0]})
            for v in ok:
                both = gm.groupby("ste").vp.agg(lambda s: {v, ref} <= set(s)).sum()
                if v != ref and key(v) in f2.params and both >= 5 and f2.bse[key(v)] < 0.15:
                    fe[v] = (f2.params[key(v)], int(both), f2.pvalues[key(v)])
        except Exception:  # noqa: BLE001 — grupo sin variación suficiente
            pass
    base = float(np.average(g.tch_calc, weights=g.Area))
    filas = []
    for v in ok:
        se = 0.0 if v == ref else fit.bse[key(v)]
        filas.append({"variedad": v, "cosechas": int(cnt.loc[v, "n"]), "suertes": int(cnt.loc[v, "s"]), "ha": round(cnt.loc[v, "ha"]),
                      "TCH promedio (sin ajustar)": round(np.average(g.tch_calc[g.vp == v], weights=g.Area[g.vp == v]), 1),
                      "último año": int(g.anio[g.vp == v].max()), "frente a": ref,
                      "efecto %": round(100 * np.expm1(b[v]), 1), "efecto TCH": round(np.expm1(b[v]) * base, 1),
                      "IC90 TCH bajo": round(np.expm1(b[v] - 1.645 * se) * base, 1), "IC90 TCH alto": round(np.expm1(b[v] + 1.645 * se) * base, 1),
                      "p": None if v == ref else round(fit.pvalues[key(v)], 3),
                      "misma suerte TCH": round(np.expm1(fe[v][0]) * base, 1) if v in fe else None,
                      "suertes con las dos": fe[v][1] if v in fe else None,
                      "p misma suerte": round(fe[v][2], 3) if v in fe else None})
    t = pd.DataFrame(filas).sort_values("efecto TCH", ascending=False).reset_index(drop=True)
    t.insert(0, "puesto", t.index + 1)
    # mejor contra segunda
    v1, v2 = t.variedad.iloc[0], t.variedad.iloc[1]
    c = fit.cov_params()
    k1, k2 = (None if v1 == ref else key(v1)), (None if v2 == ref else key(v2))
    var = (c.loc[k1, k1] if k1 else 0) + (c.loc[k2, k2] if k2 else 0) - (2 * c.loc[k1, k2] if k1 and k2 else 0)
    dif = b[v1] - b[v2]
    p = float(2 * stats.norm.sf(abs(dif) / np.sqrt(var))) if var > 0 else np.nan
    res = {"mejor": v1, "segunda": v2, "ventaja TCH": round(np.expm1(dif) * base, 1), "p mejor vs segunda": round(p, 3),
           "qué tan seguro": "clara" if p < 0.10 else "probable" if p < 0.30 else "empate",
           "variedades calificadas": len(t), "cosechas": int(len(g)), "suertes": int(g.ste.nunique()), "TCH del grupo": round(base, 1)}
    return t, res


salida, resumen = {}, {}
for nivel, col in (("Zona agroecológica", "zona_agro"), ("Sector", "sector"), ("Sector y zona", "sector_zona")):
    tabs, res = [], []
    for k, g in d[d[col].notna() & ~d[col].astype(str).str.endswith("?")].groupby(col):
        if len(g) < 2 * MIN_N:
            continue
        t, r = comparar(g)
        if t is None:
            res.append({nivel: k, "mejor": "sin datos suficientes", "cosechas": int(len(g)), "suertes": int(g.ste.nunique())})
            continue
        tabs.append(t.assign(**{nivel: k}))
        res.append({nivel: k, **r})
    salida[nivel] = pd.concat(tabs)[[nivel] + [c for c in tabs[0].columns if c != nivel]] if tabs else pd.DataFrame()
    resumen[nivel] = pd.DataFrame(res).sort_values("cosechas", ascending=False)
    print(f"\n== {nivel}")
    print(resumen[nivel].to_string(index=False))

print("\n== Sector 3501 por zona agroecológica")
s35 = salida["Sector y zona"]
print(s35[s35["Sector y zona"].str.startswith("3501")].to_string(index=False))

lee = pd.DataFrame({"Nota": [
    f"Cosechas {DESDE}-2026 de Riopaila con TCH de báscula; zona agroecológica del Maestro de Suertes 2026; sector = 4 primeros dígitos de la suerte.",
    "Cada variedad se compara con la de más área del mismo grupo, en igualdad de condiciones: año, mes, edad, etapa de la soca, "
    "cosecha mecanizada e incendio (los mismos controles del modelo de la caída). Ponderado por área, errores agrupados por suerte.",
    f"Solo se califica una variedad con al menos {MIN_N} cosechas en {MIN_S} suertes del grupo. VARIAS y sin dato no se califican.",
    "«efecto TCH»: cuánto más (o menos) TCH da que la de referencia, sobre el TCH promedio del grupo. IC90: rango probable (90 %).",
    "«misma suerte TCH»: la misma comparación solo dentro de suertes que tuvieron las dos variedades (prueba de solidez; vacía si hay menos de 5 o el error es muy grande).",
    "«qué tan seguro»: la mejor frente a la segunda; clara si p < 0,10, probable si p < 0,30, si no empate.",
    "Lo que no demuestra: una variedad sembrada sobre todo en las mejores suertes de una zona puede verse mejor de lo que es; "
    "las variedades nuevas (CC 05-430, CC 11-595, CC 11-600) tienen pocos cortes y su potencial en socas viejas aún no se ve. Solo TCH, sin sacarosa."]})
with pd.ExcelWriter(OUT) as x:
    lee.to_excel(x, sheet_name="Léeme", index=False)
    for nivel in salida:
        resumen[nivel].to_excel(x, sheet_name=f"Mejor por {nivel.lower()}"[:31], index=False)
        salida[nivel].to_excel(x, sheet_name=f"Detalle {nivel.lower()}"[:31], index=False)
print("escrito:", OUT)
