# -*- coding: utf-8 -*-
"""Riopaila: frecuencia del riego, es decir, cuántos días pasan entre una pasada de riego y la siguiente en la misma suerte.

Un riego de una suerte puede tomar varios días (se riega por partes): los registros de la misma suerte separados por
7 días o menos se juntan en una «pasada». Intervalo = días entre el inicio de una pasada y el de la siguiente, dentro
del mismo ciclo (se descartan los intervalos que cruzan una cosecha de la suerte). Se prueba también con 5 y 10 días.

Uso: python riego_frecuencia.py <CONSOLIDADO DE RIEGOS.xlsx> <rio_factores_sep.pkl>
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
XLS, PKL = Path(sys.argv[1]), Path(sys.argv[2])

wb = openpyxl.load_workbook(XLS, read_only=True, data_only=True)
filas = list(wb["Consolidado de riegos "].iter_rows(values_only=True))
h = next(i for i, r in enumerate(filas) if r and str(r[0]).strip() == "Fecha")
enc = [str(c).strip() if c is not None else f"c{j}" for j, c in enumerate(filas[h])]
R = pd.DataFrame(filas[h + 1:], columns=enc)
R = R[R.Fecha.notna()]
R = R[~R.duplicated(subset=[c for c in enc if not c.startswith("c")])].copy()
R["f"] = pd.to_datetime(R.Fecha, errors="coerce").dt.normalize()
R["ste"] = R["SEC-SUERTE"].astype(str).str.strip()
R["a"] = pd.to_numeric(R["ÁREA REGADA"], errors="coerce")
R["an"] = pd.to_numeric(R["ÁREA NETA"], errors="coerce")
R["zona"] = R["ZONA"].astype(str).str.strip()
R["estado"] = R["ESTADO DE LA SUERTE"].astype(str).str.strip()
R = R[R.f.notna() & (R.a > 0) & (R.f >= "2021-01-01")]

c = pd.read_pickle(PKL)
cos = c.groupby("ste").cosecha.apply(lambda s: np.sort(s.values.astype("datetime64[D]")))


def pasadas(umbral):
    out = []
    for ste, g in R.sort_values("f").groupby("ste"):
        nueva = g.f.diff().dt.days.fillna(999) > umbral
        g = g.assign(p=nueva.cumsum())
        p = g.groupby("p").agg(ini=("f", "min"), fin=("f", "max"), area=("a", "sum"), an=("an", "max"),
                               zona=("zona", "first"), estado=("estado", "first"))
        p["ste"] = ste
        p["dias"] = p.ini.diff().dt.days
        p["prev"] = p.ini.shift(1)
        out.append(p)
    p = pd.concat(out, ignore_index=True)
    # descarta el intervalo si entre las dos pasadas hubo una cosecha de la suerte (±15 días, la fecha es por mes)
    cruza = []
    for ste, a, b in zip(p.ste, p.prev, p.ini):
        hs = cos.get(ste)
        cruza.append(bool(hs is not None and pd.notna(a) and
                          ((hs > np.datetime64(a.date()) - np.timedelta64(15, "D")) & (hs < np.datetime64(b.date()) + np.timedelta64(15, "D"))).any()))
    p["cruza_cosecha"] = cruza
    p["cobertura"] = p.area / p.an
    p["dur"] = (p.fin - p.ini).dt.days + 1
    return p


def resumen(x):
    d = x.dias
    return pd.Series({"intervalos": len(d), "mediana": d.median(), "promedio": d.mean(), "≤15 d %": 100 * (d <= 15).mean(),
                      "16-30 d %": 100 * d.between(16, 30).mean(), "31-60 d %": 100 * d.between(31, 60).mean(),
                      ">60 d %": 100 * (d > 60).mean()})


for umbral in (7, 5, 10):
    p = pasadas(umbral)
    ok = p[p.dias.notna() & ~p.cruza_cosecha]
    ok = ok.assign(anio=ok.ini.dt.year, mes=ok.ini.dt.month)
    print(f"\n==================== pasada = registros separados por ≤{umbral} días")
    print(f"pasadas: {len(p):,} · duración mediana de una pasada {p.dur.median():.0f} día(s) · cobertura mediana "
          f"{100 * p.cobertura.median():.0f} % de la suerte · intervalos válidos {len(ok):,} (se descartan {int(p.cruza_cosecha.sum())} que cruzan cosecha)")
    print("\nPor año (días entre pasadas en la misma suerte):")
    print(ok.groupby("anio").apply(resumen).round(1).to_string())
    if umbral != 7:
        continue
    print("\nPor mes, 2026 frente a 2023-25 (mediana de días | pasadas):")
    m26 = ok[ok.anio == 2026].groupby("mes").dias.agg(["median", "size"])
    mref = ok[ok.anio.between(2023, 2025)].groupby("mes").dias.agg(["median", "size"])
    print(pd.DataFrame({"2026 mediana": m26["median"], "2026 pasadas": m26["size"], "2023-25 mediana": mref["median"],
                        "2023-25 pasadas/año": mref["size"] / 3}).round(1).to_string())
    print("\nPor zona (mediana de días):", {f"{z} {a}": v for (z, a), v in ok[ok.anio >= 2023].groupby(["zona", "anio"]).dias.median().items()})
    print("\nPor estado de la suerte, 2026 frente a 2023-25 (mediana de días):")
    print(pd.DataFrame({"2026": ok[ok.anio == 2026].groupby("estado").dias.median(),
                        "2023-25": ok[ok.anio.between(2023, 2025)].groupby("estado").dias.median(),
                        "n 2026": ok[ok.anio == 2026].groupby("estado").size()}).round(0).to_string())
    # temporada seca de 2026 (jun-sep) frente a la misma temporada de años anteriores
    seca = ok[ok.mes.between(6, 9)]
    print("\nJunio a septiembre (temporada seca), por año:")
    print(seca.groupby("anio").apply(resumen).round(1).to_string())
    # suertes que en jun-sep 2026 pasaron más de 30 días sin volver a regar
    s26 = seca[seca.anio == 2026]
    print(f"\nJun-sep 2026: {s26.ste.nunique()} suertes con al menos dos pasadas; mediana {s26.dias.median():.0f} días; "
          f"{100 * (s26.dias > 30).mean():.0f} % de los intervalos pasó de 30 días")
    p.to_pickle("riego_pasadas.pkl")
