# -*- coding: utf-8 -*-
r"""¿El modelo parametrizado (repositorio modelo-caida-tch) da lo mismo que la versión 3 con los datos reales de Riopaila?

Compara, con la plantilla que arma a_plantilla_riopaila.py:
  1. cada variable, cosecha por cosecha, contra rio_integrado_dataset.pkl (la base del modelo de la versión 3);
  2. los coeficientes, contra el mismo modelo de caida_integrada_rio.py estimado con esa base;
  3. la caída y el aporte de cada causa, contra caida_integrada_rio.pkl;
  4. la prueba sin ver 2026, contra validacion_modelo.py.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe comparar_con_v3.py <plantilla_riopaila.xlsx> <datos intermedios> <salida.xlsx>
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, r"C:\Users\Agr349\modelo-caida-tch")
from modelo_tch import motor, salidas  # noqa: E402

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
XLS, PK, SAL = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

res = motor.correr(XLS, "riopaila")
print("revisión:", res.revision.resumen())
print(res.revision.hallazgos[["nivel", "hoja", "columna", "n_filas", "mensaje"]].to_string(index=False))
if not res.ok:
    sys.exit("no corrió")
print("notas:", res.notas)
salidas.libro(res, SAL.with_name(SAL.stem + "_resultado_nuevo.xlsx"))

# ---------------------------------------------------------------- 1. variables cosecha por cosecha
from modelo_tch import variables  # noqa: E402
nuevo, disp, _ = variables.construir(res.revision.tablas, res.cfg)
v3 = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
K = ["ste", "anio", "Mes", "Corte"]
v3["Corte"] = v3.Corte.clip(lower=1)
m = nuevo.merge(v3, on=K, how="outer", suffixes=("", "_v3"), indicator=True)
print(f"\n1) cosechas: nuevo {len(nuevo)} · v3 {len(v3)} · en las dos {(m._merge == 'both').sum()} · solo nuevo {(m._merge == 'left_only').sum()} · "
      f"solo v3 {(m._merge == 'right_only').sum()}")
b = m[m._merge == "both"]
VARS = {"y": 1e-9, "rel": 1e-9, "d32": 1e-6, "llu03": 0.5, "mec": 0, "inc": 0, "var": None, "edad_b": None, "soca_b": None,
        "pm_new": 0, "pm_seg": 0, "pm_nd": 0, "p_na": 0, "ca_mm100": 0.005, "cah_na": 0, "defsr_fin": 1, "mm_fin": 1, "def_fin": 1,
        "def_na": 0, "lab_na": 0, "rot_tard": 0, "rot_na": 0, "mal_extra30": 0.01, "mal_na": 0, "fert_120": 0, "fert_na": 0,
        "nf_ciclo": 0.001, "nf_na": 0, "nf_exc15": 0.001, "no_renov": 0}
filas = []
for k, tol in VARS.items():
    a, v = b[k], b[k + "_v3"]
    if tol is None:
        igual = a.astype(str) == v.astype(str)
        dif = np.nan
    else:
        a, v = pd.to_numeric(a, errors="coerce"), pd.to_numeric(v, errors="coerce")
        igual = (a.isna() & v.isna()) | ((a - v).abs() <= tol)
        dif = float((a - v).abs().where(~igual).mean()) if (~igual).any() else 0.0
    filas.append({"variable": k, "cosechas": len(b), "iguales": int(igual.sum()), "% iguales": 100 * igual.mean(),
                  "distintas": int((~igual).sum()), "diferencia media donde difieren": dif,
                  "solo nuevo con dato": int((b[k].notna() & b[k + "_v3"].isna()).sum()), "solo v3 con dato": int((b[k].isna() & b[k + "_v3"].notna()).sum())})
cmp_var = pd.DataFrame(filas)
print(cmp_var.round(3).to_string(index=False))

# ---------------------------------------------------------------- 2. coeficientes
ED = "C(edad_b, Treatment('12-13'))"
MEC = " + ".join(f"mec_{y}" for y in range(2011, 2027))
NUEVAS = ["def100", "def_na", "rot_tard", "rot_na", "mal_extra30", "mal_na", "fert_120", "fert_na", "lab_na", "no_renov",
          "pm_new", "pm_seg", "pm_nd", "p_na", "nf_exc15", "nf_na", "ca_mm100", "cah_na"]
f = f"y ~ C(ste) + C(anio) + C(Mes) + {ED} + C(soca_b) + C(var) + inc + Corte + {MEC} + llu03_100 + d32 + " + " + ".join(NUEVAS)
est = v3.dropna(subset=["llu03", "d32"])
mo = smf.wls(f, data=est, weights=est.Area)
mo = mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(est.loc[mo.data.row_labels, "ste"])[0]})
co = res.coeficientes.set_index("variable")
cmp_co = pd.DataFrame({"v3 %": 100 * np.expm1(mo.params), "v3 p": mo.pvalues}).join(co[["efecto_pct", "p"]].rename(columns={"efecto_pct": "nuevo %", "p": "nuevo p"}), how="inner")
cmp_co["diferencia (pts)"] = cmp_co["nuevo %"] - cmp_co["v3 %"]
print(f"\n2) coeficientes: v3 n={int(mo.nobs)} R²={mo.rsquared:.3f} · nuevo n={res.ajuste.nobs} R²={res.ajuste.r2:.3f}")
print(cmp_co.round(3).to_string())

# ---------------------------------------------------------------- 3. caída y causas
v3c = pd.read_pickle(PK / "caida_integrada_rio.pkl")
tab = v3c["tab"]
NOMBRE = {"Cosecha mecánica": "Cosecha mecanizada", "Corte anterior mecánico": "Corte anterior mecanizado",
          "Lluvia del arranque (0-3 meses)": "Lluvia del arranque", "Malezas (herbicida después de 90 días)": "Malezas (herbicida después del plazo)",
          "Fertilización después de 120 días": "Fertilización tardía"}
t3 = pd.DataFrame({"causa": [NOMBRE.get(k, k) for k in tab.index], "v3 TCH": -tab["t/ha"].values})
nu = res.aportes["causas"][["causa", "TCH"]].rename(columns={"TCH": "nuevo TCH"})
cmp_ca = t3.merge(nu, on="causa", how="outer")
cmp_ca["diferencia"] = cmp_ca["nuevo TCH"] - cmp_ca["v3 TCH"]
s = res.aportes["resumen"]
print(f"\n3) caída ene-sep 2026: v3 {v3c['n']} cosechas, {v3c['HA']:,.0f} ha, {100 * v3c['gap']:+.2f} % (log) · "
      f"nuevo {s['cosechas']} cosechas, {s['ha']:,.0f} ha, {100 * s['caida_log']:+.2f} %")
print(cmp_ca.round(2).to_string(index=False))

# ---------------------------------------------------------------- 4. prueba
p = res.prueba
print(f"\n4) prueba sin ver 2026: nuevo anticipa {p['v2']['explica_pct']:.1f} % (v3: 42 %) · años: correlación {p['v1_correlacion']:.2f} (v3: 0,91), "
      f"sentido {p['v1_sentido']} de {p['v1_anios']} (v3: 13 de 14)")
print(p["v1"].round(1).to_string(index=False))

with pd.ExcelWriter(SAL) as w:
    cmp_var.to_excel(w, sheet_name="Variables", index=False)
    cmp_co.reset_index(names="variable").to_excel(w, sheet_name="Coeficientes", index=False)
    cmp_ca.to_excel(w, sheet_name="Causas", index=False)
    p["v1"].to_excel(w, sheet_name="Prueba año por año", index=False)
    pd.DataFrame([p["v2"]]).to_excel(w, sheet_name="Prueba sin ver 2026", index=False)
    b[[c for c in b.columns if not c.startswith("_")]].head(0).to_excel(w, sheet_name="(columnas)", index=False)
print("escrito:", SAL)
