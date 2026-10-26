# -*- coding: utf-8 -*-
r"""Evapotranspiración (ETP) diaria de Cenicaña para las EMA La Paila (PAI) y Bugalagrande (BLG), asociada a cada suerte.

Entradas:
  · etp_diaria_PAI_BLG.csv: lo diario de la red meteorológica de Cenicaña (api.cenicana.org/meteorologia/daily, con la
    sesión del Visor del clima), dic-2009 a la fecha: etp, evaporación, lluvia, temperatura, radiación y humedad.
  · estaciones_suertes.csv del repo Precipitacion-riopaila: la estación de cada suerte.
  · rio_integrado_dataset.pkl (caida_integrada_rio.py): las cosechas 2011-2026 con su inicio de ciclo.
ETP publicada cuando existe y es coherente (0,4 a 1,1 veces la evaporación del día); si falta (abr-2015 a 2017, BLG hasta
mar-2018) o no es coherente (BLG 2011), ETP estimada = evaporación × la razón ETP/evaporación de esa estación y ese mes
del año en 2018-2026. Suertes que no están en estaciones_suertes.csv: la estación más cercana a su centroide; si no está
en el mapa (suertes renumeradas o divididas), la estación de la mayoría de las suertes de su hacienda.
Por cosecha: ETP y lluvia de todo el ciclo y del mes 8 a la cosecha (la misma ventana del balance de balance_riego.py).
Solo describe: no entra al modelo de la caída.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe etp_cenicana.py <etp_diaria_PAI_BLG.csv> <estaciones_suertes.csv>
       <datos intermedios> <salida.xlsx>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import gee  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
CSV, ESTS, PK, OUT = (Path(a) for a in sys.argv[1:5])
NOM = {"PAI": "La Paila", "BLG": "Bugalagrande"}
UBI = {"La Paila": (4.324614, -76.08448), "Bugalagrande": (4.2031, -76.18389)}   # coordenadas de la EMA en Cenicaña

# ---------------------------------------------------------------- ETP diaria: publicada o estimada
d = pd.read_csv(CSV, parse_dates=["fecha"])
d["est"] = d.est.map(NOM)
d["razon"] = d.etp / d.evaporacion
ok = d.etp.notna() & d.razon.between(0.4, 1.1)
d["mes"] = d.fecha.dt.month
R = d[ok & (d.fecha.dt.year >= 2018)].groupby(["est", "mes"]).razon.median().rename("razon_mes")
d = d.join(R, on=["est", "mes"])
d["etp_usada"] = np.where(ok, d.etp, d.evaporacion * d.razon_mes)
d["fuente"] = np.where(ok, "Cenicaña", np.where(d.etp_usada.notna(), "Estimada: evaporación × razón del mes", "Sin dato"))
print("razón ETP/evaporación 2018-26 por mes:\n", R.unstack(0).round(2).to_string())
print(d.groupby([d.fecha.dt.year, "est"]).fuente.apply(lambda s: round(100 * (s == "Cenicaña").mean())).unstack().to_string())

# ---------------------------------------------------------------- mensual por estación
m = d.assign(f=d.fecha.dt.to_period("M").dt.to_timestamp()).groupby(["est", "f"]).agg(
    etp=("etp_usada", "sum"), evaporacion=("evaporacion", "sum"), lluvia=("lluvia", "sum"),
    dias=("fecha", "size"), dias_estimados=("fuente", lambda s: int((s != "Cenicaña").sum()))).reset_index()
m["etp_menos_lluvia"] = m.etp - m.lluvia

# ---------------------------------------------------------------- estación de cada suerte
e = pd.read_csv(ESTS, sep=";", skiprows=1, encoding="latin-1").iloc[:, [0, 1, 2]].dropna()
e.columns = ["hacienda", "ste", "est"]
e = e.assign(ste=e.ste.astype(str).str.strip(), est=e.est.astype(str).str.strip(), origen="estaciones_suertes.csv")
c = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
c = c[c.anio >= 2011].copy()
cen = gee.centroides_suertes("riopaila")


SEC = e.groupby(e.ste.str[:4]).est.agg(lambda s: s.mode().iloc[0])   # estación de la mayoría de las suertes de la hacienda


def cercana(s):
    if s not in cen:
        if s[:4] in SEC.index:
            return pd.Series({"est": SEC[s[:4]], "km": np.nan, "origen": "no está en el mapa: la de su hacienda"})
        return pd.Series({"est": "La Paila", "km": np.nan, "origen": "sin hacienda conocida: La Paila (como el modelo)"})
    lon, lat = cen[s]
    km = {k: 111.32 * np.hypot(lat - a, (lon - o) * np.cos(np.radians(lat))) for k, (a, o) in UBI.items()}
    k = min(km, key=km.get)
    return pd.Series({"est": k, "km": round(km[k], 1), "origen": "más cercana al centroide"})


faltan = sorted(set(c.ste) - set(e.ste))
f = pd.DataFrame([cercana(s) for s in faltan], index=faltan).rename_axis("ste").reset_index()
f["hacienda"] = ""
S = pd.concat([e, f[["hacienda", "ste", "est", "origen"]]], ignore_index=True)
S["km_a_la_EMA"] = [(lambda s: round(111.32 * np.hypot(cen[s][1] - UBI[x][0], (cen[s][0] - UBI[x][1]) * np.cos(np.radians(cen[s][1]))), 1)
                     if s in cen else np.nan)(s) for s, x in zip(S.ste, S.est)]
S["cosechada_2026"] = S.ste.isin(set(c[c.anio == 2026].ste))
print(f"suertes: {len(e)} en estaciones_suertes.csv + {len(f)} sin tabla (cercanía o hacienda); 2026 sin tabla: "
      f"{len(set(c[c.anio == 2026].ste) - set(e.ste))}")
print(f.est.value_counts().to_string())

# ---------------------------------------------------------------- por cosecha
D = {k: g.set_index("fecha").sort_index() for k, g in d.groupby("est")}
EST = S.drop_duplicates("ste").set_index("ste").est
c["estE"] = c.ste.map(EST).fillna(c.est)


def ventana(x):
    g = D[x.estE]
    i8 = x.ini + pd.DateOffset(months=8)
    a, b = g.loc[x.ini:x.cosecha], g.loc[i8:x.cosecha]
    cubre = lambda w, i, j: len(w) >= 0.9 * ((j - i).days + 1)  # noqa: E731
    return pd.Series({
        "etp_ciclo": a.etp_usada.sum() if cubre(a, x.ini, x.cosecha) else np.nan,
        "lluvia_ciclo": a.lluvia.sum() if cubre(a, x.ini, x.cosecha) else np.nan,
        "etp_m8": b.etp_usada.sum() if cubre(b, i8, x.cosecha) else np.nan,
        "lluvia_m8": b.lluvia.sum() if cubre(b, i8, x.cosecha) else np.nan,
        "pct_estimada": round(100 * (a.fuente != "Cenicaña").mean()) if len(a) else np.nan})


c = pd.concat([c, c.apply(ventana, axis=1)], axis=1)
c["etp_menos_lluvia_m8"] = c.etp_m8 - c.lluvia_m8
P = c[["AÑO", "Mes", "ste", "estE", "Area", "Edad", "tch_calc", "ini", "cosecha", "etp_ciclo", "lluvia_ciclo", "etp_m8",
       "lluvia_m8", "etp_menos_lluvia_m8", "pct_estimada"]].rename(columns={"estE": "estacion", "tch_calc": "TCH"})
w = lambda g, k: np.average(g[k].dropna(), weights=g.loc[g[k].notna(), "Area"]) if g[k].notna().any() else np.nan  # noqa: E731
res = pd.DataFrame({y: {k: w(g, k) for k in ["etp_ciclo", "lluvia_ciclo", "etp_m8", "lluvia_m8", "etp_menos_lluvia_m8"]}
                    for y, g in P[P.Mes.between(1, 9)].groupby("AÑO")}).T.round(0)
print("cosechas ene-sep, promedio ponderado por área (mm):\n", res.to_string())

# ---------------------------------------------------------------- Excel
lee = pd.DataFrame({"Nota": [
    "ETP diaria de la red meteorológica de Cenicaña (Visor del clima), EMA La Paila (PAI) y Bugalagrande (BLG), dic-2009 a "
    f"{d.fecha.max().date()}.",
    "Fuente «Cenicaña»: ETP publicada. «Estimada»: el día no tiene ETP (abr-2015 a 2017; Bugalagrande hasta mar-2018) o no es "
    "coherente (más de 1,1 o menos de 0,4 veces la evaporación, sobre todo Bugalagrande 2011): evaporación × razón ETP/evaporación "
    "de esa estación y ese mes en 2018-2026.",
    "Desde 2018 la ETP es 0,73 a 0,78 veces la evaporación de tanque; el balance del informe usa 0,8.",
    "Estación por suerte: tabla estaciones_suertes.csv (repo Precipitacion-riopaila); las suertes que no están ahí toman la EMA "
    "más cercana a su centroide o, si no están en el mapa, la de la mayoría de las suertes de su hacienda.",
    "Por cosecha: ETP y lluvia de todo el ciclo y del mes 8 a la cosecha (misma ventana que la falta de agua del balance). "
    "Vacío si falta más del 10 % de los días.",
    "Solo describe el clima de cada cosecha: no entra al modelo de la caída."]})
with pd.ExcelWriter(OUT) as x:
    lee.to_excel(x, sheet_name="Léeme", index=False)
    d[["est", "fecha", "etp", "etp_usada", "fuente", "evaporacion", "lluvia", "tmax", "tmed", "radiacion", "hr_media"]].rename(
        columns={"est": "estacion", "etp": "etp_publicada"}).to_excel(x, sheet_name="ETP diaria", index=False)
    m.rename(columns={"est": "estacion", "f": "mes"}).to_excel(x, sheet_name="ETP mensual", index=False)
    S.rename(columns={"ste": "suerte", "est": "estacion"}).sort_values("suerte").to_excel(x, sheet_name="Estación por suerte", index=False)
    P.to_excel(x, sheet_name="Por cosecha", index=False)
    res.rename_axis("Año").to_excel(x, sheet_name="Resumen por año")
print("escrito:", OUT)
