# -*- coding: utf-8 -*-
"""Variables de clima pedidas por el usuario (29-sep):
- arranque: lluvia de los meses 0-3 del ciclo (mm, 91 días desde el corte anterior)
- final: días con temperatura máxima > 32 °C en los 30 días antes de la cosecha
Riopaila: estaciones La Paila / Bugalagrande (EMA) para ambas; pluviómetros como control.
Castilla: lluvia del pluviómetro de la suerte; temperatura = promedio de las estaciones de Riopaila (no hay temperatura propia)."""
import sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8"); pd.set_option("display.width", 250)
S = r"C:\Users\Agr349\AppData\Local\Temp\claude\C--Users-Agr349\39506705-db06-4ee1-9a78-cdc4dba16d29\scratchpad"
B = r"C:\Users\Agr349\Documents\JUNTA DIRECTIVA\CASTILLA\Recursos Hidricos"
dias = pd.date_range("2009-01-01", "2026-09-30", freq="D")
e = pd.read_pickle(rf"{S}\caida\ema.pkl")
EMA = {}
for est in ["La Paila", "Bugalagrande"]:
    d = e[e.nm_ema == est].set_index("f").sort_index(); d = d[~d.index.duplicated()].reindex(dias)
    EMA[est] = d[["prcptcion", "tmp_mxma"]].rename(columns={"prcptcion": "llu", "tmp_mxma": "tmax"})
tmax_reg = pd.concat([EMA[k].tmax for k in EMA], axis=1).mean(axis=1)
def hot(tm, f):
    s = tm.loc[f - pd.Timedelta(days=30): f - pd.Timedelta(days=1)]
    return (s > 32).sum() * 30 / s.notna().sum() if s.notna().sum() >= 20 else np.nan
def rain(sr, a):
    s = sr.loc[a: a + pd.Timedelta(days=90)]
    return s.sum() * 91 / s.notna().sum() if s.notna().sum() >= 70 else np.nan

# ---------------- Riopaila (ZQM 2011-2026) ----------------
c = pd.read_pickle(rf"{S}\caida\cortes_calor.pkl"); c = c[c.empresa == "Riopaila"].copy()
m = pd.read_pickle(rf"{S}\riopaila\cortes_maduracion_sep26.pkl")[["f_cos"]]
c = c.join(m, how="left")
c["fc"] = c.f_cos.where(c.f_cos.notna() & ((c.f_cos - c.cosecha).dt.days.abs() <= 45), c.cosecha)
c["ini"] = c.fc - pd.to_timedelta(c.Edad * 30.44, unit="D")
c["est"] = np.where(c.fuente.isin(EMA), c.fuente, "La Paila")
c["llu03"] = [rain(EMA[s].llu, a) if pd.notna(a) else np.nan for s, a in zip(c.est, c.ini)]
c["d32"] = [hot(EMA[s].tmax, f) if pd.notna(f) else np.nan for s, f in zip(c.est, c.fc)]
# pluviómetros de Riopaila (control, 2020+)
q = pd.read_csv(rf"{S}\Precipitacion-riopaila\precipitacion.csv.csv", sep=";", encoding="latin-1", usecols=[0, 1, 2, 3])
q.columns = ["hac", "pluv", "fecha", "mm"]; q["fecha"] = pd.to_datetime(q.fecha, errors="coerce", dayfirst=True)
q["mm"] = pd.to_numeric(q.mm.astype(str).str.replace(",", "."), errors="coerce"); q["pluv"] = pd.to_numeric(q.pluv, errors="coerce")
P = q.dropna(subset=["fecha", "pluv"]).pivot_table(index="fecha", columns="pluv", values="mm", aggfunc="mean").reindex(dias)
Pm = P.median(axis=1)
r = pd.read_pickle(rf"{S}\riopaila\cortes_riego.pkl"); pl = r.dropna(subset=["pl"]).groupby("ste").pl.agg(lambda s: s.mode().iloc[0])
c["ste"] = c["Ubic Técnica"].astype(str).str.strip()
c["llu03_pl"] = [rain(P[pl[s]] if (s in pl.index and pl[s] in P.columns) else Pm, a) if pd.notna(a) and a >= pd.Timestamp("2020-01-01") else np.nan for s, a in zip(c.ste, c.ini)]
c.to_pickle("rio_clima2.pkl")
w = lambda g, k: np.average(g[k].dropna(), weights=g.Area[g[k].notna()]) if g[k].notna().any() else np.nan
print("Riopaila, ene-ago por año de cosecha: lluvia 0-3 m (EMA / pluviómetros) y días >32 °C en los 30 días previos")
print(c[c.Mes.between(1, 8) & (c["AÑO"] >= 2012)].groupby("AÑO").apply(lambda g: pd.Series({"llu03 EMA": w(g, "llu03"), "llu03 pluv": w(g, "llu03_pl"), "d32": w(g, "d32")})).round(0).to_string())
k = c.dropna(subset=["llu03", "llu03_pl"]); print("corr lluvia 0-3 EMA vs pluviómetro (cortes):", round(k[["llu03", "llu03_pl"]].corr().iloc[0, 1], 2))

# ---------------- Castilla (histórico por suerte 2020-2026, todas las tenencias) ----------------
h = pd.read_pickle(rf"{S}\castilla\factores\hist_factores.pkl")
p = pd.read_csv(rf"{B}\Precipitacion diaria por pluviometro.csv", sep=";", decimal=",", encoding="utf-8-sig", low_memory=False)
p["Fecha"] = pd.Timestamp("1899-12-30") + pd.to_timedelta(pd.to_numeric(p.Fecha, errors="coerce"), unit="D")
p["mm"] = pd.to_numeric(p.Precipitacion.astype(str).str.replace(",", "."), errors="coerce")
p["PLUV"] = p.PLUV.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
L = p.dropna(subset=["Fecha", "mm"]).pivot_table(index="Fecha", columns="PLUV", values="mm", aggfunc="mean").reindex(dias)
L["REGION"] = L.median(axis=1)
h["ini"] = h.cosecha - pd.to_timedelta(h.Edad * 30.44, unit="D")
h["llu03"] = [rain(L[pl_] if pl_ in L.columns else L["REGION"], a) if a >= pd.Timestamp("2017-01-01") else np.nan for pl_, a in zip(h.pluv, h.ini)]
h["d32"] = [hot(tmax_reg, f) for f in h.cosecha]
h.to_pickle("cas_clima2.pkl")
A = h[(h.ten == "AGRICOLA") & h.MES.between(1, 8)]
print("\nCastilla tierras propias, ene-ago: lluvia 0-3 m (pluviómetro) y días >32 °C (referencia: estaciones de Riopaila)")
print(A.groupby("AÑO").apply(lambda g: pd.Series({"llu03": w(g, "llu03"), "d32": w(g, "d32"), "cobertura llu03": g.llu03.notna().mean()})).round(2).to_string())
