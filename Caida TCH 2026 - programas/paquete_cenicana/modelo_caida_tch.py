# -*- coding: utf-8 -*-
"""Riopaila: por qué cayó el TCH de lo cosechado ene-sep 2026. Modelo y aportes de cada causa, desde la tabla por cosecha.

Es el mismo cálculo de Riopaila (caida_integrada_rio.py), pero lee solo cosechas_riopaila_2011-2026.csv.
Modelo: regresión de log TCH (y), ponderada por área, con efectos fijos de suerte, año y mes de cosecha; edad en bandas,
número de corte (lineal + bandas), variedad, incendio, cosecha mecanizada con una brecha por año, lluvia de los meses
0-3, días >32 °C antes de cosechar, falta de agua del final del ciclo después del riego, labores (2024+), renovación no
hecha, corte anterior mecanizado, nivel freático y lluvia del corte anterior. Errores agrupados por suerte.
Aporte de una causa = coeficiente × (nivel ene-sep 2026 − nivel normal en los mismos meses). Normal: 2020-25 para
clima, cosecha, edad, variedad y corte; 2022-25 para el agua y el freático; 2024-25 para las labores (cada uno solo con
las cosechas que tienen el dato). Variedad y número de corte: frente a la historia 2020-25 de la misma suerte.
Lo que los factores no explican queda como «Sin explicar»; los aportes + «Sin explicar» suman la caída.

Uso: python modelo_caida_tch.py <cosechas_riopaila_2011-2026.csv> <salida.xlsx>
Necesita pandas, numpy, statsmodels y openpyxl.
"""
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
CSV, SAL = sys.argv[1], sys.argv[2]
EDADES = ["<9", "9-10", "10-11", "11-12", "12-13", "13-14", "14-15", ">15"]
MESES = range(1, 10)
wm = lambda g, k: np.average(g[k], weights=g.Area) if len(g) else np.nan  # noqa: E731

c = pd.read_csv(CSV, encoding="utf-8-sig", parse_dates=["cosecha", "ini"])

# ---------------------------------------------------------------- modelo
ED = "C(edad_b, Treatment('12-13'))"
MEC = " + ".join(f"mec_{y}" for y in range(2011, 2027))
NUEVAS = ["def100", "def_na", "rot_tard", "rot_na", "mal_extra30", "mal_na", "fert_120", "fert_na", "lab_na", "no_renov",
          "pm_new", "pm_seg", "pm_nd", "p_na", "nf_exc15", "nf_na", "ca_mm100", "cah_na"]
f = f"y ~ C(ste) + C(anio) + C(Mes) + {ED} + C(soca_b) + C(var) + inc + Corte + {MEC} + llu03_100 + d32 + " + " + ".join(NUEVAS)
est = c.dropna(subset=["llu03", "d32"])
mo = smf.wls(f, data=est, weights=est.Area)
mo = mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(est.loc[mo.data.row_labels, "ste"])[0]})
P = mo.params
print(f"modelo: n={int(mo.nobs)}, R²={mo.rsquared:.2f}")
# probadas y sin efecto: lluvia en los 5 días antes de la roturación y de la fertilización (cosechas 2024-26)
mp = smf.wls(f + " + rot_mm10 + roth_na + fert_mm10 + ferth_na", data=est, weights=est.Area)
mp = mp.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(est.loc[mp.data.row_labels, "ste"])[0]})
PROBADAS = pd.DataFrame([{"variable": n, "efecto %": 100 * (np.exp(mp.params[k]) - 1), "p": mp.pvalues[k], "unidad": "por 10 mm"}
                         for n, k in (("Roturación en suelo húmedo", "rot_mm10"), ("Fertilización en suelo húmedo", "fert_mm10"))])

# ---------------------------------------------------------------- aportes ene-sep 2026
q = c[(c.anio == 2026) & c.Mes.isin(MESES)].copy()
ref = c[c.anio.between(2020, 2025) & c.Mes.isin(MESES)].copy()
ref_agua = c[c.anio.between(2022, 2025) & c.Mes.isin(MESES) & (c.def_na == 0)]
ref_lab = c[c.anio.between(2024, 2025) & c.Mes.isin(MESES) & (c.lab_na == 0)]
ref_nf = c[c.anio.between(2022, 2025) & c.Mes.isin(MESES) & (c.nf_na == 0)]
PM = ["pm_new", "pm_seg", "pm_nd"]
nf26 = q[q.nf_na == 0]
NIVEL = {}


def humedo(k, ok, refd):
    """coeficiente × (nivel 2026 − nivel normal), los dos solo con dato, × parte de 2026 con dato."""
    a, b = q[ok(q)], refd[ok(refd)]
    NIVEL[k] = (wm(a, k), wm(b, k), a.Area.sum() / q.Area.sum())
    return P[k] * (NIVEL[k][0] - NIVEL[k][1]) * NIVEL[k][2]


def lab(k, na):
    """coeficiente × (nivel 2026 − nivel 2024-25), los dos solo con lo registrado, × parte de 2026 registrada."""
    reg26, regR = q[(q.lab_na == 0) & (q[na] == 0)], ref_lab[ref_lab[na] == 0]
    NIVEL[k] = (wm(reg26, k), wm(regR, k), reg26.Area.sum() / q.Area.sum())
    return P[k] * (NIVEL[k][0] - NIVEL[k][1]) * NIVEL[k][2]


ok_ca = lambda d: d.mm_ca.notna() & (d.p_na == 0)  # noqa: E731
T, HA = q["TC-Total"].sum(), q.Area.sum()
gap = wm(q.dropna(subset=["rel"]), "rel") - wm(ref.dropna(subset=["rel"]), "rel")
for k in EDADES:
    q["e_" + k], ref["e_" + k] = (q.edad_b == k).astype(float), (ref.edad_b == k).astype(float)
ed = {k: P.get(f"{ED}[T.{k}]", 0.0) for k in EDADES}
bv = {k.split("[T.")[1][:-1]: v for k, v in P.items() if k.startswith("C(var)")}

# número de corte: efecto completo (por corte + banda), frente a la historia 2020-25 de la misma suerte
bandas = {k.split("[T.")[1][:-1]: v for k, v in P.items() if k.startswith("C(soca_b)")}
fcorte = P["Corte"] * c.Corte + c.soca_b.map(bandas).fillna(0.0)
r20 = c.anio.between(2020, 2025)
propio = (fcorte * c.Area)[r20].groupby(c.ste[r20]).sum() / c.Area[r20].groupby(c.ste[r20]).sum()
q["corte_rel"] = (fcorte.loc[q.index] - q.ste.map(propio)).fillna(0.0)
# variedades: la variedad de 2026 frente a la que tuvo la misma suerte en 2020-25
fvar = c["var"].map(bv).fillna(0.0)
propia_v = (fvar * c.Area)[r20].groupby(c.ste[r20]).sum() / c.Area[r20].groupby(c.ste[r20]).sum()
q["var_rel"] = (fvar.loc[q.index] - q.ste.map(propia_v)).fillna(0.0)

A = {
    "Calor (días >32 °C)": P["d32"] * (wm(q, "d32") - wm(ref, "d32")),
    "Lluvia del arranque (0-3 meses)": P["llu03_100"] * (wm(q, "llu03_100") - wm(ref, "llu03_100")),
    "Sequía al final del ciclo": P["def100"] * (wm(q[q.def_na == 0], "defsr100") - wm(ref_agua, "defsr100")),
    "Riego aplicado": -P["def100"] * (wm(q[q.def_na == 0], "mm100") - wm(ref_agua, "mm100")),
    "Renovación no hecha": P["no_renov"] * wm(q, "no_renov"),
    "Roturación tardía": lab("rot_tard", "rot_na"),
    "Malezas (herbicida después de 90 días)": lab("mal_extra30", "mal_na"),
    "Fertilización después de 120 días": lab("fert_120", "fert_na"),
    "Cosecha mecanizada": P["mec_2026"] * wm(q, "mec_2026") - sum(P[f"mec_{y}"] * wm(ref, f"mec_{y}") for y in range(2020, 2026)),
    "Corte anterior mecanizado": sum(P[k] * (wm(q, k) - wm(ref, k)) for k in PM),
    "Corte anterior en suelo húmedo": humedo("ca_mm100", ok_ca, ref),
    "Nivel freático": P["nf_exc15"] * (wm(nf26, "nf_exc15") - wm(ref_nf, "nf_exc15")) * nf26.Area.sum() / q.Area.sum(),
    "Variedades": wm(q, "var_rel"),
    "Edad de cosecha": sum(ed[k] * (wm(q, "e_" + k) - wm(ref, "e_" + k)) for k in EDADES),
    "Número de corte": wm(q, "corte_rel"),
    "Incendio": P["inc"] * (wm(q, "inc") - wm(ref, "inc")),
}
A["Sin explicar"] = gap - sum(A.values())

# lo mismo, cosecha por cosecha (en log); sin dato → 0
reg = lambda na: ((q.lab_na == 0) & (q[na] == 0)).astype(float)  # noqa: E731
agua = (q.def_na == 0).astype(float)
POR = pd.DataFrame({
    "Calor (días >32 °C)": P["d32"] * (q.d32 - wm(ref, "d32")).fillna(0),
    "Lluvia del arranque (0-3 meses)": P["llu03_100"] * (q.llu03_100 - wm(ref, "llu03_100")).fillna(0),
    "Sequía al final del ciclo": P["def100"] * (q.defsr100 - wm(ref_agua, "defsr100")) * agua,
    "Riego aplicado": -P["def100"] * (q.mm100 - wm(ref_agua, "mm100")) * agua,
    "Renovación no hecha": P["no_renov"] * q.no_renov,
    "Roturación tardía": P["rot_tard"] * (q.rot_tard - NIVEL["rot_tard"][1]) * reg("rot_na"),
    "Malezas (herbicida después de 90 días)": P["mal_extra30"] * (q.mal_extra30 - NIVEL["mal_extra30"][1]) * reg("mal_na"),
    "Fertilización después de 120 días": P["fert_120"] * (q.fert_120 - NIVEL["fert_120"][1]) * reg("fert_na"),
    "Cosecha mecanizada": P["mec_2026"] * q.mec_2026 - sum(P[f"mec_{y}"] * wm(ref, f"mec_{y}") for y in range(2020, 2026)),
    "Corte anterior mecanizado": sum(P[k] * (q[k] - wm(ref, k)) for k in PM),
    "Corte anterior en suelo húmedo": P["ca_mm100"] * (q.ca_mm100 - NIVEL["ca_mm100"][1]) * ok_ca(q),
    "Nivel freático": P["nf_exc15"] * (q.nf_exc15 - wm(ref_nf, "nf_exc15")) * (1 - q.nf_na),
    "Variedades": q.var_rel,
    "Edad de cosecha": sum(ed[k] * (q["e_" + k] - wm(ref, "e_" + k)) for k in EDADES),
    "Número de corte": q.corte_rel,
    "Incendio": P["inc"] * (q.inc - wm(ref, "inc")),
}, index=q.index)
POR["caída"] = q.rel - wm(ref.dropna(subset=["rel"]), "rel")
POR["Sin explicar"] = POR["caída"] - POR.drop(columns="caída").sum(axis=1)

tab = pd.DataFrame({"% TCH": {k: 100 * v for k, v in A.items()}, "t": {k: -v * T for k, v in A.items()}})
tab["% de la caída"] = 100 * tab.t / (-gap * T)
tab = tab.sort_values("t", ascending=False)
print(f"\nene-sep 2026 (en log): {len(q)} cosechas · {HA:,.0f} ha · {T:,.0f} t · TCH {T / HA:.1f} · frente a 2020-25 de las "
      f"mismas suertes: {100 * gap:+.1f} %")
print(tab.round(2).to_string())

# en TCH, solo las cosechas con historia 2020-25: aporte en TCH = aporte en log × TCH real × (e^L − 1)/L, con L = caída en
# log de la cosecha, así los aportes suman exacto histórico − real de cada cosecha
ok = q.rel.notna()
tch = (q["TC-Total"] / q.Area)[ok]
L = -POR.loc[ok, "caída"]
fac = np.where(L.abs() < 1e-9, tch, tch * np.expm1(L) / L)
EN_TCH = POR.loc[ok].drop(columns="caída").mul(fac, axis=0)  # negativo = le quitó TCH
w = q.Area[ok]
caida_tch = (tch * np.expm1(L)) @ w / w.sum()
tch_tab = pd.DataFrame({"TCH": EN_TCH.mul(w, axis=0).sum() / w.sum()})
tch_tab["% de la caída"] = 100 * tch_tab.TCH / -caida_tch
tch_tab = tch_tab.sort_values("TCH")
print(f"\nen TCH: {int(ok.sum())} cosechas con historia · {w.sum():,.0f} ha · histórico {(tch + tch * np.expm1(L)) @ w / w.sum():.1f}"
      f" → real {tch @ w / w.sum():.1f} TCH · caída {-caida_tch:+.1f} TCH ({caida_tch * w.sum():,.0f} t)")
print(tch_tab.round(2).to_string())

coef = pd.DataFrame({"coeficiente (log)": P, "efecto %": 100 * (np.exp(P) - 1), "error estándar": mo.bse, "p": mo.pvalues})
coef = coef[~coef.index.str.startswith("C(ste)")]
with pd.ExcelWriter(SAL, engine="openpyxl") as w:
    tch_tab.reset_index(names="causa").to_excel(w, sheet_name="Aportes en TCH", index=False)
    tab.reset_index(names="causa").to_excel(w, sheet_name="Aportes en log", index=False)
    coef.reset_index(names="variable").to_excel(w, sheet_name="Coeficientes", index=False)
    PROBADAS.to_excel(w, sheet_name="Probadas sin efecto", index=False)
    pd.concat([q[["ste", "anio", "Mes", "Area", "TC-Total"]], POR], axis=1).to_excel(w, sheet_name="Aportes por cosecha (log)",
                                                                                  index=False)
print("guardado:", SAL)
