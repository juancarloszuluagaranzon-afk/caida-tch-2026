# -*- coding: utf-8 -*-
"""Riopaila: ¿la cantidad de riegos afectó el TCH de 2026?

Riegos: CONSOLIDADO DE RIEGOS 2026-.xlsx, hoja «Consolidado de riegos » (cada riego por suerte, abr-2020 a oct-2026).
Por cada cosecha (tabla rio_factores_sep.pkl de factores_sep.py: ZQM + G&P a septiembre, con lluvia del arranque y
calor) se suman los riegos entre el corte anterior y la cosecha:
  riegos = área regada acumulada ÷ área neta (riegos «ponderados»: 1 = la suerte entera regada una vez)
  lámina = Σ (área regada × mm) ÷ área neta, en mm sobre toda la suerte
por etapa: meses 0-4, 4-8 y del 8 a la cosecha. Solo ciclos que empezaron desde 2021 (el registro de 2020 es parcial).
Lluvia y evaporación de la EMA de la suerte (La Paila / Bugalagrande) por etapa, para comparar riego con déficit.

Modelo: el mismo de factores_sep.py (efectos fijos de suerte, año y mes, edad, soca, variedad, incendio, mecánica por
año, lluvia del arranque y calor) + riegos por etapa + lluvia y evaporación por etapa. Ojo: el riego se programa donde
falta agua (prioridad por balance hídrico), así que su efecto «dentro del año» tiende a salir menor que el real.

Uso: python riego_2026.py <CONSOLIDADO DE RIEGOS.xlsx> <rio_factores_sep.pkl> <carpeta del repo Precipitacion-riopaila>
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
XLS, PKL, REPO = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
wm = lambda g, k: np.average(g[k].dropna(), weights=g.Area[g[k].notna()]) if g[k].notna().any() else np.nan  # noqa: E731

# ---------------------------------------------------------------- riegos
wb = openpyxl.load_workbook(XLS, read_only=True, data_only=True)
filas = list(wb["Consolidado de riegos "].iter_rows(values_only=True))
h = next(i for i, r in enumerate(filas) if r and str(r[0]).strip() == "Fecha")
enc = [str(c).strip() if c is not None else f"c{j}" for j, c in enumerate(filas[h])]
R = pd.DataFrame(filas[h + 1:], columns=enc)
R = R[R.Fecha.notna()].copy()
n0 = len(R)
R["f"] = pd.to_datetime(R.Fecha, errors="coerce")
R["ste"] = R["SEC-SUERTE"].astype(str).str.strip()
R["a"] = pd.to_numeric(R["ÁREA REGADA"], errors="coerce")
R["mm"] = pd.to_numeric(R["MM"], errors="coerce")
R["an"] = pd.to_numeric(R["ÁREA NETA"], errors="coerce")
dup = R.duplicated(subset=[c for c in enc if not c.startswith("c")], keep="first")
print(f"registros: {n0:,} · filas idénticas repetidas: {int(dup.sum()):,} · sin fecha válida: {int(R.f.isna().sum())}")
print(f"  área regada mayor que el área neta: {int((R.a > R.an * 1.01).sum())} · lámina > 300 mm: {int((R.mm > 300).sum())} · "
      f"lámina 0 o vacía: {int(((R.mm <= 0) | R.mm.isna()).sum())}")
R = R[~dup & R.f.notna() & (R.a > 0)].copy()
R["mm_ok"] = R.mm.where(R.mm.between(20, 300), R.mm.where(R.mm.between(20, 300)).median())
R["vol"] = R.a * R.mm_ok  # ha·mm
print("riegos por año (ha regadas):", R.groupby(R.f.dt.year).a.sum().round(0).to_dict())
print("lámina mediana por riego (mm):", R.groupby(R.f.dt.year).mm_ok.median().round(0).to_dict())
print("LABOR:", R.LABOR.astype(str).value_counts().to_dict())
G = {s: g.sort_values("f") for s, g in R.groupby("ste")}

# ---------------------------------------------------------------- cosechas
c = pd.read_pickle(PKL)
c = c[(c.ini >= "2021-01-01") & (c.anio >= 2022)].copy()
sin = ~c.ste.isin(G)
print(f"\ncosechas 2022-2026 (ciclo desde 2021): {len(c):,} · sin ningún riego registrado en la suerte: {int(sin.sum())} "
      f"({100 * c.Area[sin].sum() / c.Area.sum():.0f} % del área)")
TR = {"e0_4": (0, 4), "e4_8": (4, 8), "fin": (8, 99)}


def sumar(ste, ini, fin, area):
    g = G.get(ste)
    out = {}
    for k, (a, b) in TR.items():
        d0 = ini + pd.Timedelta(days=30.44 * a)
        d1 = min(fin, ini + pd.Timedelta(days=30.44 * b))
        if g is None or d1 <= d0:
            out[f"rg_{k}"], out[f"mm_{k}"] = 0.0, 0.0
            continue
        x = g[(g.f >= d0) & (g.f < d1)]
        out[f"rg_{k}"] = x.a.sum() / area
        out[f"mm_{k}"] = x.vol.sum() / area
    out["rg_tot"] = sum(out[f"rg_{k}"] for k in TR)
    out["mm_tot"] = sum(out[f"mm_{k}"] for k in TR)
    return out


c = pd.concat([c.reset_index(drop=True),
               pd.DataFrame([sumar(s, i, f, a) for s, i, f, a in zip(c.ste, c.ini, c.cosecha, c.Area)])], axis=1)

# lluvia y evaporación de la EMA por etapa
e = pd.read_csv(REPO / "clima_estaciones.csv", sep=";")
e["f"] = pd.to_datetime(e.fc_obsrvcion)
EMA = {k: g.set_index("f").sort_index()[["prcptcion", "evp_clclada"]] for k, g in e.groupby("nm_ema")}


def clima(est, ini, fin):
    s = EMA[est]
    out = {}
    for k, (a, b) in TR.items():
        d0, d1 = ini + pd.Timedelta(days=30.44 * a), min(fin, ini + pd.Timedelta(days=30.44 * b))
        x = s.loc[d0:d1 - pd.Timedelta(days=1)]
        n = max((d1 - d0).days, 0)
        ok = x.prcptcion.notna().sum() >= 0.7 * n and n > 0
        out[f"llu_{k}"] = x.prcptcion.mean() * n if ok else np.nan
        out[f"et_{k}"] = x.evp_clclada.mean() * n if ok else np.nan
    return out


c = pd.concat([c, pd.DataFrame([clima(s, i, f) for s, i, f in zip(c.est, c.ini, c.cosecha)])], axis=1)
for k in TR:
    c[f"def_{k}"] = c[f"et_{k}"] - c[f"llu_{k}"] - c[f"mm_{k}"]  # déficit que quedó después del riego (mm)
    c[f"defsr_{k}"] = c[f"et_{k}"] - c[f"llu_{k}"]  # déficit sin contar el riego
c.to_pickle("rio_riego.pkl")

# ---------------------------------------------------------------- descriptivo
print("\nPor año de cosecha (ponderado por área; riegos = veces que se regó la suerte completa):")
cols = ["rg_tot", "rg_e0_4", "rg_e4_8", "rg_fin", "mm_tot", "llu_fin", "et_fin", "defsr_fin", "def_fin", "d32"]
t = c.groupby("anio").apply(lambda g: pd.Series({k: wm(g, k) for k in cols} | {"cortes": len(g),
                                                                                 "% sin riego al final": 100 * g.Area[g.rg_fin == 0].sum() / g.Area.sum()}))
print(t.round(1).to_string())
print("\nMismos meses (ene-sep), 2026 frente a 2022-25:")
q, r = c[(c.anio == 2026) & (c.Mes <= 9)], c[c.anio.between(2022, 2025) & (c.Mes <= 9)]
for k in cols:
    print(f"  {k:10s} 2026 {wm(q, k):8.1f} · 2022-25 {wm(r, k):8.1f}")
print("\n2026 por mes de cosecha: riegos al final / déficit sin riego al final (mm) / déficit después del riego:")
print(c[c.anio == 2026].groupby("Mes").apply(lambda g: (round(wm(g, "rg_fin"), 1), round(wm(g, "defsr_fin")), round(wm(g, "def_fin")))).to_dict())
print("referencia 2022-25 por mes:", c[c.anio.between(2022, 2025)].groupby("Mes").apply(
    lambda g: (round(wm(g, "rg_fin"), 1), round(wm(g, "defsr_fin")), round(wm(g, "def_fin")))).to_dict())

# ---------------------------------------------------------------- modelo
ED = "C(edad_b, Treatment('12-13'))"
mec = " + ".join(f"mec_{y}" for y in range(2022, 2027))
base = f"y ~ C(ste) + C(anio) + C(Mes) + {ED} + C(soca_b) + C(var) + inc + Corte + {mec} + llu03_100 + d32"
d = c.dropna(subset=["llu03", "d32", "llu_e0_4", "llu_e4_8", "llu_fin"]).copy()
for k in TR:
    for v in ("llu", "et", "mm", "def", "defsr"):
        d[f"{v}100_{k}"] = d[f"{v}_{k}"] / 100


def fit(f):
    mo = smf.wls(f, data=d, weights=d.Area)
    rows = mo.data.row_labels
    return mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.loc[rows, "ste"])[0]})


print(f"\nModelo (cosechas 2022-sep 2026 con ciclo desde 2021, n={len(d)}):")
specs = {
    "A. número de riegos por etapa": " + rg_e0_4 + rg_e4_8 + rg_fin + llu100_e4_8 + llu100_fin + et100_e4_8 + et100_fin",
    "B. lámina de riego por etapa (por 100 mm)": " + mm100_e0_4 + mm100_e4_8 + mm100_fin + llu100_e4_8 + llu100_fin + et100_e4_8 + et100_fin",
    "C. déficit que quedó después del riego (por 100 mm)": " + def100_e0_4 + def100_e4_8 + def100_fin",
}
res = {}
for nom, extra in specs.items():
    mo = fit(base + extra)
    res[nom] = mo
    print(f"  {nom}:")
    for k, v in mo.params.items():
        if k.startswith(("rg_", "mm100", "def100", "llu100", "et100")):
            print(f"     {k:12s} {100 * (np.exp(v) - 1):+6.2f} %  (p={mo.pvalues[k]:.3f})")
# aporte a 2026 frente a 2022-25, mismos meses
q, r = d[(d.anio == 2026) & (d.Mes <= 9)], d[d.anio.between(2022, 2025) & (d.Mes <= 9)]
for nom, ks in (("A. número de riegos por etapa", ["rg_e0_4", "rg_e4_8", "rg_fin"]),
                ("B. lámina de riego por etapa (por 100 mm)", ["mm100_e0_4", "mm100_e4_8", "mm100_fin"]),
                ("C. déficit que quedó después del riego (por 100 mm)", ["def100_e0_4", "def100_e4_8", "def100_fin"])):
    mo = res[nom]
    ap = {k: mo.params[k] * (wm(q, k) - wm(r, k)) for k in ks}
    tot = sum(ap.values())
    print(f"\n  aporte a ene-sep 2026 frente a 2022-25 según {nom[:2]}: {100 * (np.exp(tot) - 1):+.1f} % "
          f"(" + ", ".join(f"{k} {100 * (np.exp(v) - 1):+.1f}" for k, v in ap.items()) + ")")
# dosis-respuesta al final, dentro del año y de la suerte
d["rg_fin_g"] = pd.cut(d.rg_fin, [-0.01, 0, 1, 2, 3, 99], labels=["0", "≤1", "1-2", "2-3", ">3"])
mo = fit(base + " + C(rg_fin_g) + llu100_fin + et100_fin")
print("\n  riegos del mes 8 a la cosecha frente a ninguno:",
      {k.split("[T.")[1][:-1]: f"{100 * (np.exp(v) - 1):+.1f} % (p={mo.pvalues[k]:.2f})" for k, v in mo.params.items() if k.startswith("C(rg_fin_g)")},
      "| % del área ene-sep 2026 / 2022-25:",
      {a_: (100 * x.groupby("rg_fin_g", observed=False).Area.sum() / x.Area.sum()).round(0).to_dict()
       for a_, x in (("2026", d[(d.anio == 2026) & (d.Mes <= 9)]), ("2022-25", d[d.anio.between(2022, 2025) & (d.Mes <= 9)]))})
