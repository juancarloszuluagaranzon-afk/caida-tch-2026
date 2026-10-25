# -*- coding: utf-8 -*-
"""Datos del tablero «Caída del TCH Riopaila 2026»: cuánto le quitó o dio cada variable a TODAS las cosechas ene-sep.

Una fila por cosecha (caida_por_suerte.pkl, de caida_integrada_rio.py). Para cada una: TCH real, TCH histórico 2020-25 de la
misma suerte (media geométrica, la del modelo), caída exacta (histórico − real), el presupuesto (TCH PPTO del Maestro de
Suertes 2026, columna AG) y cuántas t/ha le quitó o dio cada variable que mide el modelo (efectos de 7.433 cosechas
2011-2026, cada suerte frente a sí misma). Todo sale de variables medidas; no se usa ninguna calificación 1-3-5.
Aporte en t/ha = aporte en log × TCH real × (e^L − 1)/L, con L = caída en log: los aportes suman exacto la caída.

Uso: python tablero_datos.py <caida_por_suerte.pkl> <rio_integrado_dataset.pkl> <Maestro Suertes 2026.xlsx>
                             <Caida_TCH_..._soporte_v3.xlsx> <carpeta salida> <excel salida>
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
PKL, DS, MAESTRO, SOP, OUT, XL = sys.argv[1:7]
OUT = Path(OUT)
OUT.mkdir(parents=True, exist_ok=True)
es = lambda v, d=1: f"{v:+.{d}f}".replace("-", "\u2212").replace(".", ",")  # noqa: E731  (+1,2 / \u22121,2)
ep = lambda p: f"{p:.3f}".replace(".", ",")  # noqa: E731
x = pd.read_pickle(PKL)
ds = pd.read_pickle(DS)
assert (ds.loc[x.index, "ste"] == x.ste).all(), "caida_por_suerte y la base del modelo no cruzan por índice"
d = x.copy()
d["variedad"] = ds.loc[x.index, "Variedad Principal"].astype(str).str.strip()
d["n"] = d.groupby(["ste", "Mes"]).cumcount()

# ---------------------------------------------------------------- Maestro de Suertes 2026: PPTO, zona, hacienda
M = list(openpyxl.load_workbook(MAESTRO, read_only=True, data_only=True)["MAESTRO"].iter_rows(min_row=5, values_only=True))
pm = pd.DataFrame(M[1:], columns=[str(v).strip() if v is not None else f"c{j}" for j, v in enumerate(M[0])])
pm = pm.loc[:, ~pm.columns.duplicated()]
pm = pm[pm.SUERTE.notna()].assign(ste=lambda t: t.SUERTE.astype(str).str.strip()).drop_duplicates("ste").set_index("ste")
d["ppto"] = d.ste.map(pd.to_numeric(pm["TCH PPTO"], errors="coerce")).where(lambda v: v > 20)
d["zona"] = d.ste.map(pd.to_numeric(pm["ZONA"], errors="coerce"))
d["hacienda"] = d.ste.map(pm["FINCA"].astype(str).str.strip().str.title())
d["zona_agroecologica"] = d.ste.map(pm["Zona Agroecologica"]).fillna("").astype(str).str.strip()
print(f"cosechas G&P ene-sep: {len(d)} · con historia {d.rel.notna().sum()} · con PPTO {d.ppto.notna().sum()} · "
      f"zona en {d.zona.notna().sum()} · zona agroecológica en {(d.zona_agroecologica != '').sum()}")

# ---------------------------------------------------------------- aportes por cosecha
VARS = {
    "Calor (días >32 °C)": ("Días Tmax >32 °C", "No controlable"),
    "Lluvia del arranque (0-3 meses)": ("Precipitación 0 a 3 meses", "No controlable"),
    "Sequía al final del ciclo": ("Balance hídrico: sequía al final", "No controlable"),
    "Nivel freático": ("Nivel freático", "No controlable"),
    "Corte anterior en suelo húmedo": ("Corte anterior en suelo húmedo", "No controlable"),
    "Riego aplicado": ("Balance hídrico: riego aplicado", "Flujo de caja"),
    "Renovación no hecha": ("No renovación", "Flujo de caja"),
    "Roturación tardía": ("Oportunidad roturación", "Flujo de caja"),
    "Fertilización después de 120 días": ("Oportunidad fertilización", "Flujo de caja"),
    "Malezas (herbicida después de 90 días)": ("Control de malezas", "Flujo de caja"),
    "Cosecha mecánica": ("Cosecha mecanizada", "Agronómico y operativo"),
    "Corte anterior mecánico": ("Corte anterior mecanizado", "Agronómico y operativo"),
    "Variedades": ("Variedades", "Agronómico y operativo"),
    "Edad de cosecha": ("Edad de cosecha", "Agronómico y operativo"),
    "Número de corte": ("N° de corte", "Agronómico y operativo"),
    "Incendio": ("Incendio", "Agronómico y operativo"),
}
tch = d["TC-Total"] / d.Area
L = -d["caída"]
fac = pd.Series(np.where(L.isna() | (L.abs() < 1e-9), tch, tch * np.expm1(L) / L.replace(0, np.nan)), index=d.index)
out = pd.DataFrame(index=d.index)
for k, (nom, _) in VARS.items():
    out[nom] = -d[k] * fac
out["Sin explicar"] = (-d["Sin explicar"] * fac).where(d.rel.notna())
caida = (tch * np.expm1(L)).where(d.rel.notna())
principal = out.idxmax(axis=1).where(out.max(axis=1) > 0.5, "")
principal = principal.where(d.rel.notna(), "sin TCH histórico 2020-25")
ok = d.rel.notna()
EXPL = 1 - out.loc[ok, "Sin explicar"].var() / caida[ok].var()
tot = (caida * d.Area)[ok].sum()
print(f"caída exacta (suertes con historia): {tot:,.0f} t en {d.Area[ok].sum():,.0f} ha = {tot / d.Area[ok].sum():.2f} t/ha · "
      f"sin explicar {(out['Sin explicar'] * d.Area)[ok].sum() / d.Area[ok].sum():.2f} t/ha · suerte por suerte {100 * EXPL:.0f} %")

# ---------------------------------------------------------------- salidas
clave = d.ste + " · mes " + d.Mes.astype(int).astype(str) + np.where(d.n > 0, " (" + (d.n + 1).astype(str) + ")", "")
s = pd.DataFrame({
    "clave": clave, "suerte": d.ste, "hacienda": d.hacienda, "mes": d.Mes.astype(int), "zona": d.zona.astype("Int64"),
    "zona_agroecologica": d.zona_agroecologica, "corte": d.Corte.astype("Int64"), "variedad": d.variedad,
    "cosecha": np.where(d.mec == 1, "Mecanizada", "Manual"), "corte_anterior": d.ant, "area": d.Area.round(3),
    "tch_real": tch.round(3), "tch_hist": (tch + caida).round(3), "caida": caida.round(3), "ppto": d.ppto.round(2),
    "factor_principal": principal}, index=d.index)
s = pd.concat([s, out.round(3)], axis=1).sort_values(["mes", "suerte"])
assert s.clave.is_unique
s.to_csv(OUT / "suertes_caida_tch.csv", index=False, encoding="utf-8")

coef = pd.read_excel(SOP, sheet_name="Coeficientes").set_index("variable")
EF = {"Días Tmax >32 °C": ("d32", "por día >32 °C en los 30 días antes de cosechar"),
      "Precipitación 0 a 3 meses": ("llu03_100", "por 100 mm de lluvia en los meses 0-3"),
      "Balance hídrico: sequía al final": ("def100", "por 100 mm de déficit al final del ciclo"),
      "Balance hídrico: riego aplicado": ("def100", "por 100 mm de déficit al final del ciclo"),
      "Nivel freático": ("nf_exc15", "por metro de nivel promedio del ciclo por encima de 1,5 m"),
      "Corte anterior en suelo húmedo": ("ca_mm100", "por cada 100 mm de lluvia en el mes del corte anterior"),
      "No renovación": ("no_renov", "suerte no renovada"), "Oportunidad roturación": ("rot_tard", "roturación tardía"),
      "Oportunidad fertilización": ("fert_120", "fertilización después de 120 días"),
      "Control de malezas": ("mal_extra30", "por mes de atraso del herbicida después de 90 días"),
      "Cosecha mecanizada": ("mec_2026", "mecanizada frente a manual en 2026"),
      "Corte anterior mecanizado": ("pm_new", "corte anterior mecanizado después de manual (dos seguidos: "
                                              f"{es(coef.loc['pm_seg', 'efecto %'])} %)"),
      "Incendio": ("inc", "cosecha por incendio")}
EC = pd.read_pickle(Path(DS).parent / "efecto_corte.pkl")["efecto"]  # pérdida por corte frente a la plantilla
EF_CORTE = (f"cada corte quita productividad: {es(EC.efecto_pct.iloc[0])} % en el 2º corte y {es(EC.efecto_pct.iloc[-1])} % "
            f"en el 8º o más, frente a la plantilla (misma suerte); se compara con la historia de cada suerte")
filas = []
for k, (nom, gru) in VARS.items():
    ef = (f"{es(coef.loc[EF[nom][0], 'efecto %'])} % {EF[nom][1]} (p = {ep(coef.loc[EF[nom][0], 'p'])})" if nom in EF
          else EF_CORTE if nom == "N° de corte"
          else "un efecto por variedad" if nom == "Variedades" else "un efecto por rango de edad")
    filas.append({"variable": nom, "grupo": gru, "efecto": ef, "fuente": "modelo 2011-2026 (7.433 cosechas)",
                  "t_ha": (out[nom] * d.Area)[ok].sum() / d.Area[ok].sum()})
filas.append({"variable": "Sin explicar", "grupo": "Sin explicar", "efecto": "lo que ninguna variable explica", "fuente": "",
              "t_ha": (out["Sin explicar"] * d.Area)[ok].sum() / d.Area[ok].sum()})
pz = pd.DataFrame(filas).sort_values("t_ha", ascending=False)
pz.assign(t_ha=pz.t_ha.round(3)).to_csv(OUT / "pesos_variables.csv", index=False, encoding="utf-8")
print(pz.round(2).to_string(index=False))
with pd.ExcelWriter(XL, engine="openpyxl") as wr:
    s.to_excel(wr, sheet_name="Matriz ponderada", index=False)
    pz.to_excel(wr, sheet_name="Pesos", index=False)
print("guardado:", OUT / "suertes_caida_tch.csv", "·", XL)
