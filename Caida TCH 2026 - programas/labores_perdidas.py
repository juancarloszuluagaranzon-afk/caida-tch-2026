# -*- coding: utf-8 -*-
"""Riopaila: toneladas perdidas en 2026 y 2027 por roturación tardía y control de malezas tardío.

Efectos (medidos con las cosechas 2024-2026):
  · Roturación: control oficial de Riopaila (roturacion.py): 1.ª labor TARDÍA (>30 días) −6,3 % frente a IDEAL,
    controlando la condición del suelo (sin ese control −10,9 %). NORMAL no resta.
  · Malezas: SimpleAgri (labores_sa.py): −1,46 % de TCH por cada 30 días de atraso del primer control químico más allá
    de 60 días; sin ningún control químico en el ciclo −6,7 % (frente a ≤60 días).
2026 = socas cosechadas en 2026 (ene-oct; las de nov-dic con su estado de labores). 2027 = socas cortadas desde
nov-2025 (se cosechan en 2027), estado a hoy: lo pendiente cuenta con los días que ya pasaron (mínimo).
Roturación de la caña de 2027: control oficial (cortes hasta ene-2026) y, para cortes posteriores, SimpleAgri con la
fecha corrida por el desfase medido entre la confirmación de la planilla y la fecha real de la labor.
TCH para pasar % a toneladas: el real (2026) o el del motor (2027; si no hay, 105).

Uso: python labores_perdidas.py   (en la carpeta con roturacion.pkl, ciclos_labores.pkl, cana2027_labores.pkl)
"""
import json
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import rutas  # noqa: E402

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROT_TARDIA = -0.063
MAL_30, MAL_NINGUNA, MAL_PLAZO = -0.0146, -0.067, 60

rt = pd.read_pickle("roturacion.pkl")
d, j = rt["d"], rt["j"]
cy = pd.read_pickle("ciclos_labores.pkl")
co = pd.read_pickle("cana2027_labores.pkl")
est = {e["sec_ste"]: e["tch_estimado"] for e in json.load(open(rutas.TABLERO_DATA / "estimados.json", encoding="utf-8")) if e["planta"] == "riopaila"}

# desfase SimpleAgri (confirmación de la planilla) frente a la fecha real de la roturación del control
d["f_rot"] = pd.to_datetime(d["FECHA DE ROTURACION PRIMERA"], errors="coerce")
cy["mes_c"] = cy.corte_f.dt.to_period("M")
d["mes_c"] = d.corte_f.dt.to_period("M")
m = cy.dropna(subset=["d_rot"]).merge(d.dropna(subset=["f_rot"])[["ste", "mes_c", "f_rot"]], on=["ste", "mes_c"])
m["f_sa"] = m.corte_f + pd.to_timedelta(m.d_rot, unit="D")
lag = float((m.f_sa - m.f_rot).dt.days.median())
print(f"desfase SimpleAgri − fecha real de la roturación: mediana {lag:.0f} días (n={len(m)})")


def perd(pct, tch, ha):
    return -pct * tch * ha  # toneladas (+ = pérdida)


# ---------------------------------------------------------------- 2026
q = j[j.c_anio == 2026].copy()
q["t"] = np.where(q.rot1.isin(["TARDIO", "PENDIENTE (TARDÍO)"]), perd(ROT_TARDIA, q.c_tch_calc, q.Area), 0.0)
r26_ha, r26_t = q.Area[q.t > 0].sum(), q.t.sum()
# las de nov-dic 2026 (cortes ago-oct 2025 del control aún sin cosechar)
pend = rt["pend"]
p26 = pend[pend.corte_f < "2025-11-01"]
r26_ha += p26.area[p26.rot1.isin(["TARDIO", "PENDIENTE (TARDÍO)"])].sum()
r26_t += sum(perd(ROT_TARDIA, est.get(s, 105.0), a) for s, a, o in zip(p26.ste, p26.area, p26.rot1) if o in ("TARDIO", "PENDIENTE (TARDÍO)"))
print(f"\n2026 roturación tardía: {r26_ha:,.0f} ha · {r26_t:,.0f} t")


def mal_pct(dias, hecho):
    if not hecho:
        return MAL_NINGUNA
    return MAL_30 * max(0.0, dias - MAL_PLAZO) / 30


c26 = cy[cy.h_anio == 2026].copy()
c26["pct"] = [mal_pct(x, pd.notna(x)) for x in c26.d_maleza]
c26["t"] = perd(c26.pct, c26.h_tch, c26.h_area)
print(f"2026 malezas: {c26.h_area[c26.pct < 0].sum():,.0f} ha con control tardío o sin control · {c26.t.sum():,.0f} t "
      f"(de {c26.h_area.sum():,.0f} ha de socas cosechadas ene-oct; atraso mediano {c26.d_maleza.median():.0f} días)")

# ---------------------------------------------------------------- 2027
co["tch"] = co.ste.map(est).fillna(105.0)
# roturación: control oficial para cortes nov-2025 a ene-2026; SimpleAgri corregido para los posteriores
p27 = pend[pend.corte_f >= "2025-11-01"]
oficial = set(p27.ste)
co["rot_ok"] = np.where(co.ste.isin(oficial), co.ste.map(dict(zip(p27.ste, p27.rot1))), None)
d_corr = co.d_rot - lag
co["rot_sa"] = np.where(co.d_rot.notna(), np.where(d_corr > 30, "TARDIO", np.where(d_corr > 15, "NORMAL", "IDEAL")),
                        np.where(co.dias_hoy > 30 + lag, "PENDIENTE (TARDÍO)", "en plazo"))
co["rot_f"] = co.rot_ok.fillna(co.rot_sa)
co["t_rot"] = np.where(co.rot_f.isin(["TARDIO", "PENDIENTE (TARDÍO)"]), perd(ROT_TARDIA, co.tch, co.area), 0.0)
print(f"\n2027 roturación (fuente: oficial {co.rot_ok.notna().sum()} suertes, SimpleAgri {co.rot_ok.isna().sum()}):",
      co.groupby("rot_f").area.sum().round(0).to_dict())
print(f"   tardía o pendiente fuera de plazo: {co.area[co.t_rot > 0].sum():,.0f} ha · {co.t_rot.sum():,.0f} t")
print(f"   de esas, sin registro de roturación en SimpleAgri (puede faltar el registro): "
      f"{co.area[(co.rot_f == 'PENDIENTE (TARDÍO)')].sum():,.0f} ha · {co.t_rot[co.rot_f == 'PENDIENTE (TARDÍO)'].sum():,.0f} t")
co["pct_mal"] = [mal_pct(x, True) if pd.notna(x) else (MAL_30 * max(0.0, h - MAL_PLAZO) / 30 if h > MAL_PLAZO else 0.0)
                 for x, h in zip(co.d_maleza, co.dias_hoy)]
co["t_mal"] = perd(co.pct_mal, co.tch, co.area)
print(f"2027 malezas: {co.area[co.pct_mal < 0].sum():,.0f} ha con primer control después de 60 días (hecho o aún pendiente) · "
      f"{co.t_mal.sum():,.0f} t (pendientes cuentan con los días que ya pasaron)")
print("   primer control: hecho", co.d_maleza.notna().sum(), "suertes, mediana", co.d_maleza.median(), "días · pendiente",
      co.d_maleza.isna().sum(), "suertes, de ellas >60 días desde el corte:", int(((co.d_maleza.isna()) & (co.dias_hoy > 60)).sum()))
pd.to_pickle({"rot26": (r26_ha, r26_t), "mal26": (c26.h_area[c26.pct < 0].sum(), c26.t.sum()),
              "rot27": (co.area[co.t_rot > 0].sum(), co.t_rot.sum()), "mal27": (co.area[co.pct_mal < 0].sum(), co.t_mal.sum()),
              "lag": lag}, "labores_perdidas.pkl")
