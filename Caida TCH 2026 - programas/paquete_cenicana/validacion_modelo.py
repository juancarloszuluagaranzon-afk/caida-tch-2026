# -*- coding: utf-8 -*-
"""Riopaila: ¿el modelo de factores explica la caída del TCH? Validación con datos que el modelo no vio.

Base: cosechas_riopaila_2011-2026.csv (la tabla del paquete): cosechas de Riopaila 2011-2026 con calor (días >32 °C el mes
antes de cosechar), lluvia de los meses 0-3, cosecha mecanizada, incendio, edad, número de corte, variedad, agua al final
del ciclo (2022+), labores (2024+), corte anterior mecanizado y nivel freático del ciclo (2021+). El modelo es el mismo de
modelo_caida_tch.py: efectos fijos de suerte, año y mes de cosecha.

Anomalía de una suerte en el año Y = log TCH (ajustado por mes de cosecha) − su promedio de los 6 años anteriores.
Lo que el modelo predice = Σ efecto × (nivel del factor en Y − nivel de esa suerte en esos 6 años).
Lo que queda (real − predicho) es el golpe común del año que los factores no explican, más ruido.

V1  años que no vio: para cada año 2013-2026 se ajusta el modelo SIN ese año y se predice su anomalía.
V2  2026 sin 2026: el modelo completo (con agua y labores) ajustado solo con 2011-2025, aplicado a ene-sep 2026,
    referencia 2020-25; aporte de cada factor fuera de muestra.
V5  suertes de 2026 que no vio: validación cruzada en 5 partes dentro de 2026 (conoce el año por las demás suertes).

Uso: python validacion_modelo.py <cosechas_riopaila_2011-2026.csv> <salida.xlsx>
Necesita pandas, numpy y openpyxl.
"""
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 220)
CSV_IN, SAL = sys.argv[1], sys.argv[2]
pct = lambda v: 100 * (np.exp(v) - 1)  # noqa: E731
wm = lambda v, w: float(np.average(v, weights=w)) if len(v) and np.sum(w) > 0 else np.nan  # noqa: E731

c = pd.read_csv(CSV_IN, encoding="utf-8-sig")
c = c[(c.anio >= 2011) & c.llu03.notna() & c.d32.notna() & c.y.notna()].copy().reset_index(drop=True)
c["mec_rec"] = c.mec * (c.anio >= 2023)  # la cosecha mecanizada rinde peor desde 2023
EDADES = ["<9", "9-10", "10-11", "11-12", "13-14", "14-15", ">15"]  # referencia 12-13
NUC = ["d32", "llu03_100", "mec", "mec_rec", "inc", "Corte", "pm_new", "pm_seg", "pm_nd", "p_na", "ca_mm100", "cah_na"]
AGUA = ["def100", "def_na", "nf_exc15", "nf_na"]
LAB = ["rot_tard", "rot_na", "mal_extra30", "mal_na", "fert_120", "fert_na", "lab_na"]


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
    """WLS con efecto fijo de suerte (resta del promedio ponderado de cada suerte); columnas sin variación quedan en 0."""
    w = d.Area.values.astype(float)
    g = d.ste.values
    Z = pd.concat([X, d[["y"]]], axis=1).astype(float)
    sw_g = pd.Series(w, index=d.index).groupby(g).transform("sum")
    medias = Z.mul(w, axis=0).groupby(g).transform("sum").div(sw_g, axis=0)
    Z = Z - medias
    cols = [k for k in X.columns if Z[k].abs().max() > 1e-9]
    s = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(Z[cols].values * s[:, None], Z["y"].values * s, rcond=None)
    return pd.Series(beta, index=cols).reindex(X.columns).fillna(0.0)


# «sin registro» y «sin dato» son controles de calidad del dato, no factores: no entran en lo que se predice
NA = ["def_na", "rot_na", "mal_na", "fert_na", "lab_na", "p_na", "nf_na", "cah_na"]


def factores(X, b, con_anio=False):
    """parte de log TCH que explican los factores (sin mes ni controles de dato; con el año solo si se pide)."""
    k = [col for col in X.columns if not col.startswith("m_") and col not in NA and (con_anio or not col.startswith("a_"))]
    return X[k].values @ b[k].values


def mes(X, b):
    k = [col for col in X.columns if col.startswith("m_")]
    return X[k].values @ b[k].values


# variables que solo existen desde cierto año: su nivel normal se toma solo de las cosechas que tienen el dato (si no, los
# años sin dato, llenados con 0, contarían como «normal = 0» y el aporte de 2026 saldría inflado)
DISP = {"ca_mm100": ["cah_na", "p_na"], "def100": ["def_na"], "nf_exc15": ["nf_na"], "rot_tard": ["lab_na", "rot_na"], "mal_extra30": ["lab_na", "mal_na"],
        "fert_120": ["lab_na", "fert_na"]}


def aporte_cols(d, X, b, ks, eref, idx):
    """Σ efecto × (nivel de la cosecha − nivel normal de su suerte en las filas eref), por cosecha de idx; cada columna
    con su propia disponibilidad. Sin dato en la cosecha → 0; suerte sin referencia con dato → promedio de todas."""
    out = np.zeros(len(idx))
    for k in ks:
        if b[k] == 0:
            continue
        v = X[k].values * b[k]
        ok = np.ones(len(d), bool)
        for na in DISP.get(k, []):
            ok &= d[na].values == 0
        sel = eref & ok
        r = pd.DataFrame({"ste": d.ste.values[sel], "v": v[sel], "w": d.Area.values[sel]})
        bk = (r.v * r.w).groupby(r.ste).sum() / r.w.groupby(r.ste).sum()
        glob = float(np.average(r.v, weights=r.w)) if len(r) else 0.0
        pos = d.index.get_indexer(idx)
        ref_q = d.ste.iloc[pos].map(bk).fillna(glob).values
        out += np.where(ok[pos], v[pos] - ref_q, 0.0)
    return out


def anomalias(d, X, b, Y, ventana, con_anio=False):
    """anomalía real y predicha de cada cosecha del año Y frente a la misma suerte en `ventana` (años)."""
    ya = d.y.values - mes(X, b)  # lo real, tal como pasó (solo ajustado por el mes de cosecha)
    t = pd.DataFrame({"ste": d.ste.values, "anio": d.anio.values, "w": d.Area.values, "ya": ya}, index=d.index)
    eref = t.anio.isin(ventana).values
    base = t[eref].groupby("ste").apply(lambda g: wm(g.ya, g.w)).rename("ya_ref")
    q = t[t.anio == Y].join(base, on="ste").dropna(subset=["ya_ref"])
    q["real"] = q.ya - q.ya_ref
    ks = [k for k in X.columns if not k.startswith("m_") and k not in NA and (con_anio or not k.startswith("a_"))]
    q["pred"] = aporte_cols(d, X, b, ks, eref, q.index)
    return q


# ================================================================ V1 años que no vio
print("V1 · cada año predicho con un modelo que no lo vio (factores: calor, lluvia del arranque, cosecha mecanizada, "
      "corte anterior mecanizado, incendio, edad, corte, variedad)")
Xall = diseno(c, NUC)
filas = []
for Y in range(2013, 2027):
    tr = c.anio != Y
    b = ajustar(c[tr], Xall[tr])
    q = anomalias(c, Xall, b, Y, range(Y - 6, Y))
    if Y == 2026:
        q = q[c.loc[q.index, "Mes"] <= 9]
    filas.append({"anio": Y, "cosechas": len(q), "ha": q.w.sum(), "real": pct(wm(q.real, q.w)), "predicho": pct(wm(q.pred, q.w))})
v1 = pd.DataFrame(filas)
v1["sin_explicar"] = v1.real - v1.predicho
r = np.corrcoef(v1.real, v1.predicho)[0, 1]
mae0, mae1 = v1.real.abs().mean(), v1.sin_explicar.abs().mean()
print(v1.round(1).to_string(index=False))
print(f"  correlación real-predicho entre años: {r:.2f} · error medio sin modelo {mae0:.1f} % → con modelo {mae1:.1f} % "
      f"({100 * (1 - mae1 / mae0):.0f} % menos)")

# ================================================================ V2 2026 sin 2026 (modelo completo)
print("\nV2 · 2026 con el modelo completo ajustado solo con 2011-2025 (referencia 2020-25, ene-sep)")
X2 = diseno(c, NUC + AGUA + LAB)
tr = c.anio <= 2025
b2 = ajustar(c[tr], X2[tr])
q2 = anomalias(c, X2, b2, 2026, range(2020, 2026))
q2 = q2[c.loc[q2.index, "Mes"] <= 9]
A, P = wm(q2.real, q2.w), wm(q2.pred, q2.w)
print(f"  {len(q2)} cosechas · {q2.w.sum():,.0f} ha · anomalía real {pct(A):+.1f} % · predicha {pct(P):+.1f} % · "
      f"explica {100 * P / A:.0f} % de la caída")
# aporte de cada factor fuera de muestra: efecto × (nivel 2026 − nivel de la suerte en 2020-25)
GRUPOS = {
    "Calor (días >32 °C)": ["d32"], "Lluvia del arranque (0-3 meses)": ["llu03_100"],
    "Cosecha mecanizada": ["mec", "mec_rec"], "Corte anterior mecanizado": ["pm_new", "pm_seg", "pm_nd"], "Corte anterior en suelo húmedo": ["ca_mm100"], "Incendio": ["inc"],
    "Edad de cosecha": ["e_" + k for k in EDADES], "Número de corte": ["Corte"] + [k for k in X2.columns if k.startswith("s_")],
    "Variedades": [k for k in X2.columns if k.startswith("v_")],
    "Agua al final del ciclo (sequía y riego)": ["def100"], "Nivel freático": ["nf_exc15"],
    "Labores (roturación, malezas, fertilización)": ["rot_tard", "mal_extra30", "fert_120"],
}
ref_rows = c.anio.between(2020, 2025).values
aporte = {nom: wm(aporte_cols(c, X2, b2, ks, ref_rows, q2.index), q2.w) for nom, ks in GRUPOS.items()}
v2 = pd.DataFrame({"factor": list(aporte), "log": list(aporte.values())})
tch_real = wm(np.exp(c.loc[q2.index, "y"]), q2.w)
v2["t_ha"] = -v2.log * tch_real
v2.loc[len(v2)] = ["Sin explicar (golpe común del año y ruido)", A - P, -(A - P) * tch_real]
print(v2.round(3).to_string(index=False))


def r2(yv, pv, w):
    return 1 - np.sum(w * (yv - pv) ** 2) / np.sum(w * (yv - np.average(yv, weights=w)) ** 2)


# ================================================================ V5 suertes de 2026 que el modelo no vio, con el año conocido
print("\nV5 · suertes de 2026 que el modelo no vio, sabiendo cómo le fue al año por las demás suertes")
MEC_Y = [f"mec_{y}" for y in range(2011, 2027)]
X5 = diseno(c, ["d32", "llu03_100", "inc", "Corte", "def100", "no_renov", "pm_new", "pm_seg", "pm_nd", "nf_exc15", "ca_mm100"] + MEC_Y + NA
           + ["rot_tard", "mal_extra30", "fert_120"])
st26 = c.loc[(c.anio == 2026) & (c.Mes <= 9), "ste"].unique()
orden = np.random.default_rng(11).permutation(st26)
pred5 = pd.Series(np.nan, index=c.index)
for f_ in range(5):
    te = (c.anio == 2026) & c.ste.isin(set(orden[f_::5]))
    b5 = ajustar(c[~te], X5[~te])
    q5 = anomalias(c, X5, b5, 2026, range(2020, 2026), con_anio=True)
    q5 = q5[q5.index.isin(c.index[te & (c.Mes <= 9)])]
    pred5.loc[q5.index] = q5.pred
real5 = q2.real.reindex(c.index)
ok5 = pred5.notna() & real5.notna()
r2_5 = r2(real5[ok5].values, pred5[ok5].values, c.Area[ok5].values)
print(f"  {int(ok5.sum())} cosechas · R² suerte por suerte {r2_5:.2f}")

w5 = c.Area[ok5].values
r2_0 = r2(real5[ok5].values, q2.pred.reindex(c.index)[ok5].values, w5)
v4 = pd.DataFrame([
    {"metodo": "Nuestro modelo (no vio 2026)", "objetivo": "Caída de cada suerte frente a su historia", "r2": r2_0,
     "nota": "ajustado con 2011-2025; predice cada suerte de 2026 sin conocerla"},
    {"metodo": "Nuestro modelo (no vio esas suertes de 2026)", "objetivo": "Caída de cada suerte frente a su historia", "r2": r2_5,
     "nota": "validación cruzada en 5 partes dentro de 2026: conoce el año por las demás suertes"},
])
print("\nR² suerte por suerte (fuera de muestra)")
print(v4.assign(r2=v4.r2.round(2)).to_string(index=False))

# ================================================================ salidas
with pd.ExcelWriter(SAL, engine="openpyxl") as wr:
    v1.to_excel(wr, sheet_name="V1 años que no vio", index=False)
    v2.to_excel(wr, sheet_name="V2 2026 sin 2026", index=False)
    v4.to_excel(wr, sheet_name="V5 suerte por suerte", index=False)
    pd.DataFrame({"variable": b2.index, "efecto_log": b2.values}).to_excel(wr, sheet_name="Coeficientes V2", index=False)
print("guardado:", SAL)
