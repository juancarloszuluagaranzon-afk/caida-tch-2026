# -*- coding: utf-8 -*-
"""Base Maduración 2026 de Castilla: ¿cuánto rinde cada clase de la matriz de calificación del equipo?
TCH de 2026 frente al promedio 2020-2025 de la misma suerte (rel), por clase 1/3/5, y todas las calificaciones juntas."""
import sys, warnings
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8"); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
b = pd.read_pickle("base_maduracion_2026.pkl")
b["ut"] = b.suerte.astype(str).str.strip(); b["MES"] = b.MES.astype(int)
h = pd.read_pickle("cas_clima3.pkl")
r26 = h[(h["AÑO"] == 2026) & (h.ten == "AGRICOLA")][["ut", "MES", "rel", "llu03", "d32"]].drop_duplicates(["ut", "MES"])
x = b.merge(r26, on=["ut", "MES"], how="left")
x["TCH"] = x["TC-Total"] / x.Area
x["vs_ppto"] = np.log(x.TCH / x["PPTO TCH"])
print(f"base: {len(b)} suertes; con historia de la suerte: {x.rel.notna().sum()}")
wm = lambda g, k: np.average(g[k].dropna(), weights=g.Area[g[k].notna()]) if g[k].notna().any() else np.nan
T = x["TC-Total"].sum()
CAL = {"Calificación Barrenadores": "Diatraea", "Calificación Edad Cosecha": "Edad de cosecha", "Calificación Incendio": "Incendio",
       "Calificación semanas": "Semanas de madurante", "Calificación Dosis": "Dosis de madurante (cc/t)", "Calificación ME": "Materia extraña",
       "Calificación TP": "Tiempo de permanencia", "Calificación Roya": "Roya", "calificación N° Corte": "Número de corte",
       "Class dias T_Max mas 32": "Días Tmax > 32 °C", "Clas 1 mes antes de cosecha": "Clima 1 mes antes", "Clasificacion 0 a 3": "Clima 0-3 meses",
       "Clas T Termico": "Térmico", "Calificación Variedad": "Variedad (desviación ppto)"}
filas = []
for c, lab in CAL.items():
    for k, g in x.groupby(c):
        filas.append({"variable": lab, "clase": int(k), "ha": g.Area.sum(), "%área": 100 * g.Area.sum() / x.Area.sum(), "TCH": g["TC-Total"].sum() / g.Area.sum(),
                      "vs su historia %": 100 * (np.exp(wm(g, "rel")) - 1), "vs ppto %": 100 * (np.exp(wm(g, "vs_ppto")) - 1)})
t = pd.DataFrame(filas)
print(t.round(1).to_string(index=False))
# ---- todas juntas (dentro de 2026, mes fijo) ----
d = x.dropna(subset=["rel"]).copy()
ren = {c: "c" + str(i) for i, c in enumerate(CAL)}
d = d.rename(columns=ren)
use = [ren[c] for c in CAL if c not in ("Calificación Variedad", "Calificación Dosis", "Clas T Termico")]
f = "rel ~ " + " + ".join(f"C({v}, Treatment(1))" for v in use) + " + C(MES)"
mo = smf.wls(f, data=d, weights=d.Area).fit(cov_type="HC1")
inv = {v: k for k, v in ren.items()}
print(f"\nTodas juntas (n={int(mo.nobs)}, R²={mo.rsquared:.2f}); efecto de la clase frente a la clase 1 (óptima):")
res = []
for k, v in mo.params.items():
    if k.startswith("C(c"):
        var = k.split(",")[0][2:]; cl = int(float(k.split("[T.")[1][:-1]))
        res.append({"variable": CAL[inv[var]], "clase": cl, "efecto %": 100 * (np.exp(v) - 1), "p": mo.pvalues[k]})
res = pd.DataFrame(res); print(res.round(3).to_string(index=False))
# toneladas: lo que costaron las clases 3 y 5 frente a la 1, por variable
print("\nToneladas que cuestan las clases malas (efecto × caña de esas suertes), variables con p<0,10:")
for var in use:
    tot = 0
    for cl in [3, 5]:
        k = f"C({var}, Treatment(1))[T.{cl}]"
        if k in mo.params and mo.pvalues[k] < 0.10:
            g = d[d[var] == cl]; tot += (g["TC-Total"] * (np.exp(-mo.params[k]) - 1)).sum()
    if tot: print(f"  {CAL[inv[var]]:<28} {tot:,.0f} t")
# ---- continuas ----
print("\nContinuas (2026, mes fijo):")
for f2, lab in [("rel ~ Barrenadores + C(MES)", "Diatraea %I.I."), ("rel ~ Q('Sem Mad') + C(MES)", "semanas de madurante (con madurante)")]:
    dd = x.dropna(subset=["rel"]) if "Sem" not in f2 else x.dropna(subset=["rel", "Sem Mad"])
    m2 = smf.wls(f2, data=dd, weights=dd.Area).fit(cov_type="HC1"); k = [p for p in m2.params.index if "Barren" in p or "Sem" in p][0]
    print(f"  {lab}: {100*m2.params[k]:+.2f}% por unidad (p={m2.pvalues[k]:.3f}, n={int(m2.nobs)})")
print("  Diatraea 2026 (base del equipo, 351 suertes):", round(wm(x, "Barrenadores"), 2), "% I.I. | área >2,5%:", round(100 * x.Area[x.Barrenadores > 2.5].sum() / x.Area.sum()))
# artefacto de la dosis por tonelada
tr = x[x["Consolidad tipo madurante"] == "Trinexapac"].dropna(subset=["Dosis"]).copy()
tr["Lha"] = tr.Dosis * tr.TCH / 1000
print(f"\nDosis Trinexapac: corr(cc/t, TCH) = {tr[['Dosis','TCH']].corr().iloc[0,1]:.2f}; corr(L/ha, TCH) = {tr[['Lha','TCH']].corr().iloc[0,1]:.2f}; L/ha mediana {tr.Lha.median():.2f}")
rng = np.random.default_rng(1); perm = tr.Lha.sample(frac=1, random_state=1).values * 1000 / tr.TCH.values
print(f"  con L/ha barajadas al azar entre suertes, corr(cc/t, TCH) = {np.corrcoef(perm, tr.TCH)[0,1]:.2f}  → la relación la crea la división por el TCH")
x.to_pickle("base_mad_rel.pkl"); t.to_pickle("tabla_clases.pkl"); res.to_pickle("efectos_clases.pkl")
