# -*- coding: utf-8 -*-
"""Riopaila: control químico de malezas con la FECHA REAL de aplicación (bases de aplicaciones de los contratistas).

Fuentes: «Copia de LABOR APLICACIONES 31-12-2025.xlsx» (ene-2025 a ene-2026) y «BASE DE DATOS APLICACIONES 2026
14-08-2026.xlsx» (14-ago a 10-oct-2026). Labor 620 = control químico de malezas (preemergente, postemprana, intermedia,
80/20, hoja ancha); se excluyen arroz (690) y canales (640).
1. Desfase de SimpleAgri (fecha de confirmación de la planilla) frente a la fecha real.
2. Cosechas de 2026 cuyo corte fue en 2025 (su primer control quedó dentro de la base 2025): días del corte a la primera
   aplicación real; efecto en el TCH (cada suerte frente a su promedio 2020-25, con mes, edad y corte).
3. Pérdida 2026 con el plazo de 90 días; caña de 2027: base real donde la hay, SimpleAgri corregido donde no.

Uso: python malezas_aplicaciones.py <aplicaciones 2025.xlsx> <aplicaciones 2026.xlsx>   (en la carpeta caida_oct)
"""
import json
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import rutas  # noqa: E402

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
MAL30, PLAZO = -0.0146, 90


def leer(ruta):
    filas = [r for r in openpyxl.load_workbook(ruta, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True)
             if any(v is not None for v in r)]
    h = next(i for i, r in enumerate(filas) if r and str(r[0]).strip() == "ZONA")
    enc = [str(c).strip() if c is not None else f"c{j}" for j, c in enumerate(filas[h])]
    d = pd.DataFrame(filas[h + 1:], columns=enc)
    d["f"] = pd.to_datetime(d.FECHA, errors="coerce").dt.normalize()
    d["ste"] = d["SECTOR-SUERTE"].astype(str).str.strip()
    d["labor"] = pd.to_numeric(d.LABOR, errors="coerce")
    d["formula"] = d.FORMULA.astype(str).str.strip().str.upper()
    return d.loc[d.f.notna() & d.ste.str.match(r"^\d{4}-\d{3}$"), ["ste", "f", "labor", "formula"]]


A = pd.concat([leer(sys.argv[1]), leer(sys.argv[2])], ignore_index=True)
H = A[A.labor == 620].drop_duplicates(["ste", "f"]).copy()
print(f"aplicaciones de herbicida (620): {len(H)} · {H.f.min().date()} a {H.f.max().date()} · fórmulas {H.formula.value_counts().to_dict()}")
print("por mes:", H.f.dt.to_period("M").value_counts().sort_index().to_dict())

# 1. desfase de SimpleAgri
cy = pd.read_pickle("ciclos_labores.pkl")
sa = []
for f in sorted(Path("sa/planillas").glob("*.pkl")):
    if f.stem < "2024-12":
        continue
    for r in pickle.load(open(f, "rb")):
        if str(r.get("Actividad") or "").strip() == "620" and str(r.get("Estado Planilla", "")).startswith("CONFIRMADO"):
            sa.append((str(r.get("Terreno") or "").strip(), r.get("Fecha Confirmacion")))
S = pd.DataFrame(sa, columns=["ste", "f_sa"])
S["f_sa"] = pd.to_datetime(S.f_sa, errors="coerce").dt.normalize()
S = S.dropna().drop_duplicates()
m = pd.merge_asof(H.sort_values("f")[["ste", "f"]], S.sort_values("f_sa"), left_on="f", right_on="f_sa", by="ste",
                  direction="forward", tolerance=pd.Timedelta(days=60))
m["lag"] = (m.f_sa - m.f).dt.days
print(f"\nSimpleAgri frente a la fecha real: {m.lag.notna().sum()} de {len(m)} aplicaciones encontradas en SimpleAgri; "
      f"desfase mediana {m.lag.median():.0f} días (p25 {m.lag.quantile(.25):.0f}, p75 {m.lag.quantile(.75):.0f})")

# 2. ciclos cortados en 2025 y cosechados en 2026
cyc = cy[(cy.corte_f >= "2025-01-15") & (cy.h_anio == 2026)].copy()
HG = {s: g.sort_values("f") for s, g in H.groupby("ste")}


def primera(ste, d0, d1):
    g = HG.get(ste)
    if g is None:
        return np.nan, 0
    x = g[(g.f >= d0 - pd.Timedelta(days=10)) & (g.f < d1)]
    return ((x.f.iloc[0] - d0).days if len(x) else np.nan), len(x)


v = [primera(s, d0, d1 - pd.Timedelta(days=30)) for s, d0, d1 in zip(cyc.ste, cyc.corte_f, cyc.sig_f)]
cyc["d_real"], cyc["n_real"] = zip(*v)
print(f"\nsocas cosechadas en 2026 y cortadas en 2025: {len(cyc)} · {cyc.h_area.sum():,.0f} ha · con aplicación registrada "
      f"{cyc.d_real.notna().sum()} ({100 * cyc.h_area[cyc.d_real.notna()].sum() / cyc.h_area.sum():.0f} % del área)")
print("días al primer herbicida (real): mediana", cyc.d_real.median(), "· SimpleAgri:", cyc.d_maleza.median())
print("aplicaciones por ciclo:", cyc.n_real.value_counts().sort_index().to_dict())
g = cyc.assign(gr=np.where(cyc.d_real.isna(), "sin registro", pd.cut(cyc.d_real, [-99, 60, 90, 120, 9999], labels=["≤60", "61-90", "91-120", ">120"]).astype(str)))
print("área por grupo (real):", g.groupby("gr").h_area.sum().round(0).to_dict())
x = cyc.dropna(subset=["d_real", "h_rel"]).copy()
x["m30"] = x.d_real.clip(0, 240) / 30
x["Area"] = x.h_area
mo = smf.wls("h_rel ~ m30 + C(h_mes) + h_edad + h_corte", x, weights=x.Area).fit(cov_type="HC1")
print(f"efecto con fecha real (cosechas 2026): {100 * (np.exp(mo.params['m30']) - 1):+.2f} % por cada 30 días (p={mo.pvalues['m30']:.3f}, n={int(mo.nobs)})")
y = x.dropna(subset=["d_maleza"]).copy()
y["m30"] = y.d_maleza.clip(0, 240) / 30
mo2 = smf.wls("h_rel ~ m30 + C(h_mes) + h_edad + h_corte", y, weights=y.Area).fit(cov_type="HC1")
print(f"   mismos ciclos con fecha de SimpleAgri: {100 * (np.exp(mo2.params['m30']) - 1):+.2f} % por 30 días (p={mo2.pvalues['m30']:.3f})")

# 3. pérdida 2026 con el plazo de 90 días (fecha real; sin registro → SimpleAgri corregido; ninguno → sin control)
lag = float(m.lag.median())
cyc["d_uso"] = cyc.d_real.fillna(cyc.d_maleza - lag)
cyc["fuente"] = np.where(cyc.d_real.notna(), "aplicaciones", np.where(cyc.d_maleza.notna(), "SimpleAgri corregido", "sin registro"))
cyc["pct"] = np.where(cyc.d_uso.isna(), -0.067 + 0.0146, MAL30 * (cyc.d_uso - PLAZO).clip(lower=0) / 30)
cyc["t"] = -cyc.pct * cyc.h_tch * cyc.h_area
print(f"\n2026 (socas cortadas en 2025): atrasadas >90 días o sin control: {cyc.h_area[cyc.pct < 0].sum():,.0f} ha · {cyc.t.sum():,.0f} t · por fuente:",
      cyc.groupby("fuente").apply(lambda g: (len(g), round(g.h_area.sum()), round(g.t.sum()))).to_dict())
rest = cy[(cy.h_anio == 2026) & (cy.corte_f < "2025-01-15")].copy()
rest["d_uso"] = rest.d_maleza - lag
rest["pct"] = np.where(rest.d_uso.isna(), -0.067 + 0.0146, MAL30 * (rest.d_uso - PLAZO).clip(lower=0) / 30)
rest["t"] = -rest.pct * rest.h_tch * rest.h_area
print(f"   cortadas antes de 2025 (SimpleAgri corregido): {len(rest)} socas · {rest.h_area[rest.pct < 0].sum():,.0f} ha · {rest.t.sum():,.0f} t")

# caña de 2027
co = pd.read_pickle("cana2027_labores.pkl")
est = {e["sec_ste"]: e["tch_estimado"] for e in json.load(open(rutas.TABLERO_DATA / "estimados.json", encoding="utf-8")) if e["planta"] == "riopaila"}
hoy = pd.Timestamp.today().normalize()
v = [primera(s, d0, hoy + pd.Timedelta(days=1)) for s, d0 in zip(co.ste, co.corte_f)]
co["d_real"] = [a for a, _ in v]
co["d_uso"] = co.d_real.fillna(co.d_maleza - lag)
co["fuente"] = np.where(co.d_real.notna(), "aplicaciones", np.where(co.d_maleza.notna(), "SimpleAgri corregido", "pendiente"))
co["dias"] = np.where(co.d_uso.notna(), co.d_uso, co.dias_hoy)
co["pct"] = MAL30 * (co.dias - PLAZO).clip(lower=0) / 30
co["tch"] = co.ste.map(est).fillna(105.0)
co["t"] = -co.pct * co.tch * co.area
print(f"\n2027: {co.area[co.pct < 0].sum():,.0f} ha con atraso >90 días (hecho o pendiente) · {co.t.sum():,.0f} t · por fuente:",
      co.groupby("fuente").apply(lambda g: (len(g), round(g.area.sum()), round(g.t.sum()))).to_dict())
pd.to_pickle({"cyc": cyc, "rest": rest, "co": co, "lag": lag, "efecto_real": (mo.params["m30"], mo.pvalues["m30"], int(mo.nobs))}, "malezas_aplicaciones.pkl")
