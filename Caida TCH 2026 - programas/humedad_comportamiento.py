# -*- coding: utf-8 -*-
r"""¿Cada suerte cosechada en 2026 se comportó como su grupo de humedad (H0-H5) o como uno más húmedo o más seco?

Agua que sobró en el ciclo 2026 de cada suerte (del corte anterior a la cosecha):
  · exceso = Σ por mes máx(lluvia − ETP, 0), llevado a mm por año (× 365 / días del ciclo).
    Lluvia: el pluviómetro de la suerte (misma regla de suelo_humedo.py: el del control de roturación; si no, el más común de
    su sector; si no, el más cercano a menos de 3 km); los días sin dato (y septiembre de 2026) con la EMA de la suerte.
    ETP: la diaria de Cenicaña de la EMA de la suerte (etp_cenicana.py; días sin ETP estimados con la evaporación).
  · grupo «comportado» con la tabla del estudio de suelos: H0 < 50 mm/año (sin exceso), H1 < 200, H2 200-400, H3 400-600,
    H4 > 600; en permeabilidad lenta un escalón más (H2 < 200, H3 200-400, H4 > 400). H5 no se puede asignar (pide relieve y
    textura): un exceso de H4 o más queda como H4.
  · segunda señal, el nivel freático del ciclo (pozos interpolados a la suerte): nivel promedio y % de lecturas a menos de 1 m,
    frente a lo típico de su grupo designado y frente a su propio ciclo normal.
Normal de cada suerte: sus ciclos cosechados en 2021-2025 (pluviómetros desde 2020).
TCH: caída de 2026 frente a su historia según se comportó (más húmeda, igual, más seca que su grupo).

Uso: <tch-motor>\.venv-gee\Scripts\python.exe humedad_comportamiento.py <datos intermedios> <repo Precipitacion-riopaila>
       <CONTROL DE ROTURACION.xlsm> <suelos tch}.xlsx> <ETP_Cenicana_La_Paila_Bugalagrande.xlsx> <carpeta web> <salida.xlsx>
"""
import json
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import gee  # noqa: E402  (centroides de las suertes)

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
PK, REPO, CTRL, SUE, ETPX, WEB, OUT = (Path(a) for a in sys.argv[1:8])
GR = ["H0", "H1", "H2", "H3", "H4"]


def grupo_de(mm, perm):
    if pd.isna(mm):
        return None
    if mm < 50:
        return "H0"
    if perm == "lenta":
        return "H2" if mm < 200 else "H3" if mm < 400 else "H4"
    return "H1" if mm < 200 else "H2" if mm < 400 else "H3" if mm < 600 else "H4"


# ---------------------------------------------------------------- suelos (grupo designado y permeabilidad)
def arregla(v):
    if not isinstance(v, str):
        return v
    v = v.replace("Ã\x81", "Á")
    try:
        return v.encode("cp1252").decode("utf-8").strip()
    except (UnicodeEncodeError, UnicodeDecodeError):
        return v.strip()


su = pd.read_excel(SUE)
su.columns = [c.strip() for c in su.columns]
su = su.apply(lambda c: c.map(arregla)).rename(columns={"suerte": "ste", "Grupo humedad": "grupo", "Permeabilidad": "perm"})
su["ste"] = su.ste.astype(str).str.strip()
su = su.drop_duplicates("ste").set_index("ste")

# ---------------------------------------------------------------- lluvia diaria: pluviómetro de la suerte, con la EMA de respaldo
pl = pd.read_csv(REPO / "precipitacion.csv.csv", sep=";", encoding="latin-1", usecols=[1, 2, 3])
pl.columns = ["PLUV", "Fecha", "mm"]
pl["PLUV"] = pl.PLUV.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
pl["Fecha"] = pd.to_datetime(pl.Fecha, format="%d/%m/%Y", errors="coerce")
pl["mm"] = pd.to_numeric(pl.mm.astype(str).str.replace(",", "."), errors="coerce")
L = pl.dropna().groupby(["Fecha", "PLUV"]).mm.mean().unstack().sort_index()
E = pd.read_excel(ETPX, sheet_name="ETP diaria", parse_dates=["fecha"])
LL = E.pivot_table(index="fecha", columns="estacion", values="lluvia")
ET = E.pivot_table(index="fecha", columns="estacion", values="etp_usada")

F = list(openpyxl.load_workbook(CTRL, read_only=True, data_only=True)["B.D. ROTURACIÓN"].iter_rows(values_only=True))
h = next(i for i, r in enumerate(F) if r and str(r[0]).strip() == "SECTOR-SUERTE")
enc = [re.sub(r"\s+", " ", str(x)).strip() if x is not None else f"c{j}" for j, x in enumerate(F[h])]
C = pd.DataFrame([r[: len(enc)] for r in F[h + 1:]], columns=enc).loc[:, lambda d: ~d.columns.duplicated()]
C = C[C["SECTOR-SUERTE"].notna()].assign(ste=lambda t: t["SECTOR-SUERTE"].astype(str).str.strip())
C["pluv"] = C.PLUVIOMETRO.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
C.loc[~C.pluv.str.fullmatch(r"\d+"), "pluv"] = ""
pl_ste = C[C.pluv != ""].groupby("ste").pluv.agg(lambda s: s.mode().iloc[0])
pl_sec = C[C.pluv != ""].assign(sec=C.ste.str[:4]).groupby("sec").pluv.agg(lambda s: s.mode().iloc[0])
gp = json.load(open(r"C:\Users\Agr349\agrocontrol-campo\public\data\contexto_pluviometros.geojson", encoding="utf-8"))["features"]
GP = pd.DataFrame([(str(f["properties"]["Pluviometr"]), *f["geometry"]["coordinates"]) for f in gp], columns=["PLUV", "lon", "lat"])
GP = GP[GP.PLUV.isin(L.columns)].set_index("PLUV")
CEN = gee.centroides_suertes("riopaila")


def pluv_de(ste):
    if ste in pl_ste.index and pl_ste[ste] in L.columns:
        return pl_ste[ste]
    if ste[:4] in pl_sec.index and pl_sec[ste[:4]] in L.columns:
        return pl_sec[ste[:4]]
    c_ = CEN.get(ste)
    if c_ is None or GP.empty:
        return ""
    d = np.hypot((GP.lon - c_[0]) * 111320 * np.cos(np.radians(c_[1])), (GP.lat - c_[1]) * 110570)
    return d.idxmin() if d.min() <= 3000 else ""


def exceso(ste, est, ini, fin):
    """mm/año que sobraron (lluvia − ETP, por mes, solo lo positivo) del inicio a la cosecha, y % de días con pluviómetro."""
    dias = pd.date_range(ini.normalize(), fin.normalize())
    p = pluv_de(ste)
    lluv = L[p].reindex(dias) if p else pd.Series(np.nan, index=dias)
    cub = lluv.notna().mean()
    lluv = lluv.fillna(LL[est].reindex(dias))
    etp = ET[est].reindex(dias)
    if lluv.isna().mean() > 0.05 or etp.isna().mean() > 0.05:
        return np.nan, np.nan, cub, p
    m = pd.DataFrame({"p": lluv, "e": etp}).groupby(dias.to_period("M")).sum()
    exc = (m.p - m.e).clip(lower=0).sum()
    return exc * 365 / len(dias), m.p.sum() * 365 / len(dias), cub, p


# ---------------------------------------------------------------- cosechas: 2026 y ciclos normales 2021-25
ds = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
ds = ds[ds.ste.isin(su.index) & (ds.anio >= 2021)].copy()
est_csv = pd.read_csv(REPO / "estaciones_suertes.csv", sep=";", skiprows=1, encoding="latin-1").iloc[:, [1, 2]].dropna()
EST = est_csv.set_axis(["ste", "est"], axis=1).assign(ste=lambda t: t.ste.astype(str).str.strip(), est=lambda t: t.est.str.strip()).drop_duplicates("ste").set_index("ste").est
ds["E"] = ds.ste.map(EST).fillna(ds.est)
r = [exceso(s, e, i, f) for s, e, i, f in zip(ds.ste, ds.E, ds.ini, ds.cosecha)]
ds[["exc", "llu_anual", "cob_pluv", "pluv"]] = pd.DataFrame(r, index=ds.index)
ds["perm"] = ds.ste.map(su.perm)
ds["grupo"] = ds.ste.map(su.grupo)
ds["comp"] = [grupo_de(m, p) for m, p in zip(ds.exc, ds.perm)]
print(f"ciclos 2021-26 con exceso calculado: {ds.exc.notna().sum()} de {len(ds)} · días con pluviómetro {100 * ds.cob_pluv.mean():.0f} %")

q = ds[ds.anio == 2026].copy()
nor = ds[ds.anio.between(2021, 2025)]
wn = lambda g, c: np.average(g[c].dropna(), weights=g.loc[g[c].notna(), "Area"]) if g[c].notna().any() else np.nan  # noqa: E731
N = nor.groupby("ste").apply(lambda g: pd.Series({"exc_normal": wn(g, "exc"), "nf_normal": wn(g, "nf_ciclo"), "lt1_normal": wn(g, "nf_lt1")}))
q = q.join(N, on="ste")
q["comp_normal"] = [grupo_de(m, p) for m, p in zip(q.exc_normal, q.perm)]
num = lambda g: int(g[1]) if isinstance(g, str) else np.nan  # noqa: E731
q["salto"] = q.comp.map(num) - q.grupo.map(num)
q["como"] = np.select([q.salto > 0, q.salto < 0, q.salto == 0], ["más húmeda que su grupo", "más seca que su grupo", "como su grupo"], "sin dato")

# freático: frente a lo típico de su grupo designado (mediana 2021-25 de las suertes del grupo) y frente a su propio normal
tip = nor.groupby("grupo").nf_lt1.median()
q["nf_tipico_grupo"] = q.grupo.map(tip)
q["nf_como"] = np.select([q.nf_lt1 > q.nf_tipico_grupo + 0.15, q.nf_lt1 < q.nf_tipico_grupo - 0.15, q.nf_lt1.notna()],
                         ["más húmeda (agua más alta)", "más seca (agua más baja)", "como su grupo"], "sin dato")

# ---------------------------------------------------------------- TCH según se comportó
S = pd.DataFrame(json.load(open(WEB / "data" / "suertes.json", encoding="utf-8")))
S["n"] = S.groupby(["s", "m"]).cumcount()
q["n"] = q.groupby(["ste", "Mes"]).cumcount()
q = q.merge(S[["s", "m", "n", "real", "hist", "ppto"]].rename(columns={"s": "ste", "m": "Mes"}), on=["ste", "Mes", "n"], how="left")
q["caida"] = q["real"] - q["hist"]
q["caida_pct"] = 100 * q.caida / q["hist"]
w = lambda g, c: float(np.average(g[c], weights=g.Area)) if len(g) else np.nan  # noqa: E731


def resumen(g):
    g = g.dropna(subset=["caida"])
    return pd.Series({"cosechas": len(g), "ha": g.Area.sum(), "exceso 2026 (mm/año)": w(g, "exc"), "exceso normal (mm/año)": wn(g, "exc_normal"),
                      "% lecturas freático < 1 m": 100 * wn(g, "nf_lt1"), "historia": w(g, "hist"), "real 2026": w(g, "real"),
                      "caída TCH": w(g, "caida"), "caída %": w(g, "caida_pct"), "% cosecha mecanizada": 100 * w(g, "mec")})


por_grupo = q.groupby("grupo").apply(resumen).reindex(GR).dropna(how="all")
cruce = pd.crosstab(q.grupo, q.comp, values=q.Area, aggfunc="sum").reindex(index=GR, columns=GR).round(0)
cruce_n = pd.crosstab(q.grupo, q.comp, values=q.Area, aggfunc="sum", normalize="index").reindex(index=GR, columns=GR).mul(100).round(0)
cruce_normal = pd.crosstab(q.grupo, q.comp_normal, values=q.Area, aggfunc="sum", normalize="index").reindex(index=GR, columns=GR).mul(100).round(0)
por_como = q.groupby("como").apply(resumen)
por_nf = q.groupby("nf_como").apply(resumen)
print("\nexceso y TCH por grupo designado:\n", por_grupo.round(1).T.to_string())
print("\n% del área de cada grupo designado (filas) según el grupo en que se comportó en 2026 (columnas):\n", cruce_n.to_string())
print("\nlo mismo con sus ciclos normales 2021-25:\n", cruce_normal.to_string())
print("\nTCH según se comportó (balance):\n", por_como.round(1).to_string())
print("\nTCH según el freático:\n", por_nf.round(1).to_string())

# ¿restó más la que se comportó más húmeda? caída % frente a cuántos grupos se corrió, con la cosecha mecanizada como control
t = q.dropna(subset=["caida_pct", "salto"])
f1 = smf.wls("caida_pct ~ salto + mec", data=t, weights=t.Area).fit(cov_type="HC1")
t2 = q.dropna(subset=["caida_pct", "exc", "exc_normal"]).assign(dexc=lambda d: (d.exc - d.exc_normal) / 100)
f2 = smf.wls("caida_pct ~ dexc + mec", data=t2, weights=t2.Area).fit(cov_type="HC1")
t3 = q.dropna(subset=["caida_pct", "nf_lt1", "lt1_normal"]).assign(dlt1=lambda d: 10 * (d.nf_lt1 - d.lt1_normal))
f3 = smf.wls("caida_pct ~ dlt1 + mec", data=t3, weights=t3.Area).fit(cov_type="HC1")
pruebas = pd.DataFrame([
    {"prueba": "Por cada grupo que se corrió hacia más húmedo (balance 2026 frente al grupo designado)", "caída % de TCH": f1.params["salto"], "p": f1.pvalues["salto"], "cosechas": int(f1.nobs)},
    {"prueba": "Por cada 100 mm/año de exceso más que en sus ciclos normales 2021-25", "caída % de TCH": f2.params["dexc"], "p": f2.pvalues["dexc"], "cosechas": int(f2.nobs)},
    {"prueba": "Por cada 10 puntos más de lecturas del freático a menos de 1 m que en su normal", "caída % de TCH": f3.params["dlt1"], "p": f3.pvalues["dlt1"], "cosechas": int(f3.nobs)}]).round(3)
print("\n", pruebas.to_string(index=False))

# ---------------------------------------------------------------- datos del informe (pestaña «Suelos y humedad» y ficha de cada suerte)
r1 = lambda v, n=1: None if v is None or pd.isna(v) else round(float(v), n)  # noqa: E731
tabla = lambda c: [[g, *[r1(c.loc[g, k], 0) for k in GR]] for g in c.index]  # noqa: E731
fila = lambda et, x: [et, int(x.cosechas), r1(x.ha, 0), r1(x["exceso 2026 (mm/año)"], 0), r1(x["% lecturas freático < 1 m"], 0),  # noqa: E731
                      r1(x.historia), r1(x["real 2026"]), r1(x["caída TCH"]), r1(x["% cosecha mecanizada"], 0)]
HJ = {"grupos": [[g, r1(x["exceso 2026 (mm/año)"], 0), r1(x["exceso normal (mm/año)"], 0), r1(x["% lecturas freático < 1 m"], 0)]
                 for g, x in por_grupo.iterrows()],
      "cruce": tabla(cruce_n), "cruce_normal": tabla(cruce_normal),
      "balance": [fila(k, por_como.loc[k]) for k in ["más húmeda que su grupo", "como su grupo", "más seca que su grupo"] if k in por_como.index],
      "freatico": [fila(k, por_nf.loc[k]) for k in ["más húmeda (agua más alta)", "como su grupo", "más seca (agua más baja)"] if k in por_nf.index],
      "pruebas": [[x.prueba, r1(x["caída % de TCH"], 2), r1(x.p, 3), int(x.cosechas)] for _, x in pruebas.iterrows()],
      "cosechas": {f"{r.ste}|{int(r.Mes)}": [r.comp, r1(r.exc, 0), r1(r.exc_normal, 0), r.nf_como, r1(None if pd.isna(r.nf_lt1) else 100 * r.nf_lt1, 0)]
                   for r in q.itertuples() if isinstance(r.comp, str)}}
json.dump(HJ, open(WEB / "data" / "humedad.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("escrito:", WEB / "data" / "humedad.json")

det = q[["ste", "Mes", "Area", "grupo", "perm", "pluv", "cob_pluv", "llu_anual", "exc", "comp", "exc_normal", "comp_normal", "como",
         "nf_ciclo", "nf_lt1", "lt1_normal", "nf_tipico_grupo", "nf_como", "mec", "hist", "real", "caida", "caida_pct"]].rename(columns={
    "ste": "suerte", "Area": "ha", "grupo": "grupo designado", "perm": "permeabilidad", "pluv": "pluviómetro", "cob_pluv": "% días con pluviómetro",
    "llu_anual": "lluvia (mm/año)", "exc": "exceso 2026 (mm/año)", "comp": "se comportó como", "exc_normal": "exceso normal 2021-25",
    "comp_normal": "normalmente como", "nf_ciclo": "freático promedio (m)", "nf_lt1": "lecturas < 1 m", "lt1_normal": "lecturas < 1 m normal",
    "nf_tipico_grupo": "lecturas < 1 m típico del grupo", "nf_como": "según el freático", "mec": "cosecha mecanizada", "hist": "historia",
    "real": "real 2026", "caida": "caída TCH", "caida_pct": "caída %"}).round(2)
lee = pd.DataFrame({"Nota": [
    "Exceso de agua del ciclo 2026 (del corte anterior a la cosecha) = Σ por mes máx(lluvia − ETP, 0), en mm por año. Lluvia del pluviómetro "
    "de la suerte (la EMA donde falta); ETP diaria de Cenicaña de la EMA de la suerte.",
    "«Se comportó como»: el grupo que le toca a ese exceso con la tabla del estudio de suelos (H0 < 50, H1 < 200, H2 200-400, H3 400-600, H4 > 600 mm/año; "
    "un escalón más en permeabilidad lenta). H5 no se puede asignar con estos datos.",
    "«Normalmente como»: lo mismo con sus ciclos cosechados en 2021-25 (pluviómetros desde 2020).",
    "Freático: % de lecturas del ciclo a menos de 1 m (pozos interpolados a la suerte), frente a lo típico de su grupo (mediana 2021-25) y frente a su normal.",
    "Lo que no demuestra: el exceso por balance no ve el agua que llega por escorrentía, canales o drenaje malo; la tabla de grupos es anual y del "
    "estudio de suelos, no de un año. Las pruebas comparan suertes entre sí (con la cosecha mecanizada como control), no son el modelo completo."]})
with pd.ExcelWriter(OUT) as x:
    lee.to_excel(x, sheet_name="Léeme", index=False)
    por_grupo.round(1).reset_index().to_excel(x, sheet_name="Por grupo designado", index=False)
    cruce.reset_index().to_excel(x, sheet_name="Designado vs comportado (ha)", index=False)
    cruce_n.reset_index().to_excel(x, sheet_name="Designado vs comportado (%)", index=False)
    cruce_normal.reset_index().to_excel(x, sheet_name="Designado vs normal (%)", index=False)
    por_como.round(1).reset_index().to_excel(x, sheet_name="TCH según balance", index=False)
    por_nf.round(1).reset_index().to_excel(x, sheet_name="TCH según freático", index=False)
    pruebas.to_excel(x, sheet_name="Pruebas", index=False)
    det.to_excel(x, sheet_name="Suertes", index=False)
print("escrito:", OUT)
