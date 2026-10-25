# -*- coding: utf-8 -*-
r"""Nivel freático de cada suerte en cada lectura quincenal y por ciclo de cosecha.

Fuente: lecturas de los pozos de observación del Registro de NF de Ingeniería Agrícola (Luis Acosta), tal como están
publicadas en su portal Comité APS (js/datos.js → freatico: pozos [n, lat, lon, hacienda, sector, zona] y
lecturas {fecha: {pozo: m}}; 2 = seco, más de 2 m). Nivel de la suerte = IDW (potencia 2) de los pozos a menos de
1,5 km de su centroide (máximo 4); sin pozo a esa distancia queda sin dato.
Por ciclo (del corte anterior a la cosecha): nivel promedio, nivel de los 45 días antes del corte (el criterio del
Registro de NF), el más superficial y la parte de las lecturas a menos de 1 m.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe freatico_suertes.py <freatico.json> <carpeta con los .pkl>
Va después de factores_sep.py y antes de caida_integrada_rio.py.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import gee  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
FR, PK = Path(sys.argv[1]), Path(sys.argv[2])
fr = json.load(open(FR, encoding="utf-8"))
pz = pd.DataFrame(fr["pozos"], columns=["pozo", "lat", "lon", "hacienda", "sector", "zona"]).set_index("pozo")
L = pd.DataFrame({pd.Timestamp(f): {int(k): v for k, v in d.items()} for f, d in fr["lecturas"].items()}).T.sort_index()
L = L.apply(lambda s: pd.to_numeric(s.replace({"S": 2, "s": 2}), errors="coerce")).clip(upper=2)
print(f"{len(pz)} pozos · {len(L)} lecturas {L.index.min().date()} a {L.index.max().date()} · "
      f"{100 * L.notna().mean().mean():.0f} % de celdas con dato")

cen = gee.centroides_suertes("riopaila")
S = pd.DataFrame(cen, index=["lon", "lat"]).T
R = 6371000.0
la1, lo1 = np.radians(S.lat.values)[:, None], np.radians(S.lon.values)[:, None]
la2, lo2 = np.radians(pz.lat.values)[None, :], np.radians(pz.lon.values)[None, :]
D = 2 * R * np.arcsin(np.sqrt(np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2))
D = pd.DataFrame(D, index=S.index, columns=pz.index)

filas = []
for f, lect in L.iterrows():
    ok = lect.dropna()
    if ok.empty:
        continue
    d = D[ok.index]
    for s in d.index:
        dd = d.loc[s]
        cerca = dd[dd <= 1500].nsmallest(4)
        if cerca.empty:
            continue
        w = 1 / np.maximum(cerca.values, 50) ** 2
        filas.append((s, f, float(np.sum(w * ok[cerca.index].values) / w.sum()), int(cerca.index[0]), float(cerca.iloc[0])))
N = pd.DataFrame(filas, columns=["ste", "fecha", "nivel", "pozo_cercano", "dist_m"])
N.to_csv(PK / "freatico_suertes_lecturas.csv", index=False)
print(f"nivel por suerte: {N.ste.nunique()} suertes con pozo a menos de 1,5 km · {len(N)} filas")

K = ["ste", "anio", "Mes", "Corte"]
c = pd.read_pickle(PK / "rio_factores_sep.pkl")
G = {s: g.set_index("fecha").nivel for s, g in N.groupby("ste")}
out = []
for r in c[c.cosecha >= "2021-03-01"].itertuples():
    g = G.get(r.ste)
    if g is None:
        continue
    fin = r.cosecha + pd.Timedelta(days=15)  # el ZQM da el mes; el corte puede ser cualquier día de ese mes
    ciclo = g[(g.index >= r.ini) & (g.index <= fin)]
    if len(ciclo) < 3:
        continue
    a45 = g[(g.index > fin - pd.Timedelta(days=60)) & (g.index <= fin)]
    out.append({**{k: getattr(r, k) for k in K}, "nf_ciclo": ciclo.mean(), "nf_45": a45.mean() if len(a45) else np.nan, "nf_min": ciclo.min(),
                "nf_lt1": (ciclo < 1).mean(), "nf_n": len(ciclo)})
O = pd.DataFrame(out).drop_duplicates(K)
O.to_pickle(PK / "freatico_ciclos.pkl")  # lo usa caida_integrada_rio.py
print(f"ciclos con ≥3 lecturas: {len(O)} de {(c.cosecha >= '2021-03-01').sum()} cosechas desde mar-2021")
print(O.groupby("anio")[["nf_ciclo", "nf_45", "nf_min", "nf_lt1", "nf_n"]].agg(["mean", "count"]).round(2))
