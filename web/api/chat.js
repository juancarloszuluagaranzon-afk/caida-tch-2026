// Chat del informe «Caída del TCH Riopaila 2026»: responde preguntas solo con los datos del informe, usando Gemini
// (Google AI Studio). Función de Vercel; la llave va en la variable de entorno GEMINI_API_KEY (nunca en la página).
// Opcional: GEMINI_MODEL (por defecto gemini-flash-latest; si no existe, usa el «flash» más nuevo de la cuenta).
// POST /api/chat  {pregunta, historial: [{rol: 'usuario'|'modelo', texto}], suerte: clave de la ficha abierta o null}
// Responde texto plano que llega por partes (se muestra mientras se escribe); los errores, en JSON {error}.
'use strict';
const fs = require('fs');
const path = require('path');

let MODELO = process.env.GEMINI_MODEL || 'gemini-flash-latest';
const API = 'https://generativelanguage.googleapis.com/v1beta';
// razonamiento mínimo: estas preguntas buscan cifras en una tabla y el razonamiento era la mayor parte de la espera.
// Cada familia de Gemini acepta un ajuste distinto; si uno da 400 se prueba el siguiente (el último: sin ajuste).
const PENSAR = [{ thinkingLevel: 'minimal' }, { thinkingBudget: 0 }, { thinkingLevel: 'low' }, null];
let iPensar = 0;

// si el modelo no existe (Google retira y renombra modelos), elige el «flash» más nuevo de los disponibles para la llave
async function elegirModelo() {
  const r = await fetch(`${API}/models?pageSize=200`, { headers: { 'x-goog-api-key': process.env.GEMINI_API_KEY } });
  const j = await r.json();
  const ms = (j.models || []).filter(m => (m.supportedGenerationMethods || []).includes('generateContent'))
    .map(m => m.name.replace('models/', ''))
    .filter(n => /flash/.test(n) && !/(lite|image|tts|live|audio|thinking|exp|preview)/.test(n));
  const ver = n => parseFloat((n.match(/gemini-(\d+(?:\.\d+)?)/) || [0, 0])[1]);
  ms.sort((a, b) => ver(b) - ver(a) || a.length - b.length);
  return ms[0] || null;
}
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
- Escribe los números como en Colombia: coma decimal y punto de miles (110,3 TCH; 17.107 t; −5,4 %).
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
  const sistema = INSTRUCCIONES + (CONTEXTO || armarContexto());
  try {
    const llamar = () => {
      const generationConfig = { temperature: 0.2, maxOutputTokens: 8192 };   // el razonamiento, si lo hay, cuenta contra el tope
      if (PENSAR[iPensar]) generationConfig.thinkingConfig = PENSAR[iPensar];
      return fetch(`${API}/models/${MODELO}:streamGenerateContent?alt=sse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': process.env.GEMINI_API_KEY },
        body: JSON.stringify({ systemInstruction: { parts: [{ text: sistema }] }, contents, generationConfig }),
      });
    };
    let r = await llamar();
    for (let intento = 0; !r.ok && intento < PENSAR.length + 1; intento++) {
      if (r.status === 404) {                       // el modelo ya no existe: el «flash» más nuevo de la cuenta
        const otro = await elegirModelo();
        if (!otro || otro === MODELO) break;
        MODELO = otro; iPensar = 0;
      } else if (r.status === 400 && iPensar < PENSAR.length - 1) {
        iPensar++;                                  // este modelo no acepta ese ajuste de razonamiento: probar el siguiente
      } else break;
      r = await llamar();
    }
    if (!r.ok) {
      const j = await r.json().catch(() => null);
      const motivo = j && j.error && j.error.message ? ': ' + String(j.error.message).slice(0, 200) : '';
      return fin(502, { error: `Gemini no respondió (${r.status}${motivo}). Intente de nuevo en un momento.` });
    }
    // la respuesta llega por partes (SSE de Gemini) y se reenvía a la página como texto a medida que llega
    res.statusCode = 200;
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('X-Accel-Buffering', 'no');
    const dec = new TextDecoder();
    let buf = '', algo = false, cortada = false;
    for await (const trozo of r.body) {
      buf += dec.decode(trozo, { stream: true });
      let i;
      while ((i = buf.indexOf('\n')) >= 0) {
        const linea = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
        if (!linea.startsWith('data:')) continue;
        let ev; try { ev = JSON.parse(linea.slice(5)); } catch (e) { continue; }
        const c0 = ev.candidates && ev.candidates[0];
        const t = (c0 && c0.content && c0.content.parts || []).filter(p => !p.thought).map(p => p.text || '').join('');
        if (t) { res.write(t); algo = true; }
        if (c0 && c0.finishReason === 'MAX_TOKENS') cortada = true;
      }
    }
    if (!algo) res.write('No obtuve respuesta. Intente reformular la pregunta.');
    if (cortada) res.write('\n\n(La respuesta quedó cortada: haga una pregunta más concreta.)');
    return res.end();
  } catch (e) {
    if (res.headersSent) { res.write('\n\n(Se cortó la conexión con Gemini. Intente de nuevo.)'); return res.end(); }
    return fin(502, { error: 'No se pudo consultar a Gemini. Intente de nuevo en un momento.' });
  }
};
