# -*- coding: utf-8 -*-
r"""Imágenes Sentinel-2 (NDVI y color real) del rebrote de suertes de ejemplo: el ciclo que salió de un corte manual
frente al ciclo que salió de su primera cosecha mecánica, en la misma fecha del calendario (los dos cortes fueron a
mediados de julio, así que la edad es la misma).

Las fechas se eligieron de la serie de escenas despejadas sobre el bloque (Cloud Score+ cs_cdf ≥ 0,6 en ≥ 95 % del área;
la SCL sola dejaba pasar bruma). Para cada escena guarda el PNG con el contorno de cada suerte y el NDVI, el NDMI y la
parte del área con NDVI < 0,6 («rebrote ralo»). Usa la conexión de tch-motor/tchmotor/gee.py.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe mecanica_imagenes.py <salida>
"""
import json
import sys
import urllib.request
from pathlib import Path

import ee

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import gee  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
SAL = Path(sys.argv[1])
SAL.mkdir(parents=True, exist_ok=True)
gee.iniciar()

SUERTES = ["3501-550", "3501-551", "3501-560", "3501-561"]
# (etiqueta, fecha de la escena, ciclo, corte del que sale el ciclo)
ESCENAS = [("manual_100d", "2024-10-24", "después del corte manual de jul-2024", "2024-07"),
           ("mecanica_100d", "2025-10-22", "después del primer corte mecánico, jul-2025", "2025-07"),
           ("manual_150d", "2024-12-11", "después del corte manual de jul-2024", "2024-07"),
           ("mecanica_150d", "2025-12-08", "después del primer corte mecánico, jul-2025", "2025-07")]
PALETA = ["7f3b08", "b35806", "e08214", "fdb863", "f7f7c4", "d9f0a3", "78c679", "238443", "004529"]
pol = gee.coords_suertes("riopaila")
fc = ee.FeatureCollection([ee.Feature(gee.geom_ee(pol[s]), {"ste": s}) for s in SUERTES])
zona = fc.geometry()
marco = zona.bounds().buffer(150).bounds()
borde = ee.Image().byte().paint(fc, 1, 2).visualize(palette=["111111"])
cs = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")
log = []
for nom, fecha, ciclo, corte in ESCENAS:
    d = ee.Date(fecha)
    img = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(zona).filterDate(d, d.advance(1, "day"))
           .linkCollection(cs, ["cs_cdf"]).first())
    ok = img.select("cs_cdf").gte(0.6)
    ndvi = img.normalizedDifference(["B8", "B4"])
    ndmi = img.normalizedDifference(["B8", "B11"])
    m = ee.Image.cat([ok.rename("ok"), ndvi.rename("ndvi"), ndmi.rename("ndmi"), ndvi.lt(0.6).rename("rala")]) \
        .reduceRegion(ee.Reducer.mean(), zona, 10).getInfo()
    for capa, vis in (("ndvi", ndvi.visualize(min=0.1, max=0.9, palette=PALETA)),
                      ("color", img.select(["B4", "B3", "B2"]).visualize(min=0, max=2500, gamma=1.2))):
        url = vis.blend(borde).getThumbURL({"region": marco, "dimensions": 640, "format": "png"})
        urllib.request.urlretrieve(url, SAL / f"bloque3501_{nom}_{capa}.png")
    fila = {"escena": nom, "fecha": fecha, "ciclo": ciclo, "corte": corte, "despejado": round(m["ok"], 3),
            "ndvi": round(m["ndvi"], 3), "ndmi": round(m["ndmi"], 3), "rala_pct": round(100 * m["rala"], 1)}
    log.append(fila)
    print(fila)
json.dump(log, open(SAL / "escenas_bloque3501.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
