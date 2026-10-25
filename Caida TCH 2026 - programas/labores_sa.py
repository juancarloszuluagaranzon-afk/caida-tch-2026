# -*- coding: utf-8 -*-
"""Riopaila: oportunidad de fertilización, control de malezas y roturación (SimpleAgri) y su efecto en el TCH.

Planillas de SimpleAgri ene-2023 a oct-2026 (solo lo reciente: cosechas 2024-2026) (empresa 001, «Fecha Confirmacion»): roturación 540-544, fertilización 580-583/
591/593 (granulada y líquida al suelo; sin foliar), control químico de malezas 620 y manual 610.
Ciclo de una soca = de su corte (ZQM/G&P: día 15 del mes; app de Cosecha: fecha real de cierre en 2025-26) a la
cosecha siguiente. Se cuentan los días del corte a la primera labor de cada tipo dentro del ciclo.
Efecto: TCH de la cosecha frente al promedio 2020-25 de la misma suerte, con efectos de año y mes de cosecha, edad y
número de corte (solo socas: la plantilla se maneja distinto). Caña de 2027: socas cortadas desde nov-2025, estado hoy.

Uso: python labores_sa.py <carpeta con las planillas .pkl> <rio_factores_sep.pkl>
"""
import pickle
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
sys.path.insert(0, r"C:\Users\Agr349\tch-motor\scripts")
import presupuesto_cosecha as pc  # noqa: E402
from tchmotor import dataset_gee as dg, produccion as pr, turnos  # noqa: E402

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
CARP, PKL = Path(sys.argv[1]), Path(sys.argv[2])
HOY = pd.Timestamp(date.today())
GRUPOS = {"rot": {"540", "541", "542", "543", "544"}, "fert": {"580", "581", "582", "583", "591", "593"}, "maleza": {"620"},
          "maleza_man": {"610"}}

# ---------------------------------------------------------------- labores
filas = []
for f in sorted(x for x in CARP.glob("*.pkl") if x.stem >= "2023-01"):
    for r in pickle.load(open(f, "rb")):
        a = str(r.get("Actividad") or "").strip()
        g = next((k for k, v in GRUPOS.items() if a in v), None)
        if g and str(r.get("Estado Planilla", "")).startswith("CONFIRMADO"):
            filas.append((str(r.get("Terreno") or "").strip(), g, a, r.get("Fecha Confirmacion"), r.get("Cant. Realizada Planilla"), r.get("Area")))
L = pd.DataFrame(filas, columns=["ste", "g", "act", "f", "cant", "area"])
L["f"] = pd.to_datetime(L.f, errors="coerce").dt.normalize()
L = L[L.f.notna() & L.ste.str.match(r"^\d{4}-\d{3}$")].drop_duplicates(["ste", "g", "f"])
print("labores por año y tipo (registros suerte-día):")
print(L.groupby([L.f.dt.year, "g"]).size().unstack().fillna(0).astype(int).to_string())
LG = {k: g.sort_values("f") for k, g in L.groupby(["ste", "g"])}

# ---------------------------------------------------------------- cortes con fecha
c = pd.read_pickle(PKL)
cos = c[["ste", "cosecha", "anio", "Mes", "Edad", "Corte", "tch_calc", "Area", "rel", "y"]].copy()
mp, _ = pr.cargar_maestro()
rec, _ = pr.cosechas_recientes(pr.leer_cosechas_recientes(), mp, dg.cortes_zqm(dg.leer_zqm()))
rec = rec[(rec.planta == "riopaila") & (rec.anio == 2026) & (rec.mes == 10)]
cos = pd.concat([cos, pd.DataFrame({"ste": rec.sec_ste, "cosecha": pd.to_datetime(rec.harvest), "anio": rec.anio, "Mes": rec.mes,
                                    "Edad": rec.edad, "Corte": rec.corte, "tch_calc": rec.tch, "Area": rec.ha})], ignore_index=True)
base = c[c.anio.between(2020, 2025)].groupby("ste").y.mean()
cos["rel"] = cos.rel.fillna(np.log(cos.tch_calc) - cos.ste.map(base))
# fecha real del corte (app de Cosecha) para 2025-26
try:
    app = pd.DataFrame(turnos.cortes_terminados("2025-01-01", HOY.strftime("%Y-%m-%d")))
    app["f"] = pd.to_datetime(app.fecha_fin, errors="coerce")
    app = app.dropna(subset=["f"])
    print(f"\napp de Cosecha: {len(app)} cortes con fecha de cierre 2025-26")
except Exception as e:  # noqa: BLE001
    app = pd.DataFrame(columns=["suerte", "f"])
    print("app de Cosecha no disponible:", type(e).__name__)
real = {(s, f.year, f.month): f for s, f in zip(app.get("suerte", []), app.f)}
cos["corte_f"] = [real.get((s, d.year, d.month), d) for s, d in zip(cos.ste, cos.cosecha)]
cos["exacta"] = [(s, d.year, d.month) in real for s, d in zip(cos.ste, cos.cosecha)]
cos = cos.sort_values(["ste", "corte_f"]).reset_index(drop=True)
cos["sig_f"] = cos.groupby("ste").corte_f.shift(-1)
cos["sig_i"] = cos.groupby("ste").cosecha.transform(lambda s: s.index.to_series().shift(-1))


def primero(ste, g, d0, d1):
    x = LG.get((ste, g))
    if x is None:
        return np.nan, 0
    x = x[(x.f >= d0 - pd.Timedelta(days=10)) & (x.f < d1)]
    return ((x.f.iloc[0] - d0).days if len(x) else np.nan), len(x)


# ciclo = de un corte (soca) a la cosecha siguiente
cy = cos[cos.sig_f.notna()].copy()
for g in GRUPOS:
    v = [primero(s, g, d0, d1 - pd.Timedelta(days=30)) for s, d0, d1 in zip(cy.ste, cy.corte_f, cy.sig_f)]
    cy[f"d_{g}"], cy[f"n_{g}"] = zip(*v)
nx = cos.loc[cy.sig_i.astype(int).values].reset_index(drop=True)
cy = cy.reset_index(drop=True)
cy[["h_anio", "h_mes", "h_edad", "h_corte", "h_tch", "h_area", "h_rel"]] = nx[["anio", "Mes", "Edad", "Corte", "tch_calc", "Area", "rel"]].values
cy = cy[(cy.h_corte >= 2) & (cy.corte_f >= "2023-03-01") & cy.h_rel.notna()].copy()
for k in ["h_anio", "h_mes", "h_edad", "h_corte", "h_tch", "h_area", "h_rel"]:
    cy[k] = pd.to_numeric(cy[k], errors="coerce")
print(f"\nciclos de soca con su cosecha (cortes desde mar-2018): {len(cy)} · cosechas {int(cy.h_anio.min())}-{int(cy.h_anio.max())}")
print("días del corte a la primera labor (mediana por año de cosecha) y % de ciclos sin la labor:")
print(cy.groupby("h_anio").apply(lambda g: pd.Series({k: g[f"d_{k}"].median() for k in ("rot", "fert", "maleza")} |
                                                      {f"sin {k} %": 100 * g[f"d_{k}"].isna().mean() for k in ("rot", "fert", "maleza")})).round(0).to_string())


def cat(d, cortes, etiquetas):
    return np.where(pd.isna(d), "NINGUNA", pd.cut(pd.Series(d), cortes, labels=etiquetas).astype(str))


cy["fert_c"] = cat(cy.d_fert, [-99, 60, 120, 9999], ["≤60", "61-120", ">120"])
cy["mal_c"] = cat(cy.d_maleza, [-99, 45, 90, 9999], ["≤45", "46-90", ">90"])
cy["rot_c"] = cat(cy.d_rot, [-99, 15, 30, 9999], ["IDEAL", "NORMAL", "TARDÍO"])
cy["Area"] = cy.h_area
f = ("h_rel ~ C(fert_c, Treatment('≤60')) + C(mal_c, Treatment('≤45')) + C(rot_c, Treatment('IDEAL')) + C(h_anio) + C(h_mes) "
     "+ h_edad + h_corte")
mod = smf.wls(f, cy, weights=cy.Area)
mo = mod.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(cy.loc[mod.data.row_labels, "ste"])[0]})
print(f"\nmodelo (n={int(mo.nobs)}):")
ef = {}
for k, v in mo.params.items():
    if "[T." in k and any(s in k for s in ("fert_c", "mal_c", "rot_c")):
        nom = k.split("(")[1].split(",")[0] + ":" + k.split("[T.")[1][:-1]
        ef[nom] = (v, mo.pvalues[k])
        n = int((cy[k.split("(")[1].split(",")[0]] == k.split("[T.")[1][:-1]).sum())
        print(f"   {nom:22s} {100 * (np.exp(v) - 1):+6.1f} %  (p={mo.pvalues[k]:.3f}, n={n})")
print("   reparto de ciclos:", {k: cy[k].value_counts().to_dict() for k in ("fert_c", "mal_c", "rot_c")})
cy.to_pickle("ciclos_labores.pkl")

# ---------------------------------------------------------------- caña de 2027: socas cortadas desde nov-2025, estado hoy
ma, _ = pc.leer_maestro("riopaila")
mm = pd.DataFrame([dict(ste=s, area=v["area"] or 0, ncorte=v["ncorte"], var=v["var"]) for s, v in ma.items()])
ult = cos.groupby("ste").corte_f.max()
co = mm[(mm.ncorte >= 2) & (mm["var"].str.upper() != "RENOVACION")].copy()
co["corte_f"] = co.ste.map(ult)
co = co[(co.corte_f >= "2025-11-01")]
for g in ("rot", "fert", "maleza"):
    v = [primero(s, g, d0, HOY + pd.Timedelta(days=1)) for s, d0 in zip(co.ste, co.corte_f)]
    co[f"d_{g}"], co[f"n_{g}"] = zip(*v)
co["dias_hoy"] = (HOY - co.corte_f).dt.days
# estado: hecha (con sus días) o pendiente con los días que ya pasaron
co["fert_c"] = np.where(co.d_fert.notna(), cat(co.d_fert, [-99, 60, 120, 9999], ["≤60", "61-120", ">120"]),
                        np.where(co.dias_hoy > 120, ">120", np.where(co.dias_hoy > 60, "61-120", "en plazo")))
co["mal_c"] = np.where(co.d_maleza.notna(), cat(co.d_maleza, [-99, 45, 90, 9999], ["≤45", "46-90", ">90"]),
                       np.where(co.dias_hoy > 90, ">90", np.where(co.dias_hoy > 45, "46-90", "en plazo")))
co["rot_c"] = np.where(co.d_rot.notna(), cat(co.d_rot, [-99, 15, 30, 9999], ["IDEAL", "NORMAL", "TARDÍO"]),
                       np.where(co.dias_hoy > 30, "TARDÍO", "en plazo"))
print(f"\ncaña de 2027 (socas cortadas desde nov-2025): {len(co)} suertes · {co.area.sum():,.0f} ha")
for k in ("rot_c", "fert_c", "mal_c"):
    print(f"   {k}:", co.groupby(k).area.sum().round(0).to_dict())
co.to_pickle("cana2027_labores.pkl")
pd.to_pickle(ef, "efectos_labores.pkl")
