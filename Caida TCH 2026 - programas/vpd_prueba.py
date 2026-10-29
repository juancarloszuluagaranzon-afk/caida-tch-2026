# -*- coding: utf-8 -*-
"""Riopaila: ¿el VPD o la humedad relativa explican la caída del TCH mejor que los días >32 °C? Prueba aparte (no cambia
el modelo ni el informe).

Base: rio_integrado_dataset.pkl (caida_integrada_rio.py) y el diario de Cenicaña de las EMA La Paila (PAI) y
Bugalagrande (BLG) con Tmax, Tmed y humedad relativa media (etp_cenicana\\etp_diaria_PAI_BLG.csv). Cada cosecha toma su
EMA (la misma columna «est» que usa el calor) y las mismas ventanas:
  · 30 días antes de cosechar (la ventana de los días >32 °C);
  · 120 días antes de cosechar (≈ mes 8 a la cosecha, la ventana de la sequía).
VPD del mediodía = es(Tmax) − es(Tmed) × HR/100 (kPa; es de Tetens, la presión real con la HR media del día); se usa en
décimas de kPa. HR en puntos de %. Días válidos: HR 20-100 %, Tmed 15-35 °C; se exige ≥ 20 de 30 (≥ 80 de 120) días.

Variantes (mismo modelo integrado: efectos fijos de suerte, año y mes, ponderado por área, errores agrupados por suerte):
  base (d32) · VPD en lugar de d32 · d32 + VPD · HR en lugar de d32 · d32 + HR · base + VPD de 120 días · base + HR 120.
Para cada una: efecto, p, aporte en 2026 frente a 2020-25 (ene-sep), y la prueba sin ver el año (V1: cada año 2013-2026
con un modelo que no lo vio; V2: 2026 con el modelo completo ajustado con 2011-2025), con el mismo método de
validacion_modelo.py.

Uso: python vpd_prueba.py <datos intermedios> <salida.xlsx>
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 220)
PK, SAL = Path(sys.argv[1]), sys.argv[2]
pct = lambda v: 100 * (np.exp(v) - 1)  # noqa: E731
wm = lambda v, w: float(np.average(v, weights=w)) if len(v) and np.sum(w) > 0 else np.nan  # noqa: E731

# ---------------------------------------------------------------- clima diario de Cenicaña
d = pd.read_csv(PK / "etp_cenicana" / "etp_diaria_PAI_BLG.csv", parse_dates=["fecha"])
ok = d.hr_media.between(20, 100) & d.tmed.between(15, 35) & d.tmax.between(15, 42)
d.loc[~ok, ["hr_media", "tmed", "tmax"]] = np.nan
es = lambda t: 0.6108 * np.exp(17.27 * t / (t + 237.3))  # noqa: E731
d["vpd"] = 10 * (es(d.tmax) - es(d.tmed) * d.hr_media / 100)  # décimas de kPa
dias = pd.date_range("2009-12-01", "2026-12-31")
CL = {nom: d[d.est == cod].set_index("fecha")[["vpd", "hr_media"]].reindex(dias)
      for nom, cod in (("La Paila", "PAI"), ("Bugalagrande", "BLG"))}


def media(s, f, n, minimo):
    v = s.loc[f - pd.Timedelta(days=n): f - pd.Timedelta(days=1)]
    return v.mean() if v.notna().sum() >= minimo else np.nan


c = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
c = c[(c.anio >= 2011) & c.llu03.notna() & c.d32.notna() & c.y.notna()].copy().reset_index(drop=True)
for n, mn, suf in ((30, 20, "30"), (120, 80, "120")):
    c["vpd" + suf] = [media(CL[e].vpd, f, n, mn) for e, f in zip(c.est, c.cosecha)]
    c["hr" + suf] = [media(CL[e].hr_media, f, n, mn) for e, f in zip(c.est, c.cosecha)]
NUEVAS_CL = ["vpd30", "hr30", "vpd120", "hr120"]
falta = c[NUEVAS_CL].isna().any(axis=1)
print(f"cosechas: {len(c)} · sin VPD/HR completo: {int(falta.sum())} (se rellenan con el promedio del mes y año de su EMA)")
for k in NUEVAS_CL:  # pocos huecos: el promedio de las cosechas del mismo año, mes y EMA
    c[k] = c[k].fillna(c.groupby(["anio", "Mes", "est"])[k].transform("mean")).fillna(c.groupby(["anio", "est"])[k].transform("mean"))
print("correlación entre cosechas:")
print(c[["d32", "vpd30", "hr30", "vpd120", "hr120", "def100"]].corr().round(2).to_string())

MESES = range(1, 10)
q = c[(c.anio == 2026) & c.Mes.isin(MESES)]
ref = c[c.anio.between(2020, 2025) & c.Mes.isin(MESES)]
tch26 = wm(np.exp(q.y), q.Area)
niv = pd.DataFrame({k: [wm(ref[k], ref.Area), wm(q[k], q.Area)] for k in ["d32"] + NUEVAS_CL}, index=["2020-25", "2026"]).T
niv["cambio"] = niv["2026"] - niv["2020-25"]
print("\nniveles ene-sep (ponderado por área):")
print(niv.round(2).to_string())

# ---------------------------------------------------------------- modelo integrado con cada variante
ED = "C(edad_b, Treatment('12-13'))"
MEC = " + ".join(f"mec_{y}" for y in range(2011, 2027))
NUEVAS = ["def100", "def_na", "rot_tard", "rot_na", "mal_extra30", "mal_na", "fert_120", "fert_na", "lab_na", "no_renov",
          "pm_new", "pm_seg", "pm_nd", "p_na", "nf_exc15", "nf_na", "ca_mm100", "cah_na"]
BASE = f"y ~ C(ste) + C(anio) + C(Mes) + {ED} + C(soca_b) + C(var) + inc + Corte + {MEC} + llu03_100 + " + " + ".join(NUEVAS)
VARIANTES = {
    "base (días >32 °C)": ["d32"],
    "VPD 30 días en lugar de >32 °C": ["vpd30"],
    "días >32 °C + VPD 30 días": ["d32", "vpd30"],
    "HR 30 días en lugar de >32 °C": ["hr30"],
    "días >32 °C + HR 30 días": ["d32", "hr30"],
    "base + VPD 120 días": ["d32", "vpd120"],
    "base + HR 120 días": ["d32", "hr120"],
}
UNID = {"d32": "por día >32 °C", "vpd30": "por 0,1 kPa", "vpd120": "por 0,1 kPa", "hr30": "por punto de HR", "hr120": "por punto de HR"}
filas, modelos = [], {}
for nom, ks in VARIANTES.items():
    m = smf.wls(BASE + " + " + " + ".join(ks), data=c, weights=c.Area)
    m = m.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(c.loc[m.data.row_labels, "ste"])[0]})
    modelos[nom] = m
    for k in ks:
        ap = m.params[k] * niv.loc[k, "cambio"]
        filas.append({"variante": nom, "variable": k, "efecto %": pct(m.params[k]), "unidad": UNID[k], "p": m.pvalues[k],
                      "cambio 2026": niv.loc[k, "cambio"], "aporte %": pct(ap), "aporte TCH": ap * tch26,
                      "R2": m.rsquared, "AIC": m.aic})
    print(f"{nom:<34} " + " · ".join(f"{k} {pct(m.params[k]):+.2f} % (p {m.pvalues[k]:.3f})" for k in ks)
          + f" · R² {m.rsquared:.4f}")
efectos = pd.DataFrame(filas)

# ---------------------------------------------------------------- prueba sin ver el año (método de validacion_modelo.py)
c["mec_rec"] = c.mec * (c.anio >= 2023)
EDADES = ["<9", "9-10", "10-11", "11-12", "13-14", "14-15", ">15"]
NUC0 = ["llu03_100", "mec", "mec_rec", "inc", "Corte", "pm_new", "pm_seg", "pm_nd", "p_na", "ca_mm100", "cah_na"]
AGUA = ["def100", "def_na", "nf_exc15", "nf_na"]
LAB = ["rot_tard", "rot_na", "mal_extra30", "mal_na", "fert_120", "fert_na", "lab_na"]
NA = ["def_na", "rot_na", "mal_na", "fert_na", "lab_na", "p_na", "nf_na", "cah_na"]
DISP = {"ca_mm100": ["cah_na", "p_na"], "def100": ["def_na"], "nf_exc15": ["nf_na"], "rot_tard": ["lab_na", "rot_na"],
        "mal_extra30": ["lab_na", "mal_na"], "fert_120": ["lab_na", "fert_na"]}


def diseno(d, cont):
    X = d[cont].astype(float).copy()
    soca = pd.Series(np.asarray(d.soca_b, dtype=object).astype(str), index=d.index)
    var = pd.Series(np.asarray(d["var"], dtype=object).astype(str), index=d.index)
    edad = pd.Series(np.asarray(d.edad_b, dtype=object).astype(str), index=d.index)
    for k in EDADES:
        X["e_" + k] = (edad == k).astype(float)
    for k in sorted(soca.unique())[1:]:
        X["s_" + k] = (soca == k).astype(float)
    for k in sorted(v for v in var.unique() if v not in ("otra", "nan")):
        X["v_" + k] = (var == k).astype(float)
    for m in range(2, 13):
        X[f"m_{m}"] = (d.Mes == m).astype(float)
    for a in sorted(d.anio.unique()):
        X[f"a_{a}"] = (d.anio == a).astype(float)
    return X


def ajustar(d, X):
    w = d.Area.values.astype(float)
    g = d.ste.values
    Z = pd.concat([X, d[["y"]]], axis=1).astype(float)
    sw_g = pd.Series(w, index=d.index).groupby(g).transform("sum")
    Z = Z - Z.mul(w, axis=0).groupby(g).transform("sum").div(sw_g, axis=0)
    cols = [k for k in X.columns if Z[k].abs().max() > 1e-9]
    s = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(Z[cols].values * s[:, None], Z["y"].values * s, rcond=None)
    return pd.Series(beta, index=cols).reindex(X.columns).fillna(0.0)


def mes(X, b):
    k = [col for col in X.columns if col.startswith("m_")]
    return X[k].values @ b[k].values


def aporte_cols(d, X, b, ks, eref, idx):
    out = np.zeros(len(idx))
    pos = d.index.get_indexer(idx)
    for k in ks:
        if b[k] == 0:
            continue
        v = X[k].values * b[k]
        okd = np.ones(len(d), bool)
        for na in DISP.get(k, []):
            okd &= d[na].values == 0
        sel = eref & okd
        r = pd.DataFrame({"ste": d.ste.values[sel], "v": v[sel], "w": d.Area.values[sel]})
        bk = (r.v * r.w).groupby(r.ste).sum() / r.w.groupby(r.ste).sum()
        glob = float(np.average(r.v, weights=r.w)) if len(r) else 0.0
        ref_q = d.ste.iloc[pos].map(bk).fillna(glob).values
        out += np.where(okd[pos], v[pos] - ref_q, 0.0)
    return out


def anomalias(d, X, b, Y, ventana):
    ya = d.y.values - mes(X, b)
    t = pd.DataFrame({"ste": d.ste.values, "anio": d.anio.values, "w": d.Area.values, "ya": ya}, index=d.index)
    eref = t.anio.isin(ventana).values
    base = t[eref].groupby("ste").apply(lambda g: wm(g.ya, g.w)).rename("ya_ref")
    q_ = t[t.anio == Y].join(base, on="ste").dropna(subset=["ya_ref"])
    q_["real"] = q_.ya - q_.ya_ref
    ks = [k for k in X.columns if not k.startswith("m_") and k not in NA and not k.startswith("a_")]
    q_["pred"] = aporte_cols(d, X, b, ks, eref, q_.index)
    return q_


def r2(yv, pv, w):
    return 1 - np.sum(w * (yv - pv) ** 2) / np.sum(w * (yv - np.average(yv, weights=w)) ** 2)


val, anual = [], []
for nom, ks in VARIANTES.items():
    X = diseno(c, ks + NUC0)
    f1 = []
    for Y in range(2013, 2027):
        tr = c.anio != Y
        qq = anomalias(c, X, ajustar(c[tr], X[tr]), Y, range(Y - 6, Y))
        if Y == 2026:
            qq = qq[c.loc[qq.index, "Mes"] <= 9]
        f1.append({"variante": nom, "anio": Y, "real": pct(wm(qq.real, qq.w)), "predicho": pct(wm(qq.pred, qq.w))})
    v1 = pd.DataFrame(f1)
    anual.append(v1)
    X2 = diseno(c, ks + NUC0 + AGUA + LAB)
    tr = c.anio <= 2025
    b2 = ajustar(c[tr], X2[tr])
    q2 = anomalias(c, X2, b2, 2026, range(2020, 2026))
    q2 = q2[c.loc[q2.index, "Mes"] <= 9]
    A, P = wm(q2.real, q2.w), wm(q2.pred, q2.w)
    val.append({"variante": nom, "V1 correlación años": np.corrcoef(v1.real, v1.predicho)[0, 1],
                "V1 sentido (de 14)": int((np.sign(v1.real) == np.sign(v1.predicho)).sum()),
                "V1 error medio %": (v1.real - v1.predicho).abs().mean(),
                "V2 explica % de la caída 2026": 100 * P / A, "V2 R² suerte por suerte": r2(q2.real.values, q2.pred.values, q2.w.values)})
val = pd.DataFrame(val)
print("\nprueba sin ver el año:")
print(val.round(3).to_string(index=False))

with pd.ExcelWriter(SAL, engine="openpyxl") as wr:
    pd.DataFrame({"nota": [
        "Prueba aparte: VPD y humedad relativa frente a los días >32 °C en el modelo integrado de la versión 3.",
        "VPD del mediodía = es(Tmax) − es(Tmed) × HR media/100, EMA La Paila y Bugalagrande (diario de Cenicaña).",
        "Ventanas: 30 días antes de cosechar (la del calor) y 120 días (≈ mes 8 a la cosecha).",
        f"Aporte TCH ≈ aporte en log × TCH real 2026 de estas cosechas ({tch26:.1f}); ene-sep 2026 frente a 2020-25.",
        "No cambia el modelo, el informe ni el soporte."]}).to_excel(wr, sheet_name="Nota", index=False)
    niv.reset_index(names="variable").to_excel(wr, sheet_name="Niveles", index=False)
    efectos.to_excel(wr, sheet_name="Efectos y aportes", index=False)
    val.to_excel(wr, sheet_name="Prueba sin ver el año", index=False)
    pd.concat(anual).to_excel(wr, sheet_name="V1 por año", index=False)
print("guardado:", SAL)
