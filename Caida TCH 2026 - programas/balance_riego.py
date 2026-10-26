# -*- coding: utf-8 -*-
r"""Riopaila: ¿el balance hídrico y el riego aplicado (en mm) explican el TCH? Soporte de la sequía y el riego.

Entradas:
  · Clima mensual de Cenicaña por estación 1993-2026 (Clima_Cenicana_Riopaila_Castilla_1993-2026.xlsx, hoja Mensual):
    lluvia y evaporación de La Paila y Bugalagrande.
  · «Balance Hídrico 2026 actualizado.xlsx», hoja «Consolidado de riegos»: cada riego desde 2021 con fecha, área regada y lámina (mm).
  · estaciones_suertes.csv del repo Precipitacion-riopaila: la estación de cada suerte (si falta, la EMA del modelo).
  · rio_integrado_dataset.pkl (caida_integrada_rio.py): las cosechas 2011-2026 con sus variables del modelo.
Para cada cosecha: falta de agua del mes 8 del ciclo a la cosecha = Σ máx(0,8 × evaporación − lluvia, 0) por mes en su estación;
riego aplicado en la misma ventana, llevado a toda el área de la suerte; falta sin cubrir = máx(falta − riego, 0).
Regresión del log TCH como el modelo de la caída (efectos fijos de suerte, año, mes, edad, etapa de la soca y variedad; incendio,
corte y cosecha mecanizada), ponderada por área, errores agrupados por suerte. Efectos en TCH sobre el TCH normal 2020-25.
No entra al modelo de la caída (contaría el agua dos veces): es soporte de la causa sequía y riego.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe balance_riego.py <datos intermedios> <Clima_Cenicana_...xlsx>
       <Balance Hídrico 2026 actualizado.xlsx> <repo Precipitacion-riopaila> <carpeta web>
Escribe <carpeta web>/data/balance.json (lo lee la pestaña «Para la gerencia»).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding="utf-8")
PK, CLIMA, BH, REPO, WEB = (Path(a) for a in sys.argv[1:6])
ETC = 0.8                       # consumo de la caña ≈ 0,8 × evaporación de tanque (supuesto simple)
r1 = lambda v, n=1: None if v is None or pd.isna(v) else round(float(v), n)  # noqa: E731

# ---------------------------------------------------------------- balance mensual por estación
m = pd.read_excel(CLIMA, sheet_name="Mensual")
m = m[m["Estación"].isin(["La Paila", "Bugalagrande"])][["Estación", "Fecha", "Precipitación (mm)", "Evaporación (mm)"]]
m.columns = ["est", "f", "p", "e"]
m["falta"] = (ETC * m.e - m.p).clip(lower=0)
B = {k: g.set_index("f").sort_index() for k, g in m.groupby("est")}

# ---------------------------------------------------------------- riegos aplicados (mm sobre toda la suerte)
r = pd.read_excel(BH, sheet_name="Consolidado de riegos", usecols="A,H,U,V,AM")
r.columns = ["fecha", "area_regada", "ste", "area_neta", "mm"]
r["fecha"] = pd.to_datetime(r.fecha, errors="coerce")
r["ste"] = r.ste.astype(str).str.strip()
for c in ["area_regada", "area_neta", "mm"]:
    r[c] = pd.to_numeric(r[c], errors="coerce")
r = r.dropna(subset=["fecha", "mm", "area_regada"])
r["mm_ste"] = r.mm * r.area_regada / r.area_neta
R0, R1 = pd.Timestamp("2021-01-01"), r.fecha.max()
RG = {k: g.set_index("fecha").mm_ste.sort_index() for k, g in r.groupby("ste")}
print(f"riegos: {len(r)} de {r.fecha.min().date()} a {R1.date()}, {r.ste.nunique()} suertes")

# ---------------------------------------------------------------- estación de cada suerte
e = pd.read_csv(REPO / "estaciones_suertes.csv", sep=";", skiprows=1, encoding="latin-1")
e = e.iloc[:, [1, 2]].dropna()
e.columns = ["ste", "est"]
EST = e.assign(ste=e.ste.astype(str).str.strip(), est=e.est.astype(str).str.strip()).drop_duplicates("ste").set_index("ste").est

# ---------------------------------------------------------------- falta de agua y riego de cada cosecha
d = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
d = d[d.anio >= 2011].copy()
d["estB"] = d.ste.map(EST).fillna(d.est)


def ciclo(x):
    g = B.get(x.estB)
    i8 = x.ini + pd.DateOffset(months=8)
    if g is None:
        return pd.Series({"falta": np.nan, "riego": np.nan})
    w = g.loc[i8.to_period("M").to_timestamp():x.cosecha.to_period("M").to_timestamp()]
    falta = w.falta.sum() if w.falta.notna().sum() >= max(1, len(w) - 1) else np.nan
    rs = RG.get(x.ste)
    riego = float(rs.loc[i8:x.cosecha].sum()) if rs is not None else 0.0
    return pd.Series({"falta": falta, "riego": riego})


d = pd.concat([d, d.apply(ciclo, axis=1)], axis=1)
d["con_riego"] = (d.ini + pd.DateOffset(months=8) >= R0) & (d.cosecha <= R1)
d["falta100"], d["riego100"] = d.falta / 100, d.riego / 100
d["sincubrir100"] = (d.falta - d.riego).clip(lower=0) / 100
ref = d[d.anio.between(2020, 2025) & d.Mes.between(1, 9)]
TN = float(np.average(ref.tch_calc, weights=ref.Area))
wm = lambda g, k: float(np.average(g[k], weights=g.Area)) if len(g) else None  # noqa: E731

# ---------------------------------------------------------------- regresiones (como el modelo de la caída)
BASE = "y ~ C(ste) + C(anio) + C(Mes) + C(edad_b) + C(soca_b) + C(var) + inc + Corte + mec"
pruebas = []


def prueba(nombre, data, extra, k):
    data = data.dropna(subset=["falta"])
    mo = smf.wls(BASE + " + " + extra, data=data, weights=data.Area)
    fit = mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(data.loc[mo.data.row_labels, "ste"])[0]})
    pct = 100 * (np.exp(fit.params[k]) - 1)
    pruebas.append({"prueba": nombre, "n": int(fit.nobs), "pct": r1(pct, 2), "tch": r1(pct / 100 * TN, 2), "p": r1(fit.pvalues[k], 3)})
    print(f"  {nombre}: {pct:+.2f} % ≈ {pct / 100 * TN:+.2f} TCH por 100 mm (p={fit.pvalues[k]:.3f}, n={int(fit.nobs)})")


c = d[d.con_riego]
prueba("Falta de agua al final del ciclo, 2011-2026", d, "falta100", "falta100")
prueba("Falta de agua al final del ciclo, solo 2021-2026", c, "falta100", "falta100")
prueba("Riego aplicado, 2021-2026", c, "falta100 + riego100", "riego100")
prueba("Falta que el riego no cubrió, 2021-2026", c, "sincubrir100 + riego100", "sincubrir100")

anios = [[int(y), r1(wm(g.dropna(subset=["falta"]), "falta"), 0), r1(wm(g[g.con_riego], "riego"), 0) if g.con_riego.any() else None]
         for y, g in d.groupby("anio")]
out = {"cosechas": int(d.falta.notna().sum()), "cosechas_riego": int(d.con_riego.sum()), "tch_base": r1(TN),
       "riegos": int(len(r)), "riego_desde": str(R0.year), "riego_hasta": R1.date().isoformat(),
       "suertes_estacion": {k: int(v) for k, v in EST.value_counts().items()}, "anios": anios, "pruebas": pruebas}
json.dump(out, open(WEB / "data" / "balance.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("escrito:", WEB / "data" / "balance.json")
