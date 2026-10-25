# -*- coding: utf-8 -*-
"""Riopaila: por qué cayó el TCH de lo cosechado ene-sep 2026 — UN solo modelo con todos los factores, para que sumen.

Base: rio_factores_sep.pkl (factores_sep.py: ZQM 2011-2025 + G&P ene-sep 2026, lluvia del arranque y calor de la EMA).
Mismo modelo de factores_sep.py (efectos fijos de suerte, año y mes; edad, soca, variedad, incendio, mecánica por año,
lluvia 0-3 meses, días >32 °C) y se le agregan, donde hay dato:
  · déficit de agua del final del ciclo después del riego (rio_riego.pkl, cosechas 2022-26), un solo coeficiente que luego
    se parte en «sequía» (evaporación − lluvia) y «riego aplicado» (lámina);
  · labores del ciclo (cosechas 2024-26): roturación (control oficial; si el corte no está, SimpleAgri − 10 días),
    primer herbicida (fecha real de las bases de aplicaciones en 2026; si no, SimpleAgri − 7 días), fertilización;
  · renovación no hecha (suertes del plan 2025 que siguieron como soca);
  · corte anterior mecánico (la cepa que dejó la máquina): mecánico después de manual o plantilla («primera vez») y dos
    mecánicos seguidos, frente a corte anterior manual;
  · nivel freático del ciclo (freatico_ciclos.pkl, freatico_suertes.py, cosechas desde 2021): metros por encima de 1,5 m
    (el límite de «bueno» del Registro de NF) del nivel promedio de la suerte entre el corte anterior y la cosecha;
  · suelo húmedo (suelo_humedo.pkl, suelo_humedo.py): lluvia en el pluviómetro de la suerte en los 5 días antes de la
    roturación y de la fertilización (cosechas 2024-26), y lluvia de la EMA en el mes del corte anterior (todas).
Cada aporte = coeficiente × (nivel 2026 − nivel normal), en los mismos meses. Normal: 2020-25 para clima, cosecha,
edad y variedad; 2022-25 para el agua y el nivel freático; 2024-25 para las labores; la renovación programada se hacía
(normal = 0). Lo que el modelo no explica queda como «sin explicar». Puente al presupuesto: «TCH PPTO» del Maestro de
Suertes 2026 (columna AG), por suerte.

Uso: python caida_integrada_rio.py <carpeta con los .pkl> <CONTROL DE ROTURACION.xlsm> <Maestro Suertes 2026.xlsx>
                                   <salida.xlsx>
"""
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
PK, CTRL, MAESTRO, SAL = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
EDADES = ["<9", "9-10", "10-11", "11-12", "12-13", "13-14", "14-15", ">15"]
MESES = range(1, 10)
K = ["ste", "anio", "Mes", "Corte"]
wm = lambda g, k: np.average(g[k], weights=g.Area) if len(g) else np.nan  # noqa: E731

c = pd.read_pickle(PK / "rio_factores_sep.pkl")
c = c[c.anio >= 2011].copy()

# ---------------------------------------------------------------- agua al final del ciclo
r = pd.read_pickle(PK / "rio_riego.pkl")[K + ["def_fin", "defsr_fin", "mm_fin"]]
c = c.merge(r, on=K, how="left")
c["def_na"] = (c.anio >= 2022) & c.def_fin.isna()
for v in ("def", "defsr", "mm"):
    c[f"{v}100"] = (c[f"{v}_fin"] / 100).fillna(0)
c["def_na"] = c.def_na.astype(int)

# ---------------------------------------------------------------- labores del ciclo (socas cosechadas 2024-26)
cl = pd.read_pickle(PK / "ciclos_labores.pkl")
cl = cl.dropna(subset=["h_anio", "h_mes"]).assign(anio=lambda x: x.h_anio.astype(int), Mes=lambda x: x.h_mes.astype(int))
# herbicida: SimpleAgri − 7 días en TODOS los años (las fechas reales de los contratistas solo existen para 2025-26 y
# mezclar fuentes cambia la cobertura entre años)
cl["d_mal"] = cl.d_maleza - pd.read_pickle(PK / "malezas_aplicaciones.pkl")["lag"]

F = list(openpyxl.load_workbook(CTRL, read_only=True, data_only=True)["B.D. ROTURACIÓN"].iter_rows(values_only=True))
h = next(i for i, x in enumerate(F) if x and str(x[0]).strip() == "SECTOR-SUERTE")
enc = [re.sub(r"\s+", " ", str(x)).strip() if x is not None else f"c{j}" for j, x in enumerate(F[h])]
CT = pd.DataFrame([x[: len(enc)] for x in F[h + 1:]], columns=enc).loc[:, lambda d: ~d.columns.duplicated()]
CT = CT[CT["SECTOR-SUERTE"].notna()].copy()
CT["ste"] = CT["SECTOR-SUERTE"].astype(str).str.strip()
CT["corte_f"] = pd.to_datetime(CT["FECHA DE CORTE"], errors="coerce")
txt = lambda s: s.astype(str).str.strip().str.upper().replace({"NONE": "", "NAN": "", "#N/A": ""})  # noqa: E731
CT["op1"], CT["op1p"], CT["est1"] = txt(CT["OPORTUNIDAD 1RA LABOR"]), txt(CT["OPORTUNIDAD PENDIENTES PRIMERA"]), txt(CT["ESTADO PRIMERA LABORE"])
CT["dias1"] = pd.to_numeric(CT["DIAS ENTRE PROGRAMACION Y ROTURACION"], errors="coerce")
CT["rot"] = np.select([CT.op1 == "TARDIO", CT.op1.isin(["IDEAL", "NORMAL"]), (CT.est1 == "REALIZADO") & (CT.dias1 <= 0),
                      CT.op1p == "TARDIO"], ["tardío", "a tiempo", "a tiempo", "tardío"], "")
CT = CT[(CT.rot != "") & CT.corte_f.notna()]
CG = {s: g for s, g in CT.groupby("ste")}


def rot_control(s, f):
    g = CG.get(s)
    if g is None or pd.isna(f):
        return ""
    dd = (g.corte_f - f).dt.days.abs()
    return g.rot.loc[dd.idxmin()] if dd.min() <= 45 else ""


cl["rot_ctrl"] = [rot_control(s, f) for s, f in zip(cl.ste, cl.corte_f)]
cl["rot"] = np.where(cl.rot_ctrl != "", cl.rot_ctrl,
                     np.where(cl.d_rot.isna(), "sin registro", np.where(cl.d_rot - 10 > 30, "tardío", "a tiempo")))
cl["rot_de"] = np.where(cl.rot_ctrl != "", "control", "SimpleAgri")
lab = cl[["ste", "anio", "Mes", "rot", "rot_de", "d_mal", "d_fert", "corte_f"]]
c = c.merge(lab, on=["ste", "anio", "Mes"], how="left")
c["lab_na"] = (c.rot.isna() | (c.Corte < 2)).astype(int)  # plantillas y ciclos sin dato de labores
# «sin registro» no es una labor: SimpleAgri registra cada año más (roturación sin registro 52 % en 2024, 10 % en 2026),
# así que va como control de calidad del dato (…_na) y el aporte de cada labor se mide solo con lo registrado
ok = c.lab_na == 0
c["rot_na"] = (ok & (c.rot == "sin registro")).astype(int)
c["rot_tard"] = (ok & (c.rot == "tardío")).astype(int)
c["mal_na"] = (ok & c.d_mal.isna()).astype(int)
c["mal_extra30"] = np.where(ok, (c.d_mal - 90).clip(lower=0).fillna(0) / 30, 0)
c["fert_na"] = (ok & c.d_fert.isna()).astype(int)
c["fert_120"] = (ok & (c.d_fert > 120)).astype(int)

nr = pd.read_pickle(PK / "no_renovadas_cosechas_2026.pkl")
nr = nr[nr.no_renov].assign(anio=2026)[["ste", "anio", "Mes"]].drop_duplicates()
c = c.merge(nr.assign(no_renov=1), on=["ste", "anio", "Mes"], how="left")
c["no_renov"] = c.no_renov.fillna(0).astype(int)

# ---------------------------------------------------------------- corte anterior (¿la cepa salió de un corte mecánico?)
c = c.sort_values(["ste", "cosecha"])
g = c.groupby("ste")
c["pc"], c["pc2"], c["m1"], c["m2"] = g.Corte.shift(), g.Corte.shift(2), g.mec.shift(), g.mec.shift(2)
c["prev_anio"], c["prev_mes"] = g.anio.shift(), g.Mes.shift()
cont = (c.Corte >= 2) & (c.Corte - c.pc == 1)  # el corte anterior de la base es el que dejó esta soca
cont2 = cont & (c.pc >= 2) & (c.pc - c.pc2 == 1)
c["ant"] = np.select([~cont, c.m1.eq(0), c.m1.eq(1) & (c.m2.eq(0) | (c.pc == 1)), c.m1.eq(1) & c.m2.eq(1) & cont2],
                     ["plantilla o sin dato", "manual", "mecánica tras manual", "mecánica seguida"], "mecánica, antes sin dato")
for k, v in {"pm_new": "mecánica tras manual", "pm_seg": "mecánica seguida", "pm_nd": "mecánica, antes sin dato",
             "p_na": "plantilla o sin dato"}.items():
    c[k] = (c.ant == v).astype(int)
c = c.sort_index()

# ---------------------------------------------------------------- nivel freático del ciclo
c = c.merge(pd.read_pickle(PK / "freatico_ciclos.pkl"), on=K, how="left").set_axis(c.index)
c["nf_exc15"] = (1.5 - c.nf_ciclo).clip(lower=0).fillna(0)
c["nf_na"] = c.nf_ciclo.isna().astype(int)

# ---------------------------------------------------------------- suelo húmedo en las labores y en el corte anterior
sh = pd.read_pickle(PK / "suelo_humedo.pkl")[K + ["mm_rot", "rot_hum", "mm_fert", "fert_hum", "mm_ca", "ca_hum"]]
c = c.merge(sh, on=K, how="left").set_axis(c.index)
okr = (c.lab_na == 0) & (c.rot_na == 0)
okf = (c.lab_na == 0) & (c.fert_na == 0)
c["roth_na"] = (okr & c.mm_rot.isna()).astype(int)
c["ferth_na"] = (okf & c.mm_fert.isna()).astype(int)
c["rot_mm10"] = np.where(okr & c.mm_rot.notna(), c.mm_rot.clip(upper=50) / 10, 0.0)
c["fert_mm10"] = np.where(okf & c.mm_fert.notna(), c.mm_fert.clip(upper=50) / 10, 0.0)
okc = c.ant.isin(["manual", "mecánica tras manual", "mecánica seguida", "mecánica, antes sin dato"])
c["cah_na"] = (okc & c.mm_ca.isna()).astype(int)
c["ca_mm100"] = np.where(okc & c.mm_ca.notna(), c.mm_ca.clip(upper=400) / 100, 0.0)
c.to_pickle(PK / "rio_integrado_dataset.pkl")  # la base completa del modelo, para la validación (validacion_modelo.py)

# ---------------------------------------------------------------- modelo
ED = "C(edad_b, Treatment('12-13'))"
MEC = " + ".join(f"mec_{y}" for y in range(2011, 2027))
NUEVAS = ["def100", "def_na", "rot_tard", "rot_na", "mal_extra30", "mal_na", "fert_120", "fert_na", "lab_na", "no_renov",
          "pm_new", "pm_seg", "pm_nd", "p_na", "nf_exc15", "nf_na", "ca_mm100", "cah_na"]
f = f"y ~ C(ste) + C(anio) + C(Mes) + {ED} + C(soca_b) + C(var) + inc + Corte + {MEC} + llu03_100 + d32 + " + " + ".join(NUEVAS)
est = c.dropna(subset=["llu03", "d32"])
mo = smf.wls(f, data=est, weights=est.Area)
mo = mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(est.loc[mo.data.row_labels, "ste"])[0]})
P = mo.params
print(f"modelo integrado: n={int(mo.nobs)}, R²={mo.rsquared:.2f}")
# probadas y sin efecto: lluvia en los 5 días antes de la roturación y de la fertilización (cosechas 2024-26)
mp = smf.wls(f + " + rot_mm10 + roth_na + fert_mm10 + ferth_na", data=est, weights=est.Area)
mp = mp.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(est.loc[mp.data.row_labels, "ste"])[0]})
PROBADAS = pd.DataFrame([{"variable": n, "efecto %": 100 * (np.exp(mp.params[k]) - 1), "p": mp.pvalues[k], "unidad": "por 10 mm"}
                         for n, k in (("Roturación en suelo húmedo", "rot_mm10"), ("Fertilización en suelo húmedo", "fert_mm10"))])
print("probadas sin efecto confiable:", PROBADAS.round(3).to_dict("records"))
for k in ["llu03_100", "d32", "def100", "rot_tard", "rot_na", "mal_extra30", "mal_na", "fert_120", "fert_na", "no_renov",
          "inc", "Corte", "mec_2024", "mec_2025", "mec_2026", "pm_new", "pm_seg", "nf_exc15", "ca_mm100"]:
    print(f"  {k:<12} {100 * (np.exp(P[k]) - 1):+6.2f} %  (p={mo.pvalues[k]:.3f})")

# ---------------------------------------------------------------- aportes ene-sep 2026
q = c[(c.anio == 2026) & c.Mes.isin(MESES)].copy()
ref = c[c.anio.between(2020, 2025) & c.Mes.isin(MESES)].copy()
ref_agua = c[c.anio.between(2022, 2025) & c.Mes.isin(MESES) & (c.def_na == 0)]
ref_lab = c[c.anio.between(2024, 2025) & c.Mes.isin(MESES) & (c.lab_na == 0)]
ref_nf = c[c.anio.between(2022, 2025) & c.Mes.isin(MESES) & (c.nf_na == 0)]
PM = ["pm_new", "pm_seg", "pm_nd"]
nf26 = q[q.nf_na == 0]


def humedo(k, ok, refd):
    """coeficiente × (nivel 2026 − nivel normal), los dos solo con dato, × parte de 2026 con dato."""
    a, b = q[ok(q)], refd[ok(refd)]
    NIVEL[k] = (wm(a, k), wm(b, k), a.Area.sum() / q.Area.sum())
    return P[k] * (NIVEL[k][0] - NIVEL[k][1]) * NIVEL[k][2]


ok_rot = lambda d: (d.lab_na == 0) & (d.rot_na == 0) & d.mm_rot.notna()  # noqa: E731
ok_fert = lambda d: (d.lab_na == 0) & (d.fert_na == 0) & d.mm_fert.notna()  # noqa: E731
ok_ca = lambda d: d.mm_ca.notna() & (d.p_na == 0)  # noqa: E731
T, HA = q["TC-Total"].sum(), q.Area.sum()
gap = wm(q.dropna(subset=["rel"]), "rel") - wm(ref.dropna(subset=["rel"]), "rel")
for k in EDADES:
    q["e_" + k], ref["e_" + k] = (q.edad_b == k).astype(float), (ref.edad_b == k).astype(float)
ed = {k: P.get(f"{ED}[T.{k}]", 0.0) for k in EDADES}
bv = {k.split("[T.")[1][:-1]: v for k, v in P.items() if k.startswith("C(var)")}
s26, sR = q.groupby("var").Area.sum() / HA, ref.groupby("var").Area.sum() / ref.Area.sum()
NIVEL = {}

# número de corte: efecto completo (por corte + etapa de la soca), frente a la propia historia 2020-25 de cada suerte,
# porque el corte avanza dentro de la suerte (comparado con el promedio de todas las suertes mezclaría suertes distintas)
bandas = {k.split("[T.")[1][:-1]: v for k, v in P.items() if k.startswith("C(soca_b)")}
fcorte = P["Corte"] * c.Corte + c.soca_b.map(bandas).fillna(0.0)
r20 = c.anio.between(2020, 2025)
propio = (fcorte * c.Area)[r20].groupby(c.ste[r20]).sum() / c.Area[r20].groupby(c.ste[r20]).sum()
q["corte_rel"] = (fcorte.loc[q.index] - q.ste.map(propio)).fillna(0.0)
ETAPAS = [("2º", 2), ("3º", 3), ("4º", 4), ("5º", 5), ("6º-7º", 6.5), ("8º o más", float(c.Corte[c.Corte >= 8].median()))]
efecto_corte = pd.DataFrame([{"corte": e, "efecto_pct": 100 * np.expm1(P["Corte"] * (n - 1) + bandas.get(
    next(k for k in bandas if float(k.strip("(]").split(",")[0]) < n <= float(k.strip("(]").split(",")[1])), 0.0))}
    for e, n in ETAPAS])
mezcla = pd.DataFrame({"2026": q.groupby(pd.cut(q.Corte, [0, 1, 2, 3, 4, 5, 7, 99])).Area.sum() / HA,
                       "normal": ref.groupby(pd.cut(ref.Corte, [0, 1, 2, 3, 4, 5, 7, 99])).Area.sum() / ref.Area.sum()})
mezcla.index = ["Plantilla", "2º", "3º", "4º", "5º", "6º-7º", "8º o más"]
pd.to_pickle({"efecto": efecto_corte, "mezcla": mezcla, "corte_2026": wm(q, "Corte"), "corte_normal": wm(ref, "Corte")},
             PK / "efecto_corte.pkl")
print("pérdida por corte frente a la plantilla:", efecto_corte.round(1).to_dict("records"))


def lab(k, na):
    """coeficiente × (nivel 2026 − nivel 2024-25), los dos solo con lo registrado, × parte de 2026 registrada."""
    reg26, regR = q[(q.lab_na == 0) & (q[na] == 0)], ref_lab[ref_lab[na] == 0]
    NIVEL[k] = (wm(reg26, k), wm(regR, k), reg26.Area.sum() / q.Area.sum())
    return P[k] * (NIVEL[k][0] - NIVEL[k][1]) * NIVEL[k][2]


A = {
    "Calor (días >32 °C)": P["d32"] * (wm(q, "d32") - wm(ref, "d32")),
    "Lluvia del arranque (0-3 meses)": P["llu03_100"] * (wm(q, "llu03_100") - wm(ref, "llu03_100")),
    "Sequía al final del ciclo": P["def100"] * (wm(q[q.def_na == 0], "defsr100") - wm(ref_agua, "defsr100")),
    "Riego aplicado": -P["def100"] * (wm(q[q.def_na == 0], "mm100") - wm(ref_agua, "mm100")),
    "Renovación no hecha": P["no_renov"] * wm(q, "no_renov"),
    "Roturación tardía": lab("rot_tard", "rot_na"),
    "Malezas (herbicida después de 90 días)": lab("mal_extra30", "mal_na"),
    "Fertilización después de 120 días": lab("fert_120", "fert_na"),
    "Cosecha mecánica": P["mec_2026"] * wm(q, "mec_2026") - sum(P[f"mec_{y}"] * wm(ref, f"mec_{y}") for y in range(2020, 2026)),
    "Corte anterior mecánico": sum(P[k] * (wm(q, k) - wm(ref, k)) for k in PM),
    "Corte anterior en suelo húmedo": humedo("ca_mm100", ok_ca, ref),
    "Nivel freático": P["nf_exc15"] * (wm(nf26, "nf_exc15") - wm(ref_nf, "nf_exc15")) * nf26.Area.sum() / q.Area.sum(),

    "Variedades": sum((s26.get(v, 0) - sR.get(v, 0)) * bv.get(v, 0.0) for v in set(s26.index) | set(sR.index)),
    "Edad de cosecha": sum(ed[k] * (wm(q, "e_" + k) - wm(ref, "e_" + k)) for k in EDADES),
    "Número de corte": wm(q, "corte_rel"),
    "Incendio": P["inc"] * (wm(q, "inc") - wm(ref, "inc")),
}
A["Sin explicar"] = gap - sum(A.values())

# lo mismo, suerte por suerte (para la matriz ponderada): cada aporte en log; los registros sin dato aportan 0
reg = lambda na: ((q.lab_na == 0) & (q[na] == 0)).astype(float)  # noqa: E731
agua = (q.def_na == 0).astype(float)
POR = pd.DataFrame({
    "Calor (días >32 °C)": P["d32"] * (q.d32 - wm(ref, "d32")).fillna(0),
    "Lluvia del arranque (0-3 meses)": P["llu03_100"] * (q.llu03_100 - wm(ref, "llu03_100")).fillna(0),
    "Sequía al final del ciclo": P["def100"] * (q.defsr100 - wm(ref_agua, "defsr100")) * agua,
    "Riego aplicado": -P["def100"] * (q.mm100 - wm(ref_agua, "mm100")) * agua,
    "Renovación no hecha": P["no_renov"] * q.no_renov,
    "Roturación tardía": P["rot_tard"] * (q.rot_tard - NIVEL["rot_tard"][1]) * reg("rot_na"),
    "Malezas (herbicida después de 90 días)": P["mal_extra30"] * (q.mal_extra30 - NIVEL["mal_extra30"][1]) * reg("mal_na"),
    "Fertilización después de 120 días": P["fert_120"] * (q.fert_120 - NIVEL["fert_120"][1]) * reg("fert_na"),
    "Cosecha mecánica": P["mec_2026"] * q.mec_2026 - sum(P[f"mec_{y}"] * wm(ref, f"mec_{y}") for y in range(2020, 2026)),
    "Corte anterior mecánico": sum(P[k] * (q[k] - wm(ref, k)) for k in PM),
    "Corte anterior en suelo húmedo": P["ca_mm100"] * (q.ca_mm100 - NIVEL["ca_mm100"][1]) * ok_ca(q),
    "Nivel freático": P["nf_exc15"] * (q.nf_exc15 - wm(ref_nf, "nf_exc15")) * (1 - q.nf_na),

    "Variedades": q["var"].map(bv).fillna(0.0) - sum(sR.get(v, 0) * bv.get(v, 0.0) for v in sR.index),
    "Edad de cosecha": sum(ed[k] * (q["e_" + k] - wm(ref, "e_" + k)) for k in EDADES),
    "Número de corte": q.corte_rel,
    "Incendio": P["inc"] * (q.inc - wm(ref, "inc")),
}, index=q.index)
POR["caída"] = q.rel - wm(ref.dropna(subset=["rel"]), "rel")
POR["Sin explicar"] = POR["caída"] - POR.drop(columns="caída").sum(axis=1)
pd.to_pickle(pd.concat([q[["ste", "Mes", "Corte", "Area", "TC-Total", "rel", "var", "mec", "d32", "rot", "no_renov", "ant",
                            "nf_ciclo", "mm_rot", "mm_fert", "mm_ca"]], POR], axis=1),
             PK / "caida_por_suerte.pkl")
GRUPO = {"Calor (días >32 °C)": "No controlable", "Lluvia del arranque (0-3 meses)": "No controlable",
         "Sequía al final del ciclo": "No controlable", "Riego aplicado": "Flujo de caja",
         "Renovación no hecha": "Flujo de caja", "Roturación tardía": "Flujo de caja",
         "Malezas (herbicida después de 90 días)": "Flujo de caja", "Fertilización después de 120 días": "Flujo de caja",
         "Cosecha mecánica": "Agronómico y operativo", "Corte anterior mecánico": "Agronómico y operativo",
         "Nivel freático": "No controlable", "Variedades": "Agronómico y operativo",
         "Corte anterior en suelo húmedo": "No controlable",
         "Edad de cosecha": "Agronómico y operativo", "Número de corte": "Agronómico y operativo",
         "Incendio": "Agronómico y operativo", "Sin explicar": "Sin explicar"}
t_tot = -gap * T
tab = pd.DataFrame({"grupo": GRUPO, "% TCH": {k: 100 * v for k, v in A.items()}, "t": {k: -v * T for k, v in A.items()}})
tab["t/ha"] = tab.t / HA
tab["% de la caída"] = 100 * tab.t / t_tot
tab = tab.sort_values("t", ascending=False)
print(f"\nene-sep 2026: {len(q)} cortes · {HA:,.0f} ha · {T:,.0f} t · TCH {T / HA:.1f} · frente a 2020-25: {100 * gap:+.1f} % "
      f"({t_tot:,.0f} t · {t_tot / HA:.1f} t/ha)")
print(tab.round(1).to_string())
g = tab.groupby("grupo")[["t", "t/ha", "% de la caída"]].sum().round(1)
print("\npor grupo:\n", g.to_string())
print("\nniveles 2026 vs normal:",
      {"días>32": (round(wm(q, "d32"), 1), round(wm(ref, "d32"), 1)),
       "déficit sin riego mm": (round(100 * wm(q[q.def_na == 0], "defsr100")), round(100 * wm(ref_agua, "defsr100"))),
       "lámina riego mm": (round(100 * wm(q[q.def_na == 0], "mm100")), round(100 * wm(ref_agua, "mm100"))),
       "% mecánica": (round(100 * wm(q, "mec")), round(100 * wm(ref, "mec"))),
       "% corte anterior mecánico": (round(100 * (wm(q, "pm_new") + wm(q, "pm_seg"))), round(100 * (wm(ref, "pm_new") + wm(ref, "pm_seg")))),
       "m por encima de 1,5 (freático)": (round(wm(nf26, "nf_exc15"), 3), round(wm(ref_nf, "nf_exc15"), 3)),
       "% no renovado": round(100 * wm(q, "no_renov"), 1)})
print("labores, solo lo registrado (2026 · 2024-25 · parte de 2026 registrada):", {k: tuple(round(x, 2) for x in v) for k, v in NIVEL.items()})

# ---------------------------------------------------------------- puente al presupuesto
# «TCH PPTO» del Maestro de Suertes 2026 (hoja MAESTRO, columna AG; encabezado en la fila 5), una cifra por suerte
mae = list(openpyxl.load_workbook(MAESTRO, read_only=True, data_only=True)["MAESTRO"].iter_rows(min_row=5, values_only=True))
mae = pd.DataFrame(mae[1:], columns=[str(x).strip() if x is not None else f"c{j}" for j, x in enumerate(mae[0])])
mae = mae[mae.SUERTE.notna()].assign(ste=lambda d: d.SUERTE.astype(str).str.strip(),
                                     ppto=lambda d: pd.to_numeric(d["TCH PPTO"], errors="coerce"))
q = q.merge(mae.dropna(subset=["ppto"]).drop_duplicates("ste")[["ste", "ppto"]], on="ste", how="left").set_axis(q.index)
qa = q[q.ppto.gt(20) & q.rel.notna()]  # solo las cosechas con PPTO e historia
gap_a = wm(qa, "rel") - wm(ref.dropna(subset=["rel"]), "rel")
Ta, HAa = qa["TC-Total"].sum(), qa.Area.sum()
T_ppto = (qa.ppto * qa.Area).sum()
esperado = Ta - gap_a * Ta
print(f"\npuente ene-sep ({len(qa)} cosechas con PPTO e historia, {HAa:,.0f} ha de {q.Area.sum():,.0f}): PPTO {T_ppto / HAa:.1f} t/ha · "
      f"historia de las mismas suertes {esperado / HAa:.1f} · real {Ta / HAa:.1f}")
print(f"  brecha contra PPTO {T_ppto - Ta:,.0f} t = presupuesto por encima de la historia {T_ppto - esperado:,.0f} t "
      f"+ caída {esperado - Ta:,.0f} t")

# ---------------------------------------------------------------- soporte
coef = pd.DataFrame({"efecto %": 100 * (np.exp(P) - 1), "p": mo.pvalues}).loc[
    ["llu03_100", "d32", "def100", "rot_tard", "rot_na", "mal_extra30", "mal_na", "fert_120", "fert_na", "no_renov", "inc",
     "Corte", "pm_new", "pm_seg", "pm_nd", "nf_exc15", "ca_mm100"] + [f"mec_{y}" for y in range(2020, 2027)]]
det = q[["ste", "Mes", "Corte", "var", "Area", "TC-Total", "rel", "d32", "llu03", "defsr_fin", "mm_fin", "def_fin", "mec", "ant", "inc",
         "rot", "rot_de", "d_mal", "d_fert", "no_renov", "nf_ciclo", "mm_rot", "mm_fert", "mm_ca", "ppto"]].rename(columns={"TC-Total": "toneladas"})
det["TCH"] = det.toneladas / det.Area
puente = pd.DataFrame({"concepto": ["Presupuesto (TCH PPTO del Maestro de Suertes 2026)", "Historia 2020-25 de las mismas suertes",
                                    "Real"], "periodo": "ene-sep 2026",
                       "t/ha": [T_ppto / HAa, esperado / HAa, Ta / HAa], "toneladas": [T_ppto, esperado, Ta]})
with pd.ExcelWriter(SAL, engine="openpyxl") as w:
    tab.reset_index(names="factor").to_excel(w, sheet_name="Factores", index=False)
    g.reset_index().to_excel(w, sheet_name="Grupos", index=False)
    puente.to_excel(w, sheet_name="Puente PPTO", index=False)
    coef.reset_index(names="variable").to_excel(w, sheet_name="Coeficientes", index=False)
    PROBADAS.to_excel(w, sheet_name="Probadas sin efecto", index=False)
    det.to_excel(w, sheet_name="Suertes ene-sep 2026", index=False)
pd.to_pickle({"tab": tab, "grupos": g, "puente": puente, "T": T, "HA": HA, "gap": gap, "n": len(q)}, PK / "caida_integrada_rio.pkl")
print("guardado:", SAL)
