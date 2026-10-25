# -*- coding: utf-8 -*-
"""Datos del tablero «Caída del TCH Riopaila 2026»: la matriz ponderada sobre TODAS las cosechas ene-sep del G&P.

Una fila por cosecha (caida_por_suerte.pkl, de caida_integrada_rio.py). Para cada una: TCH real, TCH histórico 2020-25 de la
misma suerte (media geométrica, la del modelo), caída exacta (histórico − real), los dos presupuestos (el del AgroFactors /
maestro y el de la base de maduración, solo ene-ago) y cuántas t/ha le quitó o dio cada variable:
  · paso 1, variables que mide el modelo (efectos de 7.433 cosechas 2011-2026, cada suerte frente a sí misma);
  · paso 2, calificaciones que solo tiene la matriz de 2026: efecto sobre lo que el paso 1 no explicó, frente a la suerte
    promedio de 2026 (en el total suman cero); peor nota solo puede restar; la de variedad no se usa (sale del mismo TCH).
Aporte en t/ha = aporte en log × TCH real × (e^L − 1)/L, con L = caída en log: los aportes suman exacto la caída.

Uso: python tablero_datos.py <caida_por_suerte.pkl> <rio_integrado_dataset.pkl> <rio matriz.xlsx> <base maduración.csv>
                             <Proyeccion Sep-Dic 2026.xlsx> <Caida_TCH_..._soporte.xlsx> <carpeta salida> <excel salida>
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import lsq_linear

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import produccion as pr  # noqa: E402

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
PKL, DS, MAT, BASE, PROY, SOP, OUT, XL = sys.argv[1:9]
OUT = Path(OUT)
OUT.mkdir(parents=True, exist_ok=True)
wm = lambda v, w: float(np.average(v, weights=w))  # noqa: E731

x = pd.read_pickle(PKL)
ds = pd.read_pickle(DS)
assert (ds.loc[x.index, "ste"] == x.ste).all(), "caida_por_suerte y la base del modelo no cruzan por índice"
x["variedad"] = ds.loc[x.index, "Variedad Principal"].astype(str).str.strip()
x["n"] = x.groupby(["ste", "Mes"]).cumcount()

# ---------------------------------------------------------------- matriz (notas 1-3-5 y PPTO del AgroFactors)
m = pd.read_excel(MAT, sheet_name="GYP (2)")
m = m[m.suerte.notna()].reset_index(drop=True)
m["ste"], m["Mes"] = m.suerte.astype(str).str.strip(), pd.to_numeric(m.MES)
m["n"] = m.groupby(["ste", "Mes"]).cumcount()
PASO2 = {
    "Calificación Roya": ("Roya", "Agronómico y operativo"), "Calificación Carbón": ("Carbón", "Agronómico y operativo"),
    "Calificación Dosis Maduración": ("Dosis madurante", "Agronómico y operativo"),
    "Calificación semanas": ("Semanas madurante", "Agronómico y operativo"),
    "Calificación TP": ("Tiempo de permanencia", "Agronómico y operativo"),
    "Calificación Calidad Roturación": ("Calidad roturación", "No controlable"),
    "Calificación Calidad fertilización": ("Calidad fertilización", "No controlable"),
    "Calificación Nivel freatico": ("Nivel freático", "No controlable"), "Calificacion CAPEX": ("CAPEX", "Flujo de caja"),
    "Calificación daño Ganado externo": ("Daño de ganado", "Agronómico y operativo"),
    "Calificacion Clas T Termico": ("Tiempo térmico", "No controlable"),
    "Calificacion Clas 1 mes antes de cosecha": ("Lluvia 1 mes antes de cosecha", "No controlable"),
}
P2 = {}
for k, v in PASO2.items():
    real = next((c for c in m.columns if str(c).strip().lower()[:24] == k.lower()[:24]), None)
    if real is not None and pd.to_numeric(m[real], errors="coerce").nunique() > 1:
        P2[real] = v
for c in P2:
    m[c] = pd.to_numeric(m[c], errors="coerce")
m["ppto_agrofactors"] = pd.to_numeric(m["PPTO TCH"], errors="coerce")
d = x.merge(m[["ste", "Mes", "n", "Zona", "ppto_agrofactors"] + list(P2)], on=["ste", "Mes", "n"], how="left")
d.index = x.index
print(f"cosechas G&P ene-sep: {len(d)} · con historia {d.rel.notna().sum()} · con notas de la matriz {d[list(P2)[0]].notna().sum()}")

# ---------------------------------------------------------------- presupuestos, zona y zona agroecológica
M = list(openpyxl.load_workbook(PROY, read_only=True, data_only=True)["Maestro"].iter_rows(values_only=True))
hm = next(i for i, r in enumerate(M[:5]) if r and "TCH PPTO" in [str(v).strip() for v in r])
em = [str(v).strip() if v is not None else f"c{j}" for j, v in enumerate(M[hm])]
pm = pd.DataFrame([r[: len(em)] for r in M[hm + 1:]], columns=em).loc[:, lambda t: ~t.columns.duplicated()]
pm = pm[pm.SUERTE.notna()].assign(ste=lambda t: t.SUERTE.astype(str).str.strip()).drop_duplicates("ste").set_index("ste")
d["ppto_agrofactors"] = d.ppto_agrofactors.fillna(d.ste.map(pd.to_numeric(pm["TCH PPTO"], errors="coerce")))
d["zona"] = pd.to_numeric(d.Zona, errors="coerce").fillna(d.ste.map(pd.to_numeric(pm["ZONA"], errors="coerce")))
b = pd.read_csv(BASE, sep=";", encoding="latin-1", dtype=str, keep_default_na=False)
b = b.assign(ste=b.suerte.str.strip(), Mes=pd.to_numeric(b.MES), ppto_base=pd.to_numeric(b["PPTO TCH"], errors="coerce"))
b["n"] = b.groupby(["ste", "Mes"]).cumcount()
d = d.merge(b[["ste", "Mes", "n", "ppto_base"]], on=["ste", "Mes", "n"], how="left").set_axis(d.index)
mp, _ = pr.cargar_maestro()
d["zona_agroecologica"] = d.ste.map(lambda s: (mp.get(s) or {}).get("zona_agroecologica") or "")
print(f"PPTO AgroFactors en {d.ppto_agrofactors.notna().sum()} · PPTO base de maduración en {d.ppto_base.notna().sum()} · "
      f"zona en {d.zona.notna().sum()} · zona agroecológica en {(d.zona_agroecologica != '').sum()}")

# ---------------------------------------------------------------- paso 1 y paso 2
PASO1 = {
    "Calor (días >32 °C)": ("Días Tmax >32 °C", "No controlable"),
    "Lluvia del arranque (0-3 meses)": ("Precipitación 0 a 3 meses", "No controlable"),
    "Sequía al final del ciclo": ("Balance hídrico: sequía al final", "No controlable"),
    "Riego aplicado": ("Balance hídrico: riego aplicado", "Flujo de caja"),
    "Renovación no hecha": ("No renovación", "Flujo de caja"),
    "Roturación tardía": ("Oportunidad roturación", "Flujo de caja"),
    "Fertilización después de 120 días": ("Oportunidad fertilización", "Flujo de caja"),
    "Malezas (herbicida después de 90 días)": ("Control de malezas", "Flujo de caja"),
    "Cosecha mecánica": ("Cosecha mecánica", "Agronómico y operativo"),
    "Variedades": ("Variedades", "Agronómico y operativo"),
    "Edad de cosecha": ("Edad de cosecha", "Agronómico y operativo"),
    "Número de corte": ("N° de corte", "Agronómico y operativo"),
    "Incendio": ("Incendio", "Agronómico y operativo"),
}
e = d[d.rel.notna() & d[list(P2)].notna().all(axis=1)]
MU = {c: wm(e[c], e.Area) for c in P2}
X = np.column_stack([np.ones(len(e))] + [e[c] - MU[c] for c in P2])
sw = np.sqrt(e.Area.values / e.Area.mean())
lo, hi = np.r_[-np.inf, np.full(len(P2), -np.inf)], np.r_[np.inf, np.zeros(len(P2))]
b2 = lsq_linear(X * sw[:, None], e["Sin explicar"].values * sw, bounds=(lo, hi)).x
libre = sm.WLS(e["Sin explicar"].values, X, weights=e.Area.values).fit()
tch_med = wm(e["TC-Total"] / e.Area, e.Area)

tch = d["TC-Total"] / d.Area
L = -d["caída"]
fac = pd.Series(np.where(L.isna() | (L.abs() < 1e-9), tch, tch * np.expm1(L) / L.replace(0, np.nan)), index=d.index)
out = pd.DataFrame(index=d.index)
for k, (nom, _) in PASO1.items():
    out[nom] = -d[k] * fac
resto = d["Sin explicar"].copy()
for i, (c, (nom, _)) in enumerate(P2.items()):
    ap = b2[1 + i] * (d[c] - MU[c])  # NaN donde la cosecha no tiene notas → 0
    out[nom] = -(ap.fillna(0)) * fac
    resto = resto - ap.fillna(0)
out["Sin explicar"] = (-resto * fac).where(d.rel.notna())
caida = (tch * np.expm1(L)).where(d.rel.notna())
principal = out.idxmax(axis=1).where(out.max(axis=1) > 0.5, "")
principal = principal.where(d.rel.notna(), "sin TCH histórico 2020-25")
ok = d.rel.notna()
EXPL = 1 - out.loc[ok, "Sin explicar"].var() / caida[ok].var()
tot = (caida * d.Area)[ok].sum()
print(f"caída exacta (suertes con historia): {tot:,.0f} t en {d.Area[ok].sum():,.0f} ha = {tot / d.Area[ok].sum():.2f} t/ha · "
      f"sin explicar {(out['Sin explicar'] * d.Area)[ok].sum() / d.Area[ok].sum():.2f} t/ha · suerte por suerte {100 * EXPL:.0f} %")

# ---------------------------------------------------------------- salidas
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre"]
clave = d.ste + " · mes " + d.Mes.astype(int).astype(str) + np.where(d.n > 0, " (" + (d.n + 1).astype(str) + ")", "")
s = pd.DataFrame({
    "clave": clave, "suerte": d.ste, "mes": d.Mes.astype(int), "zona": d.zona.astype("Int64"),
    "zona_agroecologica": d.zona_agroecologica, "corte": d.Corte.astype("Int64"), "variedad": d.variedad,
    "cosecha": np.where(d.mec == 1, "Mecánica", "Manual"), "area": d.Area.round(3), "tch_real": tch.round(3),
    "tch_hist": (tch + caida).round(3), "caida": caida.round(3), "ppto_agrofactors": d.ppto_agrofactors.round(2),
    "ppto_base": d.ppto_base.round(2), "factor_principal": principal}, index=d.index)
s = pd.concat([s, out.round(3)], axis=1).sort_values(["mes", "suerte"])
assert s.clave.is_unique
s.to_csv(OUT / "suertes_caida_tch.csv", index=False, encoding="utf-8")

coef = pd.read_excel(SOP, sheet_name="Coeficientes").set_index("variable")
EF = {"Días Tmax >32 °C": ("d32", "por día >32 °C"), "Precipitación 0 a 3 meses": ("llu03_100", "por 100 mm"),
      "Balance hídrico: sequía al final": ("def100", "por 100 mm de déficit al final del ciclo"),
      "Balance hídrico: riego aplicado": ("def100", "por 100 mm de déficit al final del ciclo"),
      "No renovación": ("no_renov", "suerte no renovada"), "Oportunidad roturación": ("rot_tard", "roturación tardía"),
      "Oportunidad fertilización": ("fert_120", "fertilización después de 120 días"),
      "Control de malezas": ("mal_extra30", "por mes de atraso del herbicida después de 90 días"),
      "Cosecha mecánica": ("mec_2026", "mecánica frente a manual en 2026"), "N° de corte": ("Corte", "por corte"),
      "Incendio": ("inc", "cosecha por incendio")}
filas = []
for k, (nom, gru) in PASO1.items():
    ef = (f"{coef.loc[EF[nom][0], 'efecto %']:+.1f} % {EF[nom][1]} (p = {coef.loc[EF[nom][0], 'p']:.2f})" if nom in EF
          else "un efecto por variedad" if nom == "Variedades" else "un efecto por rango de edad")
    filas.append({"variable": nom, "grupo": gru, "efecto": ef, "fuente": "modelo 2011-2026 (7.433 cosechas)", "solo_2026": False,
                  "nota5_vs_1_tha": np.nan, "t_ha": (out[nom] * d.Area)[ok].sum() / d.Area[ok].sum()})
for i, (c, (nom, gru)) in enumerate(P2.items()):
    filas.append({"variable": nom, "grupo": gru,
                  "efecto": f"{100 * np.expm1(b2[1 + i]):+.1f} % por punto de nota (libre {100 * np.expm1(libre.params[1 + i]):+.1f} %, p = {libre.pvalues[1 + i]:.2f})",
                  "fuente": "matriz 2026, frente a la suerte promedio", "solo_2026": True,
                  "nota5_vs_1_tha": round(-np.expm1(4 * b2[1 + i]) * tch_med, 2),
                  "t_ha": (out[nom] * d.Area)[ok].sum() / d.Area[ok].sum()})
filas.append({"variable": "Sin explicar", "grupo": "Sin explicar", "efecto": "lo que ninguna variable explica",
              "fuente": "", "solo_2026": False, "nota5_vs_1_tha": np.nan,
              "t_ha": (out["Sin explicar"] * d.Area)[ok].sum() / d.Area[ok].sum()})
pz = pd.DataFrame(filas).sort_values("t_ha", ascending=False)
pz.drop(columns="t_ha").to_csv(OUT / "pesos_variables.csv", index=False, encoding="utf-8")
print(pz.round(2).to_string(index=False))
with pd.ExcelWriter(XL, engine="openpyxl") as wr:
    s.to_excel(wr, sheet_name="Matriz ponderada", index=False)
    pz.to_excel(wr, sheet_name="Pesos", index=False)
print("guardado:", OUT / "suertes_caida_tch.csv", "·", XL)
