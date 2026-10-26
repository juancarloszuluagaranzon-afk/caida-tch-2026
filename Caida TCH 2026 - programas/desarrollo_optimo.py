# -*- coding: utf-8 -*-
r"""Riopaila: desarrollo de la caña antes de la cosecha frente al óptimo de su variedad, histórico 2023-25 contra 2026.

Entradas:
  · «optimo de las variedades.xlsx»: tabla de óptimos por variedad (altura cm, diámetro cm, tallos/m).
  · «Base de aforos completa 2026.xlsx»: aforos por tablón 2022-2026 (hojas «AFOROS 2022-2023», «BASE 2022-2023» y
    «Aforos 2024-2026»): altura, diámetro y tallos por metro.
  · rio_integrado_dataset.pkl (caida_integrada_rio.py): las cosechas con su área, TCH y corte anterior.
A cada cosecha de enero a septiembre le toca el aforo de su suerte más cercano antes del corte (9 meses de edad o más, hasta
150 días antes y 15 después), promedio de sus tablones. Cada medida como % del óptimo de la variedad aforada; peso de caña =
tallos × altura × diámetro² frente al mismo producto del óptimo. Promedios ponderados por el área de la cosecha.
Comparación: histórico 2023-25 (2022 casi no tiene aforos cerca del corte) contra 2026, con todas las cosechas y con las mismas
suertes (las que tienen aforo en los dos periodos). Sin nombres de personas en la salida.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe desarrollo_optimo.py <optimo de las variedades.xlsx> <Base de aforos completa 2026.xlsx>
       <datos intermedios> <salida.xlsx> [<carpeta web>]
Con <carpeta web> escribe además data/desarrollo.json (pestaña «Desarrollo de la caña», ficha de cada suerte y pestaña
«Para la gerencia»).
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 220)
OPT, AFO, PK, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4]
WEB = Path(sys.argv[5]) if len(sys.argv) > 5 else None
r1 = lambda v, n=1: None if v is None or pd.isna(v) else round(float(v), n)  # noqa: E731
nv = lambda v: re.sub(r"^CC\s*", "CC ", str(v).strip().upper())  # noqa: E731  «CC01-1940» → «CC 01-1940»

# ---------------------------------------------------------------- óptimos y aforos
o = pd.read_excel(OPT, header=1).iloc[:, :4]
o.columns = ["var", "oalt", "odia", "opob"]
o = o.dropna(subset=["var"]).assign(var=lambda d: d["var"].map(nv))


def leer(hoja, cab, off):
    """Columnas de la base de aforos (las hojas difieren en una columna inicial)."""
    d = pd.read_excel(AFO, sheet_name=hoja, header=None, skiprows=cab)
    c = lambda i: d.iloc[:, i + off]  # noqa: E731
    x = pd.DataFrame({"fecha": c(2), "ste": c(5), "var": c(6), "edad": c(7), "alt": c(15), "dia": c(21), "pob": c(24)})
    for k in ["edad", "alt", "dia", "pob"]:
        x[k] = pd.to_numeric(x[k], errors="coerce")
    x["fecha"] = pd.to_datetime(x.fecha, errors="coerce")
    x["ste"], x["var"] = x.ste.astype(str).str.strip(), x["var"].map(nv)
    return x[x.pob.between(4, 25) & x.alt.between(80, 450) & x.dia.between(1.5, 4.5) & x.fecha.notna()]


af = pd.concat([leer("AFOROS 2022-2023", 4, 0), leer("BASE 2022-2023", 4, 1), leer("Aforos 2024-2026", 2, 0)]).drop_duplicates()
af = af[af.edad.fillna(12) >= 9]          # aforo de caña para cosechar, no de seguimiento de caña joven
g = af.groupby(["ste", "fecha"]).agg(alt=("alt", "mean"), dia=("dia", "mean"), pob=("pob", "mean"), var=("var", "first")).reset_index()
G = {k: v.sort_values("fecha") for k, v in g.groupby("ste")}
print(f"aforos: {len(af)} tablones, {len(g)} aforos de suerte")

# ---------------------------------------------------------------- cada cosecha con su aforo previo
ds = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
h = ds[ds.anio.between(2022, 2026) & ds.Mes.between(1, 9)][["ste", "anio", "Mes", "cosecha", "Area", "tch_calc", "ant"]].copy()


def aforo(r):
    c = G.get(r.ste)
    if c is None:
        return None
    c = c[(c.fecha <= r.cosecha + pd.Timedelta(days=15)) & (c.fecha >= r.cosecha - pd.Timedelta(days=150))]
    return c.iloc[-1] if len(c) else None


m = [aforo(r) for r in h.itertuples()]
for k in ["fecha", "alt", "dia", "pob", "var"]:
    h["af_" + k] = [x[k] if x is not None else None for x in m]
x = h[h.af_pob.notna()].merge(o, left_on="af_var", right_on="var", how="inner")
for k in ["pob", "alt", "dia"]:
    x["p_" + k] = 100 * x["af_" + k].astype(float) / x["o" + k]
x["p_peso"] = 100 * (x.af_pob * x.af_alt * x.af_dia ** 2).astype(float) / (x.opob * x.oalt * x.odia ** 2)
x = x[x.anio >= 2023].copy()
x["per"] = np.where(x.anio == 2026, "2026", "hist")
print("cosechas con aforo y óptimo por año:", x.groupby("anio").size().to_dict())

K = ["pob", "alt", "dia", "peso"]
w = lambda L, k: float(np.average(L[k], weights=L.Area)) if len(L) else None  # noqa: E731
res = lambda L: {"cosechas": int(len(L)), "ha": r1(L.Area.sum(), 0), **{k: r1(w(L, "p_" + k)) for k in K}, "tch": r1(w(L, "tch_calc"))}  # noqa: E731
both = sorted(set(x[x.per == "2026"].ste) & set(x[x.per == "hist"].ste))
y = x[x.ste.isin(both)]
top = x[x.per == "2026"].groupby("af_var").Area.sum().sort_values(ascending=False).index[:8]
out = {"todas": {p: res(x[x.per == p]) for p in ("hist", "2026")},
       "mismas": {"suertes": len(both), **{p: res(y[y.per == p]) for p in ("hist", "2026")}},
       "anios": [[int(a), res(L)] for a, L in x.groupby("anio")],
       "variedades": [[v, res(x[(x.af_var == v) & (x.per == "hist")]), res(x[(x.af_var == v) & (x.per == "2026")])] for v in top],
       "dias_aforo": r1((x.cosecha - pd.to_datetime(x.af_fecha)).dt.days.median(), 0),
       "optimo": [[r.var, r1(r.oalt), r1(r.odia, 2), r1(r.opob, 2)] for r in o.itertuples()],
       # 2026 por cosecha, para la ficha de cada suerte
       "filas": [{"s": r.ste, "m": int(r.Mes), "v": r.af_var, "alt": r1(r.af_alt), "oalt": r1(r.oalt), "pob": r1(r.af_pob, 2),
                  "opob": r1(r.opob, 2), "dia": r1(r.af_dia, 2), "odia": r1(r.odia, 2)} for r in x[x.per == "2026"].itertuples()]}
for p, et in (("hist", "Histórico 2023-25"), ("2026", "2026")):
    print(f"{et}: todas {out['todas'][p]} | mismas {out['mismas'][p]}")

# ---------------------------------------------------------------- salida
NOM = {"cosechas": "Cosechas", "ha": "Área (ha)", "pob": "Población % del óptimo", "alt": "Altura % del óptimo",
       "dia": "Diámetro % del óptimo", "peso": "Peso de caña % del óptimo", "tch": "TCH"}
tab = lambda d: pd.DataFrame(d).T.rename(columns=NOM).rename(index={"hist": "Histórico 2023-25"})  # noqa: E731
col = x[["ste", "anio", "Mes", "Area", "tch_calc", "af_fecha", "af_var", "af_pob", "opob", "p_pob", "af_alt", "oalt", "p_alt",
         "af_dia", "odia", "p_dia", "p_peso"]].rename(columns={"ste": "Suerte", "anio": "Año", "Mes": "Mes", "Area": "Área (ha)",
         "tch_calc": "TCH", "af_fecha": "Fecha aforo", "af_var": "Variedad aforo", "af_pob": "Tallos/m", "opob": "Tallos/m óptimo",
         "p_pob": "Población %", "af_alt": "Altura (cm)", "oalt": "Altura óptima", "p_alt": "Altura %", "af_dia": "Diámetro (cm)",
         "odia": "Diámetro óptimo", "p_dia": "Diámetro %", "p_peso": "Peso de caña %"})
with pd.ExcelWriter(OUT) as wr:
    tab(out["todas"]).to_excel(wr, sheet_name="Todas las cosechas")
    tab({k: v for k, v in out["mismas"].items() if k != "suertes"}).to_excel(wr, sheet_name="Mismas suertes")
    pd.DataFrame({a: v for a, v in out["anios"]}).T.rename(columns=NOM).to_excel(wr, sheet_name="Por año")
    pd.DataFrame([{"Variedad": v, **{f"{NOM[k]} {p}": d[k] for p, d in (("histórico", hh), ("2026", nn)) for k in ["cosechas", "pob", "alt", "dia", "peso"]}}
                  for v, hh, nn in out["variedades"]]).to_excel(wr, sheet_name="Por variedad", index=False)
    col.round(2).to_excel(wr, sheet_name="Cosechas con aforo", index=False)
    o.rename(columns={"var": "Variedad", "oalt": "Altura (cm)", "odia": "Diámetro (cm)", "opob": "Tallos/m"}).to_excel(wr, sheet_name="Óptimo por variedad", index=False)
print("escrito:", OUT)
if WEB:
    json.dump(out, open(WEB / "data" / "desarrollo.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("escrito:", WEB / "data" / "desarrollo.json")
