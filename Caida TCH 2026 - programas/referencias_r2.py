# -*- coding: utf-8 -*-
r"""Referencias para leer el R² suerte por suerte del modelo: ¿qué tan bien predicen el PPTO y el aforo el cambio de cada suerte?

Misma medida que la validación del modelo (validacion_modelo.py): cambio de cada cosecha 2026 frente a su historia 2020-25,
log(real / historia), y R² ponderado por área contra la predicción log(predicción / historia). Predicciones:
  · PPTO: «TCH PPTO» del Maestro de Suertes 2026 (ya en suertes.json).
  · Aforo: «TCH CALCULADO» del aforo de campo de la suerte más cercano antes del corte (hoja «Aforos 2024-2026» de la base de
    aforos; 9 meses de edad o más; hasta 150 días antes y 15 después del corte).
Además de R² (acierta el tamaño), la correlación al cuadrado (ordena bien las suertes aunque tenga un sesgo).

Uso: <tch-motor>\.venv-gee\Scripts\python.exe referencias_r2.py <Base de aforos completa 2026.xlsx> <carpeta web>
Lee <carpeta web>/data/suertes.json y escribe <carpeta web>/data/referencias.json (pestañas Prueba del modelo y gerencia).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
AFO, WEB = sys.argv[1], Path(sys.argv[2])
S = pd.DataFrame(json.load(open(WEB / "data" / "suertes.json", encoding="utf-8")))
S = S[S["hist"].notna() & S["real"].notna()].copy()
S["f"] = pd.to_datetime(S.f, errors="coerce").fillna(pd.to_datetime("2026-" + S.m.astype(str) + "-15"))


def r2(y, p, w):
    m = np.average(y, weights=w)
    return float(1 - np.sum(w * (y - p) ** 2) / np.sum(w * (y - m) ** 2))


def medir(nombre, d, pred):
    y, p = np.log(d["real"] / d["hist"]), np.log(pred / d["hist"])
    sesgo = float(np.average(np.exp(p) * d["hist"] - d["real"], weights=d.a))   # TCH por encima (+) o por debajo (−) de lo real
    out = {"metodo": nombre, "n": int(len(d)), "r2": round(r2(y, p, d.a), 2), "corr2": round(float(np.corrcoef(y, p)[0, 1] ** 2), 2),
           "sesgo_tch": round(sesgo, 1)}
    print(out)
    return out


ref = []
p = S[S.ppto.notna()]
ref.append(medir("PPTO del Maestro de Suertes 2026", p, p.ppto))
d = pd.read_excel(AFO, sheet_name="Aforos 2024-2026", header=None, skiprows=2)
a = pd.DataFrame({"fecha": pd.to_datetime(d.iloc[:, 2], errors="coerce"), "ste": d.iloc[:, 5].astype(str).str.strip(),
                  "edad": pd.to_numeric(d.iloc[:, 7], errors="coerce"), "tch": pd.to_numeric(d.iloc[:, 25], errors="coerce")})
a = a[a.tch.between(30, 300) & (a.edad.fillna(12) >= 9) & a.fecha.notna()].groupby(["ste", "fecha"]).tch.mean().reset_index()
A = {k: g.sort_values("fecha") for k, g in a.groupby("ste")}


def aforo(r):
    c = A.get(r.s)
    if c is None:
        return np.nan, np.nan
    c = c[(c.fecha <= r.f + pd.Timedelta(days=15)) & (c.fecha >= r.f - pd.Timedelta(days=150))]
    return (c.tch.iloc[-1], (r.f - c.fecha.iloc[-1]).days) if len(c) else (np.nan, np.nan)


S[["tch_af", "dias_af"]] = [aforo(r) for r in S.itertuples()]
q = S[S.tch_af.notna()]
ref.append({**medir("Aforo de campo antes del corte (TCH calculado)", q, q.tch_af), "dias": int(q.dias_af.median())})
json.dump({"referencias": ref}, open(WEB / "data" / "referencias.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("escrito:", WEB / "data" / "referencias.json")
