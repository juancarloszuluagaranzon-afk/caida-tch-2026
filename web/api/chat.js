// Chat del informe «Caída del TCH Riopaila 2026»: responde preguntas solo con los datos del informe, usando Gemini
// (Google AI Studio). Función de Vercel; la llave va en la variable de entorno GEMINI_API_KEY (nunca en la página).
// Opcional: GEMINI_MODEL (por defecto gemini-2.5-flash).
// POST /api/chat  {pregunta, historial: [{rol: 'usuario'|'modelo', texto}], suerte: clave de la ficha abierta o null}
'use strict';
const fs = require('fs');
const path = require('path');

const MODELO = process.env.GEMINI_MODEL || 'gemini-2.5-flash';
const POR_MINUTO = 6, POR_HORA = 120;   // por IP y por instancia: freno al gasto, no una garantía
const MAX_PREGUNTA = 600, MAX_HISTORIAL = 6;

let CONTEXTO = null;
const leer = n => JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', n), 'utf8'));

function armarContexto() {
  const R = leer('resumen.json'), C = leer('causas.json'), S = leer('suertes.json'), V = leer('validacion.json');
  let D = null;
  try { D = leer('desarrollo.json'); } catch (e) { /* sin aforo */ }
  const r1 = v => v == null ? '' : Math.round(v * 10) / 10;
  const causas = C.causas.map(c => `- ${c.id} = «${c.nombre}» (${c.grupo}): aporte promedio ${r1(-c.t_ha)} TCH. Qué mide: ${c.mide} Efecto: ${c.efecto}`).join('\n');
  const ids = C.causas.map(c => c.id);
  const afo = {};
  if (D) D.filas.forEach(x => { afo[x.s + '|' + x.m] = x; });
  const pct = (x, k) => x ? Math.round(100 * x[k] / x['o' + k]) : '';
  const peso = x => x ? Math.round(100 * (x.pob * x.alt * x.dia ** 2) / (x.opob * x.oalt * x.odia ** 2)) : '';
  const cab = ['suerte', 'hacienda', 'zona', 'zona_agroecologica', 'variedad', 'mes_cosecha', 'fecha_cosecha', 'n_corte', 'area_ha', 'edad_meses',
    'tipo_cosecha', 'corte_anterior', 'fecha_corte_anterior', 'TCH_corte_anterior', 'TCH_real', 'TCH_historia_2020_25', 'TCH_PPTO',
    'dias_mas_32C', 'dias_mas_32C_normal', 'lluvia_0_3m_mm', 'deficit_sin_riego_mm', 'riego_mm', 'nivel_freatico_m', 'lluvia_mes_corte_anterior_mm',
    'roturacion', 'dias_a_fertilizacion', 'incendio', 'renovacion_pendiente',
    ...ids.map(i => 'aporte_' + i), 'sin_explicar', 'aforo_poblacion_pct', 'aforo_altura_pct', 'aforo_diametro_pct', 'aforo_peso_cana_pct'];
  const filas = S.map(s => {
    const x = afo[s.s + '|' + s.m];
    return [s.s, s.h, s.z, s.za, s.v, s.m, s.f, s.c, s.a, s.ed, s.tipo, s.ant, s.ant_f, s.ant_tch, s.real, s.hist, s.ppto,
      s.d32, s.d32n, s.llu, s.dsr, s.rie, s.nf, s.mmca, s.rot, s.dfert, s.inc ? 'sí' : 'no', s.nr ? 'sí' : 'no',
      ...ids.map(i => r1(s.ap[i] == null ? null : -s.ap[i])), r1(s.se == null ? null : -s.se),
      pct(x, 'pob'), pct(x, 'alt'), pct(x, 'dia'), peso(x)].map(v => v == null ? '' : String(v).replace(/[;\n]/g, ',')).join(';');
  });
  const P = R.puente;
  const fac = V.v2.filter(f => !f[0].startsWith('Sin explicar')), se = V.v2.find(f => f[0].startsWith('Sin explicar'));
  const pred = fac.reduce((a, f) => a + f[1], 0), pctPred = Math.round(100 * pred / (pred + se[1]));   // como prediccion() en app.js
  CONTEXTO = `RESUMEN (${R.periodo}): ${R.cosechas} cosechas con historia (${R.ha} ha) de ${R.cosechas_total}. Histórico 2020-25 ${R.hist} TCH, real 2026 ${R.real} TCH,
caída ${R.caida} TCH (${R.caida_pct} %, ${R.t_caida} t). Sin explicar ${-R.sin_explicar} TCH.
Contra el presupuesto (${P.cosechas} cosechas con PPTO, ${P.ha} ha): PPTO ${P.ppto}, histórico de esas suertes ${P.hist}, real ${P.real} TCH.

CAUSAS (aporte en TCH: negativo = le quitó al TCH, positivo = le sumó):
${causas}

VALIDACIÓN: sin ver 2026 el modelo predijo el ${pctPred} % de la caída; correlación año por año 2013-2026 = ${V.corr}; suerte por suerte R² ${(V.r2 || []).map(r => r[1]).join(' a ')}.
${D ? `DESARROLLO DE LA CAÑA: aforo de la caña en pie antes de la cosecha frente al óptimo de su variedad (población en tallos/m, altura, diámetro; peso de caña = tallos × altura × diámetro²).
Diferencias frente a corte anterior manual (puntos de %, misma variedad y zona): ${D.pruebas.map(p => `${p.k} ${p.ant}: ${p.dif} (p=${p.p})`).join('; ')}.
El origen del «óptimo» de cada variedad no está confirmado. No es una causa aparte: es el camino por el que actúan las causas.` : ''}

SUERTES COSECHADAS EN 2026 (una fila por cosecha; separador «;»; aportes en TCH, negativo = le quitó; corte_anterior: manual, «mecánica tras manual» = primer corte mecanizado, «mecánica seguida» = dos mecanizados):
${cab.join(';')}
${filas.join('\n')}`;
  return CONTEXTO;
}

const INSTRUCCIONES = `Eres el asistente del informe «Caída del TCH Riopaila 2026» de Riopaila Agrícola. Respondes en español, claro y breve, a la gerencia y a los técnicos.
Reglas:
- Responde SOLO con los datos de abajo. Si algo no está en los datos, dilo («eso no está en los datos del informe») y no lo inventes ni lo completes con conocimiento general.
- Cita las cifras como vienen (TCH con una cifra decimal, toneladas sin decimales) y di de qué suertes o grupos salen. Para promedios de varias suertes, pondera por área_ha.
- Di siempre lo que el modelo NO demuestra cuando aplique: las cifras de cada causa son efectos promedio de 7.433 cosechas, no un diagnóstico de campo de cada suerte; suerte por suerte queda mucho «sin explicar».
- Términos de Riopaila: «cosecha mecanizada» (nunca «mecánica»), el rendimiento en «TCH» (nunca «t/ha»). La cosechadora daña la cepa y genera despoblación.
- Compara contra el presupuesto (PPTO) además de contra el histórico cuando sea útil.
- No uses ni menciones calificaciones 1-3-5 ni el nombre «AgroFactors». No menciones nombres de personas.
- Escribe en texto simple; puedes usar viñetas con «- » y negrita con **. Menciona las suertes por su código (por ejemplo 3501-551).
- Si te preguntan algo ajeno al informe, dilo amablemente y vuelve al tema.

DATOS DEL INFORME:
`;

const visitas = new Map();
function permitido(ip) {
  const ahora = Date.now(), v = (visitas.get(ip) || []).filter(t => ahora - t < 3600e3);
  if (v.filter(t => ahora - t < 60e3).length >= POR_MINUTO || v.length >= POR_HORA) { visitas.set(ip, v); return false; }
  v.push(ahora); visitas.set(ip, v);
  return true;
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') { res.statusCode = 405; return res.end(JSON.stringify({ error: 'Use POST' })); }
  const fin = (codigo, obj) => { res.statusCode = codigo; res.setHeader('Content-Type', 'application/json; charset=utf-8'); res.end(JSON.stringify(obj)); };
  if (!process.env.GEMINI_API_KEY) return fin(503, { error: 'El chat todavía no está configurado (falta la llave de Gemini en Vercel).' });
  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').split(',')[0].trim();
  if (!permitido(ip)) return fin(429, { error: 'Muchas preguntas seguidas. Espere un minuto e intente de nuevo.' });
  let b = req.body;
  if (typeof b === 'string') { try { b = JSON.parse(b); } catch (e) { b = null; } }
  const pregunta = b && typeof b.pregunta === 'string' ? b.pregunta.trim().slice(0, MAX_PREGUNTA) : '';
  if (!pregunta) return fin(400, { error: 'Escriba una pregunta.' });
  const hist = Array.isArray(b.historial) ? b.historial.slice(-MAX_HISTORIAL) : [];
  const suerte = typeof b.suerte === 'string' ? b.suerte.slice(0, 40) : '';
  const contents = hist.filter(h => h && typeof h.texto === 'string')
    .map(h => ({ role: h.rol === 'modelo' ? 'model' : 'user', parts: [{ text: h.texto.slice(0, 4000) }] }));
  contents.push({ role: 'user', parts: [{ text: (suerte ? `(Estoy viendo la ficha de la suerte ${suerte}.) ` : '') + pregunta }] });
  try {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODELO}:generateContent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-goog-api-key': process.env.GEMINI_API_KEY },
      body: JSON.stringify({ systemInstruction: { parts: [{ text: INSTRUCCIONES + (CONTEXTO || armarContexto()) }] }, contents,
        generationConfig: { temperature: 0.2, maxOutputTokens: 1500 } }),
    });
    const j = await r.json();
    if (!r.ok) return fin(502, { error: 'Gemini no respondió (' + r.status + '). Intente de nuevo en un momento.' });
    const texto = (j.candidates && j.candidates[0] && j.candidates[0].content && j.candidates[0].content.parts || []).map(p => p.text || '').join('').trim();
    return fin(200, { respuesta: texto || 'No obtuve respuesta. Intente reformular la pregunta.' });
  } catch (e) {
    return fin(502, { error: 'No se pudo consultar a Gemini. Intente de nuevo en un momento.' });
  }
};
