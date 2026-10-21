// Cache-busting build token. Locally the literal "2026-10-08" is a harmless
// query string; at publish time webapp/publish-stamp.mjs rewrites every
// occurrence in index.html and app.js to the bundle build value.
const BUILD = "2026-10-14-all-figures-reconciled";

const CODED_COLS = ["econ_eval_type", "design_basis", "model_label", "qaly_label",
  "oa_label", "geo_scope", "era", "topic_domain"];

// HTML-escapes a string for HTML sinks. Plotly renders hover `text` and
// hovertemplate output as HTML, so every data-derived string concatenated into
// hover text must pass through esc() first.
export function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// R-compatible round(x, digits) — half-to-even resolved on the EXACT binary
// value of the double, matching R >= 4.0.0 (DATA_CONTRACT.md §12). x is
// decomposed exactly into sign * m * 2^e from its IEEE-754 bits; |x| * 10^d is
// kept as the exact BigInt rational num/den; the half-to-even integer
// q = round(num/den) is computed with no floating-point error at all; the
// result is the correctly-rounded double q / 10^d.
// Proofs (verified against R 4.4.1): round(2.675, 2) = 2.67 (the stored double
// is BELOW the midpoint), round(0.125, 2) = 0.12 (exact in binary, tie -> even),
// round(0.135, 2) = 0.14 (the stored double is ABOVE the midpoint).
export function rRound(x, digits = 0) {
  if (x == null || !isFinite(x)) return x;
  if (x === 0) return x;
  const d = Math.trunc(digits);

  const dv = new DataView(new ArrayBuffer(8));
  dv.setFloat64(0, x);
  const hi = dv.getUint32(0), lo = dv.getUint32(4);
  const negative = (hi >>> 31) === 1;
  const biasedExp = (hi >>> 20) & 0x7ff;
  const frac = (BigInt(hi & 0xfffff) << 32n) | BigInt(lo >>> 0);
  let m, e;
  if (biasedExp === 0) {
    m = frac; e = -1074;                                  // subnormal
  } else {
    m = (1n << 52n) | frac; e = biasedExp - 1023 - 52;    // normal: |x| = m * 2^e
  }

  // num/den = |x| * 10^d, exact
  let num = m, den = 1n;
  if (d >= 0) num *= 10n ** BigInt(d); else den *= 10n ** BigInt(-d);
  if (e >= 0) num *= 2n ** BigInt(e); else den *= 2n ** BigInt(-e);

  // half-to-even quotient
  let q = num / den;
  const twice = (num % den) * 2n;
  if (twice > den || (twice === den && q % 2n === 1n)) q += 1n;
  if (negative) q = -q;

  return Number(q) / Math.pow(10, d);
}

export function fmtNum(x) {
  if (x == null) return "";
  return Number(x).toLocaleString("en-US");
}

// Publication links and availability come from the same study-level fields.
export function publicationUrl(studies, index) {
  const candidate = studies.url?.[index];
  if (candidate) {
    try {
      const parsed = new URL(candidate);
      if (parsed.protocol === "https:" || parsed.protocol === "http:") return parsed.href;
    } catch { /* Invalid URLs are not rendered as links. */ }
  }
  const doi = studies.doi?.[index];
  return /^10\.\d{4,9}\/\S+$/i.test(doi || "") ? "https://doi.org/" + doi : null;
}

export function publicationAccessCounts(studies) {
  if (!Array.isArray(studies.doi) || !Array.isArray(studies.url)) return null;
  return studies.id.reduce((count, _, index) => count + (publicationUrl(studies, index) ? 1 : 0), 0);
}

function num(v) {
  return (typeof v === "number" && isFinite(v)) ? v : null;
}

function ratio(n, d) {
  const dd = num(d);
  return (dd != null && dd > 0) ? n / dd : null;
}

function sortedYearObj(map) {
  const out = {};
  for (const y of [...map.keys()].sort((a, b) => a - b)) out[y] = map.get(y);
  return out;
}

// Builds the ordered label→column registries (DATA_CONTRACT.md §15.6) from
// content.json. Map preserves insertion order, so selector/legend order is the
// content.json array order. Replaces the previously hardcoded TREND_VARS /
// COMP_VARS / STACK_VARS / MAP_METRICS / SCAT_X / SCAT_Y / SIGNAL_METRICS.
export function buildRegistries(content) {
  if (!content || !content.registries) {
    throw new Error("buildRegistries: content.json with .registries is required");
  }
  const r = content.registries;
  const toMap = arr => new Map(arr.map(o => [o.label, o.column]));
  return {
    TREND_VARS: toMap(r.trend_vars),
    COMP_VARS: toMap(r.comp_vars),
    STACK_VARS: toMap(r.stack_vars),
    MAP_METRICS: toMap(r.map_metrics),
    SCAT_X: toMap(r.scat_x),
    SCAT_Y: toMap(r.scat_y),
    SIGNAL_METRICS: r.signal_metrics.slice()
  };
}

export function loadData({ dict, studies, geo, disease, countries, content }) {
  const levels = dict.levels;
  const codeOf = {};
  for (const col of CODED_COLS) {
    codeOf[col] = new Map(levels[col].map((lab, i) => [lab, i]));
  }
  const pal = dict.meta.pal_inc;
  const palInc = {};
  if (Array.isArray(pal)) dict.meta.inc_lv.forEach((lv, i) => { palInc[lv] = pal[i]; });
  else Object.assign(palInc, pal);
  Object.assign(palInc, LANDSCAPE_INCOME_COLORS);
  const diseaseSets = dict.disease_grps.map(() => new Set());
  for (let i = 0; i < disease.s.length; i++) diseaseSets[disease.g[i]].add(disease.s[i]);
  return {
    dict, levels, studies, geo, disease, countries,
    content,
    registries: buildRegistries(content),
    nStudies: studies.id.length,
    codeOf,
    palInc,
    incLv: dict.meta.inc_lv.slice(),
    incOrder: dict.meta.inc_lv.slice().reverse(),
    incomeOf: countries.map(r => r.income),
    regionOf: countries.map(r => r.un_region),
    disease_grps: dict.disease_grps,
    diseaseSets,
    years: dict.years
  };
}

export function normalizeFilter(filt, db) {
  const f = filt || {};
  const one = v => Array.isArray(v) ? (v.length ? v[0] : "All") : (v == null ? "All" : v);
  const arr = v => Array.isArray(v) ? v : (v == null ? [] : [v]);
  return {
    years: f.years ? [f.years[0], f.years[1]] : (db ? db.years.slice() : [2010, 2026]),
    income: arr(f.income),
    region: arr(f.region),
    disease: arr(f.disease),
    evaltype: arr(f.evaltype),
    design: arr(f.design),
    model: one(f.model),
    qaly: one(f.qaly),
    oa: one(f.oa),
    scope: one(f.scope)
  };
}

export function applyFilters(db, filt) {
  const f = normalizeFilter(filt, db);
  const st = db.studies;
  const n = db.nStudies;
  const [lo, hi] = f.years;
  const base = new Uint8Array(n);

  const evalCodes = f.evaltype.length
    ? new Set(f.evaltype.map(l => db.codeOf.econ_eval_type.get(l))) : null;
  const designCodes = f.design.length
    ? new Set(f.design.map(l => db.codeOf.design_basis.get(l))) : null;
  const modelCode = f.model !== "All" ? db.codeOf.model_label.get(f.model) : null;
  const qalyCode = f.qaly !== "All" ? db.codeOf.qaly_label.get(f.qaly) : null;
  const oaCode = f.oa !== "All" ? db.codeOf.oa_label.get(f.oa) : null;
  const scopeCode = f.scope !== "All" ? db.codeOf.geo_scope.get(f.scope) : null;
  let disSet = null;
  if (f.disease.length) {
    disSet = new Set();
    for (const g of f.disease) {
      const gi = db.disease_grps.indexOf(g);
      if (gi >= 0) for (const s of db.diseaseSets[gi]) disSet.add(s);
    }
  }

  for (let s = 0; s < n; s++) {
    const y = st.year[s];
    if (y < lo || y > hi) continue;
    if (evalCodes && !evalCodes.has(st.econ_eval_type[s])) continue;
    if (designCodes && !designCodes.has(st.design_basis[s])) continue;
    if (modelCode !== null && st.model_label[s] !== modelCode) continue;
    if (qalyCode !== null && st.qaly_label[s] !== qalyCode) continue;
    if (oaCode !== null && st.oa_label[s] !== oaCode) continue;
    if (scopeCode !== null && st.geo_scope[s] !== scopeCode) continue;
    if (disSet && !disSet.has(s)) continue;
    base[s] = 1;
  }

  const g = db.geo;
  const incSet = f.income.length ? new Set(f.income) : null;
  const regSet = f.region.length ? new Set(f.region) : null;
  const countryFilterActive = !!(incSet || regSet);
  const geoRows = [];
  const geoStudySet = countryFilterActive ? new Set() : null;
  for (let i = 0; i < g.s.length; i++) {
    const s = g.s[i];
    if (!base[s]) continue;
    const c = g.c[i];
    if (incSet && !incSet.has(db.incomeOf[c])) continue;
    if (regSet) {
      const r = db.regionOf[c];
      if (r == null || !regSet.has(r)) continue;
    }
    geoRows.push(i);
    if (geoStudySet) geoStudySet.add(s);
  }

  const studies = [];
  const mask = new Uint8Array(n);
  for (let s = 0; s < n; s++) {
    if (!base[s]) continue;
    if (geoStudySet && !geoStudySet.has(s)) continue;
    studies.push(s);
    mask[s] = 1;
  }

  const counts = new Int32Array(db.countries.length);
  for (const i of geoRows) counts[g.c[i]]++;
  const present = [];
  const rest = [];
  for (let c = 0; c < db.countries.length; c++) {
    if (counts[c] > 0) present.push(c); else rest.push(c);
  }
  present.sort((a, b) => db.countries[a].iso3 < db.countries[b].iso3 ? -1
    : db.countries[a].iso3 > db.countries[b].iso3 ? 1 : 0);
  const byCountry = present.concat(rest).map(c => {
    const r = db.countries[c];
    const dalys = num(r.dalys);
    const spend = num(r.total_spend_bn);
    const pop = num(r.pop);
    return {
      c,
      iso3: r.iso3,
      country: r.country,
      income: r.income,
      un_region: r.un_region,
      pop: pop,
      dalys: dalys,
      total_spend_bn: spend,
      studies: counts[c],
      per100k: ratio(counts[c], dalys == null ? null : dalys / 1e5),
      per_bn: ratio(counts[c], spend),
      per_million: ratio(counts[c], pop == null ? null : pop / 1e6)
    };
  });

  return { filt: f, mask, studies, geoRows, byCountry };
}

export function valueBoxes(db, flt) {
  const n = flt.studies.length;
  const cs = new Set();
  for (const i of flt.geoRows) cs.add(db.geo.c[i]);
  const mCode = db.codeOf.model_label.get("Model-based");
  const qCode = db.codeOf.qaly_label.get("Uses QALY");
  let m = 0, q = 0;
  for (const s of flt.studies) {
    if (db.studies.model_label[s] === mCode) m++;
    if (db.studies.qaly_label[s] === qCode) q++;
  }
  return {
    v_studies: n,
    v_countries: cs.size,
    v_model_pct: n ? rRound(100 * m / n) : null,
    v_qaly_pct: n ? rRound(100 * q / n) : null
  };
}

export function trendSeries(db, flt, varName) {
  if (varName === "none") {
    const counts = new Map();
    for (const s of flt.studies) {
      const y = db.studies.year[s];
      counts.set(y, (counts.get(y) || 0) + 1);
    }
    return sortedYearObj(counts);
  }
  const isGeo = varName === "income" || varName === "un_region";
  const counts = new Map();
  const bump = (y, cat) => {
    let m = counts.get(y);
    if (!m) { m = new Map(); counts.set(y, m); }
    m.set(cat, (m.get(cat) || 0) + 1);
  };
  if (isGeo) {
    const seen = new Set();
    for (const i of flt.geoRows) {
      const s = db.geo.s[i], y = db.geo.y[i], c = db.geo.c[i];
      const cat = varName === "income" ? db.incomeOf[c] : db.regionOf[c];
      if (cat == null) continue;
      const key = s + "|" + y + "|" + cat;
      if (seen.has(key)) continue;
      seen.add(key);
      bump(y, cat);
    }
  } else {
    const lv = db.levels[varName];
    for (const s of flt.studies) {
      bump(db.studies.year[s], lv[db.studies[varName][s]]);
    }
  }
  const out = {};
  for (const y of [...counts.keys()].sort((a, b) => a - b)) {
    out[y] = Object.fromEntries(counts.get(y));
  }
  return out;
}

function studyCatGetter(db, varName) {
  const st = db.studies;
  if (varName === "icer_label") return s => st.has_icer[s] === 1 ? "ICER reported" : "Not reported";
  if (varName === "thresh_label") return s => st.has_threshold[s] === 1 ? "Threshold reported" : "Not reported";
  const lv = db.levels[varName];
  const col = st[varName];
  return s => lv[col[s]];
}

export function compCounts(db, flt, xv, sv, mode) {
  const pct = mode === "pct";
  const stacked = !!(sv && sv !== xv);
  // OA percentages condition on known status, matching the overview card.
  // Count mode retains Unknown so missingness remains inspectable.
  const knownOaOnly = pct && (xv === "oa_label" || (stacked && sv === "oa_label"));
  const unknownOa = db.codeOf.oa_label.get("Unknown");
  const excludedUnknown = knownOaOnly
    ? flt.studies.filter(s => db.studies.oa_label[s] === unknownOa).length : 0;
  const eligibleOa = s => !knownOaOnly || db.studies.oa_label[s] !== unknownOa;
  const counts = new Map();
  const add = (cat, stk) => {
    if (cat == null) return;
    if (!stacked) {
      counts.set(cat, (counts.get(cat) || 0) + 1);
    } else {
      if (stk == null) return;
      let m = counts.get(cat);
      if (!m) { m = new Map(); counts.set(cat, m); }
      m.set(stk, (m.get(stk) || 0) + 1);
    }
  };

  if (xv === "grp") {
    const stackOf = stacked ? studyCatGetter(db, sv) : null;
    const d = db.disease;
    for (let i = 0; i < d.s.length; i++) {
      const s = d.s[i];
      if (!flt.mask[s] || !eligibleOa(s)) continue;
      add(db.disease_grps[d.g[i]], stacked ? stackOf(s) : null);
    }
  } else {
    const catOf = studyCatGetter(db, xv);
    const stackOf = stacked ? studyCatGetter(db, sv) : null;
    for (const s of flt.studies) {
      if (eligibleOa(s)) add(catOf(s), stacked ? stackOf(s) : null);
    }
  }

  const cmpStr = (a, b) => a < b ? -1 : a > b ? 1 : 0;

  if (!stacked) {
    const rows = [...counts.entries()].map(([x, nn]) => ({ x, n: nn }));
    rows.sort((a, b) => cmpStr(a.x, b.x));
    const total = rows.reduce((a, r) => a + r.n, 0);
    for (const r of rows) r.v = pct ? (total > 0 ? 100 * r.n / total : 0) : r.n;
    rows.sort((a, b) => b.v - a.v);
    return { type: "simple", rows, total, pct, knownOaOnly, excludedUnknown };
  }

  const cats = [...counts.keys()].sort(cmpStr);
  const totals = new Map();
  for (const c of cats) {
    let t = 0;
    for (const v of counts.get(c).values()) t += v;
    totals.set(c, t);
  }
  const catOrder = cats.slice()
    .sort((a, b) => (totals.get(a) - totals.get(b)) || cmpStr(a, b))
    .reverse();
  const stackSet = new Set();
  for (const c of cats) for (const k of counts.get(c).keys()) stackSet.add(k);
  const stacks = [...stackSet].sort(cmpStr);
  const rawCounts = {};
  const values = {};
  for (const c of cats) {
    rawCounts[c] = Object.fromEntries(counts.get(c));
    values[c] = {};
    for (const [k, nn] of counts.get(c)) {
      values[c][k] = pct ? (totals.get(c) > 0 ? 100 * nn / totals.get(c) : 0) : nn;
    }
  }
  return { type: "stacked", catOrder, stacks, counts: rawCounts, values, totals: Object.fromEntries(totals), pct, knownOaOnly, excludedUnknown };
}

export function byCountryTop(db, flt, k = 10) {
  const rows = flt.byCountry.filter(r => r.studies > 0);
  rows.sort((a, b) => b.studies - a.studies);
  return rows.slice(0, k).map(r => ({
    iso3: r.iso3,
    studies: r.studies,
    per100k: r.per100k,
    per_bn: r.per_bn,
    per_million: r.per_million
  }));
}

export function scatterPoints(db, flt, xv, yv) {
  return flt.byCountry.filter(r =>
    r.studies > 0 &&
    r[xv] != null && r[xv] > 0 &&
    r[yv] != null && r[yv] > 0 &&
    r.income != null);
}

export function tableRows(db, flt, k = 25) {
  const rows = flt.byCountry.filter(r => r.studies > 0);
  rows.sort((a, b) => b.studies - a.studies);
  return rows.slice(0, k).map(r => ({
    Country: r.country,
    Income: r.income,
    Region: r.un_region == null ? "" : r.un_region,
    Studies: r.studies,
    "Per 100k DALYs": r.per100k == null ? null : rRound(r.per100k, 2),
    "Per US$1bn": r.per_bn == null ? null : rRound(r.per_bn, 2),
    "Per million": r.per_million == null ? null : rRound(r.per_million, 2)
  }));
}

const cmpStr = (a, b) => a < b ? -1 : a > b ? 1 : 0;

function profileSets(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const income = db.countries[ci].income;
  const g = db.geo;
  const cs = new Set(), ps = new Set();
  for (let i = 0; i < g.s.length; i++) {
    const c = g.c[i], s = g.s[i];
    if (c === ci) cs.add(s);
    if (db.incomeOf[c] === income) ps.add(s);
  }
  return { ci, income, cs, ps };
}

function methodsMixSets(db, cs, ps) {
  const lv = db.levels.econ_eval_type;
  const col = db.studies.econ_eval_type;
  const cn = new Map(), pn = new Map();
  for (const s of cs) { const t = lv[col[s]]; cn.set(t, (cn.get(t) || 0) + 1); }
  for (const s of ps) { const t = lv[col[s]]; pn.set(t, (pn.get(t) || 0) + 1); }
  const nc = cs.size, np = ps.size;
  const rows = [...new Set([...cn.keys(), ...pn.keys()])].map(t => ({
    type: t,
    country_share: nc > 0 ? 100 * (cn.get(t) || 0) / nc : null,
    peer_share: np > 0 ? 100 * (pn.get(t) || 0) / np : null
  }));
  const y_order = rows.slice()
    .sort((a, b) => ((b.peer_share == null ? 0 : b.peer_share) -
                     (a.peer_share == null ? 0 : a.peer_share)) || cmpStr(a.type, b.type))
    .map(r => r.type);
  rows.sort((a, b) => y_order.indexOf(a.type) - y_order.indexOf(b.type));
  return { rows, y_order };
}

export function methodsMix(db, iso3) {
  const sets = profileSets(db, iso3);
  return sets ? methodsMixSets(db, sets.cs, sets.ps) : null;
}

function signalCounts(db, set) {
  const st = db.studies;
  const mCode = db.codeOf.model_label.get("Model-based");
  const qCode = db.codeOf.qaly_label.get("Uses QALY");
  const oaCode = db.codeOf.oa_label.get("Open access");
  const unkCode = db.codeOf.oa_label.get("Unknown");
  let m = 0, q = 0, ic = 0, th = 0, oaKnown = 0, oa = 0;
  for (const s of set) {
    if (st.model_label[s] === mCode) m++;
    if (st.qaly_label[s] === qCode) q++;
    if (st.has_icer[s] === 1) ic++;
    if (st.has_threshold[s] === 1) th++;
    const o = st.oa_label[s];
    if (o !== unkCode) { oaKnown++; if (o === oaCode) oa++; }
  }
  return { n: set.size, m, q, ic, th, oaKnown, oa };
}

function signalsSets(db, cs, ps) {
  const c = signalCounts(db, cs), p = signalCounts(db, ps);
  const whole = (k, cc) => cc.n > 0 ? 100 * cc[k] / cc.n : null;
  const oaPct = cc => cc.oaKnown > 0 ? 100 * cc.oa / cc.oaKnown : null;
  const val = (metric, cc) => {
    if (metric === "Model-based") return whole("m", cc);
    if (metric === "Uses QALY") return whole("q", cc);
    if (metric === "Reports ICER") return whole("ic", cc);
    if (metric === "Reports threshold") return whole("th", cc);
    return oaPct(cc);
  };
  const rows = db.registries.SIGNAL_METRICS.map(metric => ({
    metric, country_pct: val(metric, c), peer_pct: val(metric, p)
  }));
  return { rows, country_oa_n: c.oaKnown, peer_oa_n: p.oaKnown };
}

export function signals(db, iso3) {
  const sets = profileSets(db, iso3);
  return sets ? signalsSets(db, sets.cs, sets.ps) : null;
}

export function benchmark(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const income = db.countries[ci].income;
  const rows = [];
  for (const r of db.countries) {
    if (r.income !== income) continue;
    const dalys = num(r.dalys), per100k = num(r.per100k_dalys);
    if (dalys == null || per100k == null || dalys <= 0 || per100k <= 0) continue;
    rows.push({ iso3: r.iso3, country: r.country, studies: r.studies, dalys, per100k });
  }
  rows.sort((a, b) => cmpStr(a.iso3, b.iso3));
  const v = rows.map(r => r.per100k).sort((a, b) => a - b);
  const mid = v.length >> 1;
  const median_per100k = !v.length ? null
    : (v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2);
  const selected = rows.some(r => r.iso3 === iso3) ? iso3 : null;
  return { rows, median_per100k, n_points: rows.length, selected };
}

export function countryProfile(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const r = db.countries[ci];
  const peers = db.countries.filter(x => x.income === r.income);
  const n_peer = peers.length;
  const median = vals => {
    const v = vals.map(num).filter(x => x != null).sort((a, b) => a - b);
    if (!v.length) return null;
    const m = v.length >> 1;
    return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
  };
  const medians = {
    m_daly: median(peers.map(x => x.per100k_dalys)),
    m_bn: median(peers.map(x => x.per_bn_usd)),
    m_mil: median(peers.map(x => x.per_million))
  };

  const g = db.geo;
  const cTrendCountry = new Map();
  const cTrendPeer = new Map();
  const mineSet = new Set();
  const peerSet = new Set();
  for (let i = 0; i < g.s.length; i++) {
    const c = g.c[i], y = g.y[i], s = g.s[i];
    if (c === ci) {
      cTrendCountry.set(y, (cTrendCountry.get(y) || 0) + 1);
      mineSet.add(s);
    }
    if (db.incomeOf[c] === r.income) {
      cTrendPeer.set(y, (cTrendPeer.get(y) || 0) + 1);
      peerSet.add(s);
    }
  }
  const peerTrend = {};
  for (const y of [...cTrendPeer.keys()].sort((a, b) => a - b)) {
    peerTrend[y] = cTrendPeer.get(y) / n_peer;
  }

  const mixC = {}, mixP = {};
  let totC = 0, totP = 0;
  const d = db.disease;
  for (let i = 0; i < d.s.length; i++) {
    const s = d.s[i];
    const grp = db.disease_grps[d.g[i]];
    if (mineSet.has(s)) { mixC[grp] = (mixC[grp] || 0) + 1; totC++; }
    if (peerSet.has(s)) { mixP[grp] = (mixP[grp] || 0) + 1; totP++; }
  }
  const shares = (o, t) => {
    const out = {};
    for (const k of Object.keys(o).sort()) out[k] = t > 0 ? 100 * o[k] / t : 0;
    return out;
  };

  const mm = methodsMixSets(db, mineSet, peerSet);
  const sg = signalsSets(db, mineSet, peerSet);
  const bm = benchmark(db, iso3);

  return {
    iso3: r.iso3,
    income: r.income,
    un_region: r.un_region,
    c_n: r.studies,
    c_daly: num(r.per100k_dalys),
    c_spend: num(r.per_bn_usd),
    c_percap: num(r.per_million),
    medians,
    n_peer,
    c_trend: { country: sortedYearObj(cTrendCountry), peer: peerTrend },
    c_mix: { country: shares(mixC, totC), peer: shares(mixP, totP) },
    c_methods: Object.assign(
      Object.fromEntries(mm.rows.map(x => [x.type,
        { country_share: x.country_share, peer_share: x.peer_share }])),
      { y_order: mm.y_order }),
    c_signals: Object.assign(
      Object.fromEntries(sg.rows.map(x => [x.metric,
        { country_pct: x.country_pct, peer_pct: x.peer_pct }])),
      { country_oa_n: sg.country_oa_n, peer_oa_n: sg.peer_oa_n }),
    c_benchmark: { median_per100k: bm.median_per100k, n_points: bm.n_points, rows: bm.rows }
  };
}

export function countryFacts(db, iso3) {
  const r = db.countries.find(x => x.iso3 === iso3);
  if (!r) return [];
  const pop = num(r.pop), dalys = num(r.dalys), spend = num(r.total_spend_bn);
  const pairs = [
    ["Income group", r.income],
    ["UN region", r.un_region == null ? "—" : r.un_region]
  ];
  if (pop != null) pairs.push(["Population", fmtNum(rRound(pop / 1e6)) + " M"]);
  if (dalys != null) pairs.push(["Disease burden", fmtNum(rRound(dalys / 1e6)) + " M DALYs (2023)"]);
  if (spend != null) pairs.push(["Health spending", "US$ " + fmtNum(rRound(spend)) + " bn (PPP 2022)"]);
  pairs.push(["Studies per million", rRound(num(r.per_million), 2)]);
  return pairs;
}

// ---- Country landscape tab (DATA_CONTRACT.md §16) --------------------------
// The interaction design is adapted from suvarnapande/hff-landscape @
// 6bc2b0c90349e78450fae45a70cfc4ac085a587d (reference-only; no code copied
// verbatim). The tab is UNFILTERED: it reads only the precomputed unfiltered
// countries.json columns and the raw geo/disease/studies tables, and never
// touches the Explorer filter state.

// Per-country bubble-scatter rows. Guard order mirrors §10.5: studies > 0,
// usable burden, usable per-100k intensity, non-null income.
export function landscapePoints(db) {
  const pts = [];
  for (let c = 0; c < db.countries.length; c++) {
    const r = db.countries[c];
    if (r.studies <= 0) continue;
    const dalys = num(r.dalys);
    const per100k = num(r.per100k_dalys);
    if (dalys == null || dalys <= 0) continue;
    if (per100k == null || per100k <= 0) continue;
    if (r.income == null) continue;
    const spend = num(r.total_spend_bn);
    const pop = num(r.pop);
    pts.push({
      c,
      iso3: r.iso3,
      country: r.country,
      income: r.income,
      studies: r.studies,
      dalys,
      per100k,
      per_bn: num(r.per_bn_usd),
      per_million: num(r.per_million),
      spend_per_person: (spend != null && pop != null && pop > 0) ? spend * 1e9 / pop : null
    });
  }
  return pts;
}

// Picker options for the landscape tab: every country with at least one study,
// name-ascending. Exported so the harness can assert the option set without a
// DOM. The tab stays unfiltered: this chooses which country's panels are shown,
// not which studies are counted.
export function landscapeCountries(db) {
  return db.countries
    .filter(r => r.studies > 0)
    .map(r => ({ iso3: r.iso3, country: r.country, studies: r.studies }))
    .sort((a, b) => a.country.localeCompare(b.country));
}

// Country mixes and the disease-group × evaluation-type cross grid (§16.6).
// CS(c) = distinct geo.s with geo.c === c (equals countries[c].studies).
// cell(gi, ei) = | CS ∩ dSet(gi) ∩ eSet(ei) |, keyed by the string gi + "|" + ei
// with both 0-based integer codes. Mix rows sort count-descending, ties
// alphabetical; the cross grid follows those row/column orders.
export function countryMixes(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const g = db.geo;
  const cs = new Set();
  for (let i = 0; i < g.s.length; i++) if (g.c[i] === ci) cs.add(g.s[i]);

  const lv = db.levels.econ_eval_type;
  const evalCounts = new Map();
  for (const s of cs) {
    const t = lv[db.studies.econ_eval_type[s]];
    evalCounts.set(t, (evalCounts.get(t) || 0) + 1);
  }
  const evalMix = [...evalCounts.entries()]
    .map(([label, count]) => ({ label, code: lv.indexOf(label), count }))
    .sort((a, b) => (b.count - a.count) || cmpStr(a.label, b.label));

  const d = db.disease;
  const diseaseCounts = new Map();
  for (let i = 0; i < d.s.length; i++) {
    const s = d.s[i];
    if (!cs.has(s)) continue;
    diseaseCounts.set(d.g[i], (diseaseCounts.get(d.g[i]) || 0) + 1);
  }
  const diseaseMix = [...diseaseCounts.entries()]
    .map(([code, count]) => ({ label: db.disease_grps[code], code, count }))
    .sort((a, b) => (b.count - a.count) || cmpStr(a.label, b.label));

  const eSet = lv.map(() => new Set());
  for (let s = 0; s < db.nStudies; s++) eSet[db.studies.econ_eval_type[s]].add(s);

  const cross = {};
  for (const dr of diseaseMix) {
    const giSet = db.diseaseSets[dr.code];
    for (const er of evalMix) {
      const eiSet = eSet[er.code];
      const indices = [];
      for (const s of cs) if (giSet.has(s) && eiSet.has(s)) indices.push(s);
      indices.sort((a, b) => a - b);
      cross[dr.code + "|" + er.code] = {
        gi: dr.code, ei: er.code,
        disease: dr.label, eval: er.label,
        count: indices.length, indices
      };
    }
  }

  const r = db.countries[ci];
  return {
    iso3, country: r.country, income: r.income,
    n_studies: cs.size,
    evalMix, diseaseMix, cross
  };
}

// Rows for the drill-down modal from the lazily loaded shard on db.drill[iso3]
// (shape §16.2). `missing` marks an index absent from this country's file.
export function drillRecords(db, iso3, indices) {
  const payload = db.drill && db.drill[iso3];
  if (!payload) return [];
  const pos = new Map();
  for (let i = 0; i < payload.s.length; i++) pos.set(payload.s[i], i);
  return indices.map(s => {
    const i = pos.get(s);
    if (i == null) {
      return { s, title: null, abstract: null, truncated: false, missing: true };
    }
    return {
      s,
      title: payload.t[i],
      abstract: payload.a[i],
      truncated: payload.x[i] === 1,
      missing: false
    };
  });
}

// Registry constants (TREND_VARS / COMP_VARS / STACK_VARS / MAP_METRICS /
// SCAT_X / SCAT_Y / SIGNAL_METRICS) now come from content.json registries —
// see buildRegistries() and db.registries (DATA_CONTRACT.md §9, §15.6).

const OA_COLORS = { "Open access": "#1baf7a", "Not open": "#eb6834", "Unknown": "#adb5bd" };
const ACCENT = "#1f5fa8";
const GREY = "#adb5bd";
// Softer income colours, shared by every income-coloured chart.
const LANDSCAPE_INCOME_COLORS = {
  "Low income": "#c96a4a",
  "Lower middle income": "#d2a84a",
  "Upper middle income": "#3b9b84",
  "High income": "#356fa8"
};
// Country profile: light-to-strong ramps for the country bars, grey-blue for peers.
const PROFILE_BLUE = ["#c9ddef", "#9fc4df", "#70a7cf", "#4288bb", "#1f659f"];
const PROFILE_TEAL = ["#d8ebe4", "#add6c7", "#79bda6", "#48a087", "#217b68"];
const PROFILE_LAVENDER = ["#e5ddec", "#cab9da", "#ad91c4", "#8c69aa", "#6d4d8e"];
const PROFILE_PEER = ["#edf1f4", "#dfe6eb", "#ced9e1", "#bdcbd5", "#aabcc8"];
// Default series colours for interactive charts (same family as the figures).
const SOFT_COLORWAY = ["#1764C0", "#2F9B92", "#63B0BC", "#93A3D0", "#D2B06B", "#88B7A8",
  "#B79BCB", "#7E94B1", "#C98F7A", "#9FB7C8"];
// Light-to-strong blue-teal ramp used for single-series bars and maps.
const SOFT_RAMP = ["#dcecf3", "#bddbe7", "#8fc7cf", "#5eb2ba", "#2f8f9d", "#1f5fa8"];

function rampColor(t) {
  const stops = SOFT_RAMP.map(h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)));
  const x = Math.min(1, Math.max(0, t)) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(x));
  const f = x - i;
  const c = stops[i].map((v, k) => Math.round(v + (stops[i + 1][k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

// n colours spread evenly along a ramp (bar i of n gets colours[k]).
function spreadPalette(colors, n) {
  return Array.from({ length: n }, (_, i) => colors[Math.min(
    colors.length - 1,
    Math.round(i * (colors.length - 1) / Math.max(1, n - 1))
  )]);
}

// The gallery registry (section titles, blurbs, figure files/titles/captions,
// incl. the interpolated paper01 PRISMA caption) now ships in content.json
// (DATA_CONTRACT.md §15.1) and is consumed as db.content.gallery — the
// hardcoded galleryRegistry() duplicate was removed.

if (typeof document !== "undefined") {

  const $ = id => document.getElementById(id);
  const PLOTLY_CFG = { responsive: true, displayModeBar: false };
  const BASE_FONT = { family: "Inter, sans-serif", size: 12, color: "#1c2733" };

  let db = null;
  let GALLERY = [];
  let FIG_INDEX = {};
  // Country landscape state: lazy drill shards cached per ISO3, and the fresh
  // index object read by the bound-once heatmap click handler (§16.6).
  const drillCache = {};
  let landCrossIndex = null;
  // TomSelect instance for the landscape country picker. Selecting a country
  // drives the same showCountryMix() as a bubble click; it never touches
  // Explorer state.
  let landSelect = null;
  const state = {
    filt: null,
    result: null,
    country: "IND",
    ts: {}
  };

  function debounce(fn, ms) {
    let t = null;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  // TRUST BOUNDARY: el()'s `html` argument goes through innerHTML and must
  // ONLY receive developer-authored literals. Data-derived strings (anything
  // from data/*.json, user-influenced values, exception messages) must be set
  // with textContent, or escaped with esc() before being embedded in an HTML
  // string (Plotly hover text). content.json strings are developer-authored
  // (generated by our R build from R/app-content.R) and would be acceptable
  // here, but are rendered via textContent anyway.
  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function fillSelect(sel, labels, selected) {
    sel.textContent = "";
    for (const lab of labels) {
      const o = document.createElement("option");
      o.value = lab;
      o.textContent = lab;
      if (selected && selected.includes(lab)) o.selected = true;
      sel.appendChild(o);
    }
  }

  let figureZoom = 1;

  function setFigureZoom(nextZoom) {
    figureZoom = Math.min(3, Math.max(0.5, nextZoom));
    $("fig-modal-img").style.width = (figureZoom * 100) + "%";
    $("fig-zoom-reset").textContent = Math.round(figureZoom * 100) + "%";
    $("fig-zoom-out").disabled = figureZoom <= 0.5;
    $("fig-zoom-in").disabled = figureZoom >= 3;
  }

  function openModal(file) {
    const f = FIG_INDEX[file];
    if (!f) return;
    $("fig-modal-title").textContent = f.title;
    const img = $("fig-modal-img");
    img.src = "figures/" + f.file;
    img.alt = f.title;
    $("fig-modal-caption").textContent = f.caption;
    setFigureZoom(1);
    $("fig-zoom-viewport").scrollTo(0, 0);
    $("fig-modal").classList.add("open");
  }

  function closeModal() {
    $("fig-modal").classList.remove("open");
    $("fig-modal-img").src = "";
    setFigureZoom(1);
  }

  function closeThematicMenu() {
    $("thematic-nav").classList.remove("open");
    $("thematic-toggle").setAttribute("aria-expanded", "false");
    $("thematic-menu").hidden = true;
  }

  // The "Countries" nav tab holds two panes (Country landscape / Country
  // profile) switched by the sub-tabs at the top of each pane.
  function showCountryView(view) {
    const pane = view === "profile" ? "country" : "landscape";
    for (const button of document.querySelectorAll("[data-country-view]")) {
      const active = button.dataset.countryView === view;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    }
    switchTab(pane);
  }

  function switchTab(name) {
    if (name === "countries") {
      showCountryView("landscape");
      return;
    }
    if (name !== "gallery") closeThematicMenu();
    const navName = (name === "landscape" || name === "country") ? "countries" : name;
    for (const b of document.querySelectorAll(".navbar .nav-link")) {
      b.classList.toggle("active", b.dataset.tab === navName);
    }
    for (const p of document.querySelectorAll(".tab-pane")) {
      p.classList.toggle("active", p.id === "pane-" + name);
    }
    if (name === "overview" && window.Plotly && $("ov-trend").data) {
      window.Plotly.Plots.resize($("ov-trend"));
    }
    if (name === "explorer" && state.result) {
      for (const id of ["x-trend", "x-map", "x-comp", "x-scatter"]) {
        if (window.Plotly && $(id).data) window.Plotly.Plots.resize($(id));
      }
    }
    if (name === "country" && window.Plotly) {
      for (const id of ["c-trend", "c-mix", "c-methods", "c-signals", "c-benchmark"]) {
        if ($(id).data) window.Plotly.Plots.resize($(id));
      }
    }
    if (name === "landscape") {
      // Build the picker on first activation, while the pane is visible.
      // TomSelect measures the control when it is constructed; building it
      // while #pane-landscape is display:none yields a zero-width dropdown
      // that never opens.
      if (!landSelect) setupLandscapePicker();
      if (window.Plotly) {
        for (const id of ["land-scatter", "land-eval-mix", "land-disease-mix", "land-cross-heatmap"]) {
          if ($(id).data) window.Plotly.Plots.resize($(id));
        }
      }
    }
  }

  function sectionIndex(title) {
    return GALLERY.findIndex(sec => sec.title === title);
  }

  // Opens a Thematic analysis section from the Overview; its back link
  // returns to the Overview.
  function openOverviewTheme(title) {
    const i = sectionIndex(title);
    if (i < 0) return;
    switchTab("gallery");
    showSection(i, "overview");
  }

  // Where each Overview "at a glance" tile leads (keyed by content.json label).
  const TILE_ACTIONS = {
    "Eligible full evaluations": () => openOverviewTheme("Size & growth"),
    "Years covered": () => showOverviewTrend("cumulative"),
    "Countries studied": () => openOverviewTheme("Geography & authorship"),
    "Journals": () => openOverviewTheme("Open access & funding"),
    "Use QALYs": () => openOverviewTheme("Methods & metrics"),
    "Model-based": () => openOverviewTheme("Methods & metrics"),
    "Single-country studies": () => openOverviewTheme("Geography & authorship")
  };

  function makeOverviewCardInteractive(box, label) {
    const action = TILE_ACTIONS[label];
    if (!action) return;
    box.classList.add("overview-nav-card");
    box.tabIndex = 0;
    box.setAttribute("role", "link");
    box.setAttribute("aria-label", label + ": open related analysis");
    box.addEventListener("click", action);
    box.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        action();
      }
    });
  }

  function renderOverview() {
    const m = db.dict.meta;
    const built = $("nav-built");
    if (built) built.textContent = "bundle " + m.built;

    // Hero paragraph: ordered segments from content.json (§15.2). Each segment
    // becomes a <span>/<strong>/<em> filled via textContent — no innerHTML.
    // HTML whitespace collapsing turns the source newlines/indent into spaces.
    const hero = $("ov-hero");
    hero.textContent = "";
    for (const seg of db.content.hero) {
      const node = document.createElement(seg.strong ? "strong" : seg.em ? "em" : "span");
      node.textContent = seg.text;
      hero.appendChild(node);
    }

    // Glance tiles: final formatted strings from content.json (§15.3);
    // sub === null means no footer line.
    const wrap = $("ov-tiles");
    wrap.textContent = "";
    for (const t of db.content.glance_tiles) {
      const box = el("div", "value-box");
      const title = el("div", "value-box-title");
      title.textContent = t.label;
      const value = el("div", "value-box-value");
      value.textContent = t.value;
      box.appendChild(title);
      box.appendChild(value);
      if (t.sub != null) {
        const sub = el("div", "value-box-sub");
        sub.textContent = t.sub;
        box.appendChild(sub);
      }
      makeOverviewCardInteractive(box, t.label);
      wrap.appendChild(box);
    }

    // Overview figure cards: header = the figure's content.json title, with a
    // "More on …" link to the Thematic analysis section that holds it.
    const heroes = [
      { file: "fig_dotmap.webp", alt: "Global dot map" },
      { file: "fig_burden.webp", alt: "Evidence vs burden" },
      { file: "fig_transition.webp", alt: "Epidemiological transition" }
    ];
    const hw = $("ov-hero-imgs");
    hw.textContent = "";
    heroes.forEach((h, i) => {
      const f = FIG_INDEX[h.file];
      const card = el("div", "card overview-analysis-card");
      // An odd last card spans the full row.
      if (heroes.length % 2 === 1 && i === heroes.length - 1) {
        card.classList.add("overview-analysis-card-wide");
      }
      const head = el("div", "card-header overview-card-head");
      const name = el("span");
      name.textContent = f ? f.title : h.alt;
      head.appendChild(name);
      if (f && f.sectionTitle) {
        const link = el("button", "card-header-link");
        link.type = "button";
        link.textContent = "More on " + f.sectionTitle.toLowerCase() + " →";
        link.addEventListener("click", () => openOverviewTheme(f.sectionTitle));
        head.appendChild(link);
      }
      const body = el("div", "card-body overview-analysis-body");
      const btn = el("button", "overview-figure-button");
      btn.type = "button";
      btn.setAttribute("aria-label", "Open figure: " + (f ? f.title : h.alt));
      const img = el("img", "overview-analysis-figure");
      img.src = "figures/" + h.file;
      img.alt = h.alt;
      img.loading = "lazy";
      btn.appendChild(img);
      btn.addEventListener("click", () => openModal(h.file));
      body.appendChild(btn);
      card.appendChild(head);
      card.appendChild(body);
      hw.appendChild(card);
    });
  }

  // Overview publication trend for the unfiltered corpus, with a
  // "Per year | Cumulative" switch.
  let overviewTrendMode = "annual";

  function showOverviewTrend(mode) {
    switchTab("overview");
    setOverviewTrendMode(mode);
    document.querySelector(".overview-trend-card").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function setOverviewTrendMode(mode) {
    overviewTrendMode = mode;
    for (const b of document.querySelectorAll("[data-trend-mode]")) {
      const on = b.dataset.trendMode === mode;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", String(on));
    }
    renderOverviewTrend();
  }

  function renderOverviewTrend() {
    const ser = trendSeries(db, applyFilters(db, {}), "none");
    const years = Object.keys(ser).map(Number).sort((a, b) => a - b);
    const annual = years.map(y => ser[y]);
    const cumulative = overviewTrendMode === "cumulative";
    let running = 0;
    const y = cumulative ? annual.map(n => (running += n)) : annual;
    // Light-to-strong blue across the years for the markers.
    const lerp = (a, b, t) => Math.round(a + (b - a) * t);
    const span = Math.max(1, years[years.length - 1] - years[0]);
    const markerColors = years.map(yr => {
      const t = (yr - years[0]) / span;
      return `rgb(${lerp(126, 26, t)},${lerp(166, 78, t)},${lerp(212, 138, t)})`;
    });
    window.Plotly.react("ov-trend", [{
      x: years, y,
      mode: "lines+markers", type: "scatter", showlegend: false,
      line: { color: ACCENT, width: 3, shape: "spline", smoothing: 0.45 },
      marker: { color: markerColors, size: 7, line: { color: "white", width: 1 } },
      fill: "tozeroy", fillcolor: "rgba(31,95,168,.12)",
      hovertemplate: (cumulative ? "By %{x}" : "%{x}") + ": %{y:,} studies<extra></extra>"
    }], {
      font: BASE_FONT,
      margin: { t: 10, b: 40, l: 60, r: 20 },
      xaxis: { showgrid: false, range: [years[0] - 0.4, years[years.length - 1] + 0.4], dtick: 2 },
      yaxis: { title: cumulative ? "cumulative studies" : "studies", tickformat: ",d",
               gridcolor: "#eeebe3", zeroline: false, rangemode: "tozero" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  // Thematic analysis index: one card per content.json gallery section, plus
  // the matching entries in the navbar dropdown.
  function renderGalleryIndex() {
    const idx = $("gal-section-index");
    const menu = $("thematic-menu");
    idx.textContent = "";
    menu.textContent = "";
    GALLERY.forEach((sec, i) => {
      const card = el("button", "thematic-card");
      card.type = "button";
      const img = el("img", "thematic-card-image");
      img.src = "figures/" + sec.figs[0].file;
      img.alt = "";
      img.loading = "lazy";
      const body = el("div", "thematic-card-body");
      const title = el("h2", "thematic-card-title");
      title.textContent = sec.title;
      const count = el("div", "thematic-card-count");
      count.textContent = sec.figs.length + " figures";
      const description = el("p", "thematic-card-description");
      const fullBlurb = sec.blurb.replace(/\s+/g, " ").trim();
      description.textContent = fullBlurb.length > 155 ? fullBlurb.slice(0, 152) + "..." : fullBlurb;
      const arrow = el("span", "thematic-card-arrow");
      arrow.textContent = "→";
      arrow.setAttribute("aria-hidden", "true");
      body.append(title, count, description, arrow);
      card.append(img, body);
      card.addEventListener("click", () => showSection(i));
      idx.appendChild(card);

      const item = el("button", "nav-theme-link");
      item.type = "button";
      item.setAttribute("role", "menuitem");
      item.textContent = sec.title;
      item.addEventListener("click", () => {
        closeThematicMenu();
        switchTab("gallery");
        showSection(i);
      });
      menu.appendChild(item);
    });
  }

  // Where the section's back link leads: null = theme index, "overview" =
  // back to the Overview.
  let sectionReturnTo = null;

  // Figures drawn at least this many pixels wide span two grid columns.
  const WIDE_FIGURE_MIN_PX = 2300;

  function showSection(i, returnTo = null) {
    const sec = GALLERY[i];
    sectionReturnTo = returnTo;
    $("gal-back").innerHTML = returnTo === "overview" ? "&larr; Back to Overview" : "&larr; All themes";
    $("gal-index").style.display = "none";
    $("gal-section").style.display = "block";
    $("gal-sec-title").textContent = sec.title;
    $("gal-sec-blurb").textContent = sec.blurb.replace(/\s+/g, " ").trim();
    const grid = $("gal-sec-grid");
    grid.textContent = "";
    grid.classList.toggle("fig-grid-single", sec.figs.length === 1);
    for (const f of sec.figs) {
      const card = el("div", "fig-card");
      const img = el("img");
      img.src = "figures/" + f.file;
      img.alt = f.title;
      img.loading = "lazy";
      img.addEventListener("click", () => openModal(f.file));
      img.addEventListener("load", () => {
        card.classList.toggle("fig-card-wide", img.naturalWidth >= WIDE_FIGURE_MIN_PX);
      }, { once: true });
      card.appendChild(img);
      const body = el("div", "fig-body");
      const ft = el("div", "fig-title");
      ft.textContent = f.title;
      const fc = el("div", "fig-caption");
      fc.textContent = f.caption.replace(/\s+/g, " ").trim();
      body.appendChild(ft);
      body.appendChild(fc);
      card.appendChild(body);
      grid.appendChild(card);
    }
    window.scrollTo(0, 0);
  }

  function hideSection() {
    $("gal-section").style.display = "none";
    $("gal-index").style.display = "block";
    sectionReturnTo = null;
    $("gal-back").innerHTML = "&larr; All themes";
  }

  function goBackFromSection() {
    const toOverview = sectionReturnTo === "overview";
    hideSection();
    if (toOverview) {
      switchTab("overview");
      $("ov-tiles").scrollIntoView({ block: "center" });
    } else {
      window.scrollTo(0, 0);
    }
  }

  function makeRadios(containerId, name, choices) {
    const c = $(containerId);
    c.textContent = "";
    choices.forEach((ch, i) => {
      const lab = el("label");
      const inp = el("input");
      inp.type = "radio";
      inp.name = name;
      inp.value = ch;
      inp.checked = i === 0;
      inp.addEventListener("change", () => {
        state.filt[name.slice(2)] = ch;
        refreshExplorer();
      });
      lab.appendChild(inp);
      lab.appendChild(document.createTextNode(ch));
      c.appendChild(lab);
    });
  }

  function makeMultiSelect(id, options, placeholder, key) {
    const sel = $(id);
    for (const o of options) {
      const opt = document.createElement("option");
      opt.value = o;
      opt.textContent = o;
      sel.appendChild(opt);
    }
    state.ts[key] = new window.TomSelect(sel, {
      plugins: ["remove_button"],
      placeholder: placeholder,
      allowEmptyOption: false,
      onChange: vals => {
        state.filt[key] = Array.isArray(vals) ? vals.slice() : (vals ? [vals] : []);
        refreshExplorer();
      }
    });
  }

  function setupExplorerControls() {
    const m = db.dict.meta;
    state.filt = {
      years: db.years.slice(),
      income: [], region: [], disease: [], evaltype: [], design: [],
      model: "All", qaly: "All", oa: "All", scope: "All"
    };

    const slider = $("x-years");
    window.noUiSlider.create(slider, {
      start: db.years,
      connect: true,
      step: 1,
      range: { min: db.years[0], max: db.years[1] }
    });
    const readout = $("x-years-readout");
    const setReadout = () => {
      readout.textContent = state.filt.years[0] + " – " + state.filt.years[1];
    };
    setReadout();
    const debouncedYears = debounce(() => refreshExplorer(), 250);
    slider.noUiSlider.on("update", (values) => {
      state.filt.years = [Math.round(+values[0]), Math.round(+values[1])];
      setReadout();
      debouncedYears();
    });

    makeMultiSelect("x-income", db.incOrder, "All groups", "income");
    makeMultiSelect("x-region", db.dict.REGIONS, "All regions", "region");
    makeMultiSelect("x-disease", db.disease_grps, "All areas", "disease");
    makeMultiSelect("x-evaltype", db.levels.econ_eval_type, "All types", "evaltype");
    makeMultiSelect("x-design", db.levels.design_basis, "All designs", "design");

    makeRadios("x-model", "x_model", ["All", "Model-based", "Measured"]);
    makeRadios("x-qaly", "x_qaly", ["All", "Uses QALY", "No QALY"]);
    makeRadios("x-oa", "x_oa", ["All", "Open access", "Not open"]);

    const scope = $("x-scope");
    fillSelect(scope, ["All"].concat(db.levels.geo_scope));
    scope.addEventListener("change", () => {
      state.filt.scope = scope.value;
      refreshExplorer();
    });

    $("x-reset").addEventListener("click", () => {
      slider.noUiSlider.set(db.years);
      for (const k of ["income", "region", "disease", "evaltype", "design"]) state.ts[k].clear();
      for (const [cont, name] of [["x-model", "model"], ["x-qaly", "qaly"], ["x-oa", "oa"]]) {
        const first = $(cont).querySelector("input");
        first.checked = true;
        state.filt[name] = "All";
      }
      scope.value = "All";
      state.filt.scope = "All";
      state.filt.years = db.years.slice();
      setReadout();
      refreshExplorer();
    });

    const REG = db.registries;
    fillSelect($("x-trend-by"), [...REG.TREND_VARS.keys()], ["Income group"]);
    fillSelect($("x-map-metric"), [...REG.MAP_METRICS.keys()], ["Studies"]);
    fillSelect($("x-comp-var"), [...REG.COMP_VARS.keys()], ["Evaluation type"]);
    fillSelect($("x-comp-stack"), [...REG.STACK_VARS.keys()], ["None"]);
    const compMode = $("x-comp-mode");
    compMode.textContent = "";
    for (const [lab, val] of [["Count", "n"], ["Share (%)", "pct"]]) {
      const o = document.createElement("option");
      o.value = val;
      o.textContent = lab;
      compMode.appendChild(o);
    }
    fillSelect($("x-scatter-x"), [...REG.SCAT_X.keys()], ["Total DALYs (GBD 2023)"]);
    fillSelect($("x-scatter-y"), [...REG.SCAT_Y.keys()], ["Studies per 100k DALYs"]);

    $("x-trend-by").addEventListener("change", renderTrend);
    $("x-map-metric").addEventListener("change", renderMap);
    $("x-comp-var").addEventListener("change", renderComp);
    $("x-comp-stack").addEventListener("change", renderComp);
    $("x-comp-mode").addEventListener("change", renderComp);
    $("x-scatter-x").addEventListener("change", renderScatter);
    $("x-scatter-y").addEventListener("change", renderScatter);
  }

  function refreshExplorer() {
    state.result = applyFilters(db, state.filt);
    renderValueBoxes();
    renderTrend();
    renderMap();
    renderComp();
    renderScatter();
    renderTable();
  }

  function renderValueBoxes() {
    const v = valueBoxes(db, state.result);
    $("v-studies").textContent = fmtNum(v.v_studies);
    $("v-countries").textContent = fmtNum(v.v_countries);
    $("v-model").textContent = v.v_model_pct == null ? "—" : v.v_model_pct + "%";
    $("v-qaly").textContent = v.v_qaly_pct == null ? "—" : v.v_qaly_pct + "%";
  }

  function hLegend(y) {
    return { orientation: "h", y: y, x: 0 };
  }

  function renderTrend() {
    const label = $("x-trend-by").value;
    const v = db.registries.TREND_VARS.get(label);
    const ser = trendSeries(db, state.result, v);
    const years = Object.keys(ser).map(Number);
    let traces;
    if (v === "none") {
      traces = [{
        x: years, y: years.map(y => ser[y]),
        mode: "lines", type: "scatter",
        line: { color: ACCENT, width: 3 },
        name: "studies", hovertemplate: "%{x}: %{y} studies<extra></extra>"
      }];
    } else {
      let cats;
      let colorMap = null;
      if (v === "income") {
        cats = db.incLv.slice();
        colorMap = db.palInc;
      } else if (v === "un_region") {
        cats = [...new Set(years.flatMap(y => Object.keys(ser[y])))].sort();
      } else {
        const lv = db.levels[v];
        if (v === "oa_label") {
          cats = lv.slice();
          colorMap = OA_COLORS;
        } else {
          cats = [...new Set(years.flatMap(y => Object.keys(ser[y])))].sort();
        }
      }
      traces = cats.map(cat => ({
        x: years,
        y: years.map(y => (ser[y] && ser[y][cat] != null) ? ser[y][cat] : null),
        mode: "lines", type: "scatter",
        name: cat,
        connectgaps: false,
        line: { width: 2.4, color: colorMap ? colorMap[cat] : undefined },
        // cat comes from dict levels (developer-curated); escaped anyway —
        // Plotly renders hovertemplate output as HTML.
        hovertemplate: "%{x} · " + esc(cat) + ": %{y} studies<extra></extra>"
      }));
    }
    window.Plotly.react("x-trend", traces, {
      font: BASE_FONT,
      margin: { t: 20, b: 60, l: 60, r: 20 },
      legend: hLegend(-0.18),
      xaxis: { title: null, gridcolor: "#eeebe3" },
      yaxis: { title: "studies", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function renderMap() {
    const label = $("x-map-metric").value;
    const m = db.registries.MAP_METRICS.get(label);
    const rows = state.result.byCountry;
    const isCounts = m === "studies";
    const z = rows.map(r => isCounts ? Math.log10(r.studies + 1) : r[m]);
    // Plotly renders hover text as HTML — country names are data-derived and
    // must be escaped before concatenation.
    const text = rows.map(r => isCounts
      ? esc(r.country) + "<br>" + fmtNum(r.studies) + " studies"
      : esc(r.country) + "<br>" + fmtNum(r.studies) + " studies<br>" +
        (r[m] == null ? "NA" : rRound(r[m], 2)) + " " + esc(label.toLowerCase()));
    const colorscale = isCounts
      ? [[0, "#f1f3f5"], [0.0001, SOFT_RAMP[0]]].concat(SOFT_RAMP.slice(1).map((c, i) => [(i + 1) / (SOFT_RAMP.length - 1), c]))
      : SOFT_RAMP.map((c, i) => [i / (SOFT_RAMP.length - 1), c]);
    const colorbar = isCounts
      ? {
          title: "studies<br>(log)",
          tickvals: [0, 1, 10, 100, 1000].map(x => Math.log10(x + 1)),
          ticktext: ["0", "1", "10", "100", "1000"],
          thickness: 12, len: 0.8
        }
      : { title: label.split(" ").join("<br>"), thickness: 12, len: 0.8 };
    window.Plotly.react("x-map", [{
      type: "choropleth",
      locations: rows.map(r => r.iso3),
      z: z,
      text: text,
      hoverinfo: "text",
      colorscale: colorscale,
      marker: { line: { color: "#ffffff", width: 0.3 } },
      colorbar: colorbar
    }], {
      font: BASE_FONT,
      geo: {
        projection: { type: "robinson" },
        showframe: false,
        showcoastlines: false,
        bgcolor: "rgba(0,0,0,0)"
      },
      margin: { t: 0, b: 0, l: 0, r: 0 }
    }, PLOTLY_CFG);
  }

  function renderComp() {
    const label = $("x-comp-var").value;
    const xv = db.registries.COMP_VARS.get(label);
    const sv = db.registries.STACK_VARS.get($("x-comp-stack").value);
    const mode = $("x-comp-mode").value;
    const res = compCounts(db, state.result, xv, sv, mode);
    const note = xv === "grp" ? " · a study can sit in several disease groups" : "";
    const annotation = {
      text: label + note, xref: "paper", yref: "paper",
      x: 0, y: 1.06, xanchor: "left", showarrow: false,
      font: { size: 11, color: "#6b7280" }
    };
    const oaNote = $("x-comp-oa-note");
    oaNote.hidden = !res.knownOaOnly;
    oaNote.textContent = res.knownOaOnly
      ? "Percentages use studies with known open-access status; " + fmtNum(res.excludedUnknown) +
        " unknown-status studies are excluded. Switch to Count to see unknowns." : "";
    let traces, layout;
    if (res.type === "simple") {
      const desc = res.rows;
      const bottomUp = desc.slice().reverse();
      const maxV = Math.max(1, ...desc.map(r => r.v));
      traces = [{
        type: "bar", orientation: "h",
        y: desc.map(r => r.x),
        x: desc.map(r => r.v),
        marker: { color: desc.map(r => rampColor(0.15 + 0.85 * Math.sqrt(r.v / maxV))) },
        hovertemplate: "%{y}: %{x}<extra></extra>"
      }];
      layout = {
        yaxis: {
          categoryorder: "array",
          categoryarray: bottomUp.map(r => r.x),
          automargin: true
        },
        xaxis: {
          title: res.pct ? (res.knownOaOnly ? "share with known open-access status (%)" : "share of filtered studies (%)") : "studies",
          gridcolor: "#eeebe3",
          ticksuffix: res.pct ? "%" : ""
        }
      };
    } else {
      const bottomUp = res.catOrder.slice().reverse();
      traces = res.stacks.map(k => ({
        type: "bar", orientation: "h",
        name: k,
        y: res.catOrder,
        x: res.catOrder.map(c => res.values[c][k] != null ? res.values[c][k] : 0),
        // k comes from dict levels (developer-curated); escaped anyway —
        // Plotly renders hovertemplate output as HTML.
        hovertemplate: "%{y} · " + esc(k) + ": %{x}<extra></extra>"
      }));
      layout = {
        barmode: "stack",
        yaxis: {
          categoryorder: "array",
          categoryarray: bottomUp,
          automargin: true
        },
        xaxis: {
          title: res.pct ? (res.knownOaOnly ? "share within category, known OA status (%)" : "share within category (%)") : "studies",
          gridcolor: "#eeebe3",
          range: res.pct ? [0, 100] : undefined,
          ticksuffix: res.pct ? "%" : ""
        }
      };
    }
    window.Plotly.react("x-comp", traces, Object.assign({
      font: BASE_FONT,
      margin: { t: 30, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)",
      annotations: [annotation]
    }, layout), PLOTLY_CFG);
  }

  function renderScatter() {
    const xLabel = $("x-scatter-x").value;
    const yLabel = $("x-scatter-y").value;
    const xv = db.registries.SCAT_X.get(xLabel);
    const yv = db.registries.SCAT_Y.get(yLabel);
    const pts = scatterPoints(db, state.result, xv, yv);
    const traces = db.incLv.map(inc => {
      const rows = pts.filter(r => r.income === inc);
      return {
        type: "scatter", mode: "markers",
        name: inc,
        x: rows.map(r => r[xv]),
        y: rows.map(r => r[yv]),
        // country names are data-derived; Plotly renders hover text as HTML.
        text: rows.map(r => esc(r.country) + "<br>" + fmtNum(r.studies) + " studies"),
        hoverinfo: "text",
        marker: { color: db.palInc[inc], size: 8, opacity: 0.75, line: { color: "white", width: 0.5 } }
      };
    });
    window.Plotly.react("x-scatter", traces, {
      font: BASE_FONT,
      margin: { t: 20, b: 70, l: 70, r: 20 },
      legend: hLegend(-0.2),
      xaxis: { type: "log", title: xLabel + " (log)", gridcolor: "#eeebe3" },
      yaxis: { type: "log", title: yLabel + " (log)", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function renderTable() {
    const rows = tableRows(db, state.result, 25);
    const cols = ["Country", "Income", "Region", "Studies", "Per 100k DALYs", "Per US$1bn", "Per million"];
    const numCols = new Set(["Studies", "Per 100k DALYs", "Per US$1bn", "Per million"]);
    // Country/Income/Region cells are data-derived strings: build the table
    // with createElement + textContent — never innerHTML string concat.
    const tbl = $("x-table");
    tbl.textContent = "";
    const thead = document.createElement("thead");
    const htr = document.createElement("tr");
    for (const c of cols) {
      const th = document.createElement("th");
      if (numCols.has(c)) th.className = "num";
      th.textContent = c;
      htr.appendChild(th);
    }
    thead.appendChild(htr);
    tbl.appendChild(thead);
    const tbody = document.createElement("tbody");
    for (const r of rows) {
      const tr = document.createElement("tr");
      for (const c of cols) {
        const v = r[c];
        const td = document.createElement("td");
        if (numCols.has(c)) td.className = "num";
        td.textContent = v == null ? "" : (c === "Studies" ? fmtNum(v) : String(v));
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    tbl.appendChild(tbody);
  }

  function setupCountryPane() {
    const sel = $("c-picker");
    for (const r of db.countries) {
      const o = document.createElement("option");
      o.value = r.iso3;
      o.textContent = r.country;
      if (r.iso3 === "IND") o.selected = true;
      sel.appendChild(o);
    }
    new window.TomSelect(sel, {
      placeholder: "Pick a country…",
      onChange: val => {
        if (!val) return;
        state.country = val;
        renderCountryAll();
      }
    });
    renderCountryAll();
  }

  function renderCountryAll() {
    const iso3 = state.country;
    const prof = countryProfile(db, iso3);
    if (!prof) return;

    const facts = $("c-facts");
    facts.textContent = "";
    // Fact keys/values are data-derived (country names, region names,
    // formatted numbers) — textContent only, never el()'s innerHTML path.
    for (const [k, v] of countryFacts(db, iso3)) {
      const dt = el("dt");
      dt.textContent = k;
      const dd = el("dd");
      dd.textContent = String(v);
      facts.appendChild(dt);
      facts.appendChild(dd);
    }

    $("c-n").textContent = fmtNum(prof.c_n);
    $("c-daly").textContent = prof.c_daly == null ? "no burden data"
      : rRound(prof.c_daly, 2) + "  (median " + rRound(prof.medians.m_daly, 2) + ")";
    $("c-spend").textContent = prof.c_spend == null ? "no spending data"
      : rRound(prof.c_spend, 2) + "  (median " + rRound(prof.medians.m_bn, 2) + ")";
    $("c-percap").textContent = rRound(prof.c_percap, 2) + "  (median " + rRound(prof.medians.m_mil, 2) + ")";

    const ct = prof.c_trend;
    const cYears = Object.keys(ct.country).map(Number);
    const pYears = Object.keys(ct.peer).map(Number);
    window.Plotly.react("c-trend", [
      {
        x: cYears, y: cYears.map(y => ct.country[y]),
        mode: "lines", type: "scatter", name: "country",
        line: { color: "#1f659f", width: 3 },
        hovertemplate: "%{x}: %{y} studies<extra>country</extra>"
      },
      {
        x: pYears, y: pYears.map(y => ct.peer[y]),
        mode: "lines", type: "scatter", name: "income-group mean",
        line: { color: "#88a6b8", width: 2.5, dash: "dash" },
        hovertemplate: "%{x}: %{y:.2f} per country<extra>income-group mean</extra>"
      }
    ], {
      font: BASE_FONT,
      margin: { t: 20, b: 60, l: 60, r: 20 },
      legend: hLegend(-0.18),
      xaxis: { gridcolor: "#eeebe3" },
      yaxis: { title: "studies per year", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    const mix = prof.c_mix;
    const grps = [...new Set([...Object.keys(mix.country), ...Object.keys(mix.peer)])];
    const meanShare = g => {
      const vals = [];
      if (mix.country[g] != null) vals.push(mix.country[g]);
      if (mix.peer[g] != null) vals.push(mix.peer[g]);
      return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
    };
    grps.sort((a, b) => meanShare(a) - meanShare(b));
    window.Plotly.react("c-mix", [
      {
        type: "bar", orientation: "h", name: "country",
        y: grps, x: grps.map(g => mix.country[g] != null ? mix.country[g] : null),
        marker: { color: spreadPalette(PROFILE_BLUE, grps.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: grps, x: grps.map(g => mix.peer[g] != null ? mix.peer[g] : null),
        marker: { color: spreadPalette(PROFILE_PEER, grps.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>income group</extra>"
      }
    ], {
      barmode: "group",
      font: BASE_FONT,
      margin: { t: 10, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      xaxis: { title: "share of disease-coded studies (%)", gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: grps, automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    // Evaluation-method mix (§11.2). y_order = peer-share desc (ties alphabetical
    // asc). ggplot renders factor level 1 at the BOTTOM ("no display reversal"), so
    // the top-ranked type sits at the bottom of the chart. Plotly's categoryarray
    // also places its FIRST entry at the BOTTOM of a horizontal-bar y axis, so
    // categoryarray = y_order AS-IS reproduces the ggplot display exactly: reading
    // the chart top→bottom the types appear in REVERSE y_order (peer share ascending).
    const meth = prof.c_methods;
    const yOrder = meth.y_order;
    const methVal = (side, t) => meth[t] && meth[t][side] != null ? meth[t][side] : null;
    window.Plotly.react("c-methods", [
      {
        type: "bar", orientation: "h", name: "country",
        y: yOrder, x: yOrder.map(t => methVal("country_share", t)),
        marker: { color: spreadPalette(PROFILE_TEAL, yOrder.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: yOrder, x: yOrder.map(t => methVal("peer_share", t)),
        marker: { color: spreadPalette(PROFILE_PEER, yOrder.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>income group</extra>"
      }
    ], {
      barmode: "group",
      font: BASE_FONT,
      margin: { t: 10, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      xaxis: { title: "share of studies (%)", gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: yOrder, automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    // Approach & reporting (§11.3). Fixed metric order Model-based → Open access;
    // ggplot uses levels = rev(metrics) so Model-based renders ON TOP and Open
    // access at the bottom. Plotly categoryarray first entry = bottom, so the
    // category array is the listed order reversed. A null pct (empty OA-known
    // subset) leaves that series' bar omitted.
    const sig = prof.c_signals;
    const sigCats = db.registries.SIGNAL_METRICS.slice().reverse();
    const sigVal = (side, m) => sig[m] && sig[m][side] != null ? sig[m][side] : null;
    window.Plotly.react("c-signals", [
      {
        type: "bar", orientation: "h", name: "country",
        y: sigCats, x: sigCats.map(m => sigVal("country_pct", m)),
        marker: { color: spreadPalette(PROFILE_LAVENDER, sigCats.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: sigCats, x: sigCats.map(m => sigVal("peer_pct", m)),
        marker: { color: spreadPalette(PROFILE_PEER, sigCats.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>income group</extra>"
      }
    ], {
      barmode: "group",
      font: BASE_FONT,
      margin: { t: 10, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      xaxis: { title: "% of studies", gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: sigCats, automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    // Peer benchmark (§11.4): log10×log10 scatter of the filtered income-group
    // rows; peers grey-blue, selected country gold, dashed type-7 median line with
    // a muted annotation. Rows without usable burden are visibly absent.
    const bm = prof.c_benchmark;
    // country names are data-derived; Plotly renders hover text as HTML.
    const hoverOf = x => esc(x.country) + " — " + fmtNum(x.studies) + " studies — " +
      rRound(x.per100k, 2) + " per 100k DALYs";
    const bmPeers = bm.rows.filter(x => x.iso3 !== prof.iso3);
    const bmSel = bm.rows.filter(x => x.iso3 === prof.iso3);
    const bmLayout = {
      font: BASE_FONT,
      margin: { t: 20, b: 60, l: 70, r: 20 },
      xaxis: { type: "log", title: "Total disease burden (DALYs, 2023, log)", gridcolor: "#eeebe3" },
      yaxis: { type: "log", title: "Studies per 100k DALYs (log)", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    };
    if (bm.median_per100k != null) {
      bmLayout.shapes = [{
        type: "line", xref: "paper", x0: 0, x1: 1,
        yref: "y", y0: bm.median_per100k, y1: bm.median_per100k,
        line: { color: "#b08d3e", width: 1.25, dash: "dash" }
      }];
      bmLayout.annotations = [{
        text: "income-group median", xref: "paper", x: 0.99, xanchor: "right",
        yref: "y", y: bm.median_per100k, yanchor: "bottom", showarrow: false,
        font: { size: 10, color: "#8f702d" }
      }];
    }
    window.Plotly.react("c-benchmark", [
      {
        type: "scatter", mode: "markers", name: "income group", showlegend: false,
        x: bmPeers.map(x => x.dalys), y: bmPeers.map(x => x.per100k),
        text: bmPeers.map(hoverOf), hoverinfo: "text",
        marker: { color: "#9fb7c8", size: 9, opacity: 0.72, line: { color: "white", width: 0.5 } }
      },
      {
        type: "scatter", mode: "markers", name: "country", showlegend: false,
        x: bmSel.map(x => x.dalys), y: bmSel.map(x => x.per100k),
        text: bmSel.map(hoverOf), hoverinfo: "text",
        marker: { color: "#2f9b92", size: 15, line: { color: "#ffffff", width: 1.2 } }
      }
    ], bmLayout, PLOTLY_CFG);
  }

  // ---- Country landscape tab ------------------------------------------------

  // Lazy per-country drill shard (§16.1/§16.2). Missing files (zero-study
  // countries such as MUS/ERI) resolve to null instead of throwing.
  async function loadDrill(iso3) {
    if (drillCache[iso3]) return drillCache[iso3];
    try {
      const r = await fetch("data/drill/" + iso3 + ".json?v=" + BUILD);
      if (!r.ok) return null;
      const payload = await r.json();
      drillCache[iso3] = payload;
      db.drill = db.drill || {};
      db.drill[iso3] = payload;
      return payload;
    } catch (e) {
      return null;
    }
  }

  function setupLandscapePicker() {
    const sel = $("land-country");
    for (const r of landscapeCountries(db)) {
      const o = document.createElement("option");
      o.value = r.iso3;
      o.textContent = r.country;
      sel.appendChild(o);
    }
    landSelect = new window.TomSelect(sel, {
      placeholder: "Pick a country…",
      // Render the list in <body> so card/tab overflow cannot clip it.
      dropdownParent: "body",
      onChange: val => { if (val) showCountryMix(val); }
    });
    if (landCrossIndex) landSelect.setValue(landCrossIndex.iso3, true);
  }

  function renderLandscape() {
    renderLandscapeScatter();
    // Seed the mix panels with the most-studied country so the tab never
    // opens empty (§2.6).
    let seed = null, best = -1;
    for (const r of db.countries) {
      if (r.studies > best) { best = r.studies; seed = r.iso3; }
    }
    if (seed) showCountryMix(seed);
  }

  function renderLandscapeScatter() {
    const pts = landscapePoints(db);
    const maxS = pts.reduce((a, p) => Math.max(a, p.studies), 1);
    const traces = db.incLv.map(inc => {
      const rows = pts.filter(p => p.income === inc);
      return {
        type: "scatter", mode: "markers", name: inc,
        x: rows.map(p => p.dalys),
        y: rows.map(p => p.spend_per_person),
        customdata: rows.map(p => p.iso3),
        // country names and formatted numbers are data-derived; Plotly renders
        // hover text as HTML, so names pass through esc().
        text: rows.map(p => {
          let t = esc(p.country) + "<br>" + fmtNum(p.studies) + " studies<br>" +
            "US$" + rRound(p.spend_per_person, 2) + " spending per person";
          t += "<br>" + rRound(p.per100k, 2) + " per 100k DALYs";
          if (p.per_bn != null) t += "<br>" + rRound(p.per_bn, 2) + " per US$1bn";
          return t;
        }),
        hoverinfo: "text",
        marker: {
          color: db.palInc[inc], opacity: 0.78,
          size: rows.map(p => 6 + 30 * Math.sqrt(p.studies / maxS)),
          line: { color: "rgba(255,255,255,.9)", width: 0.8 }
        }
      };
    });
    window.Plotly.react("land-scatter", traces, {
      font: BASE_FONT,
      margin: { t: 20, b: 70, l: 70, r: 20 },
      legend: hLegend(-0.16),
      xaxis: { type: "log", title: "Total disease burden (DALYs, 2023, log)", gridcolor: "#eeebe3" },
      yaxis: { type: "log", title: "Health spending per person (US$, log)", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
    const div = $("land-scatter");
    if (!div._mixClickBound) {
      div._mixClickBound = true;
      div.on("plotly_click", ev => {
        const p = ev.points && ev.points[0];
        if (!p || !p.customdata) return;
        showCountryMix(p.customdata);
      });
    }
  }

  function renderMixBar(id, rows, xTitle, colors) {
    const desc = rows.slice();
    const bottomUp = desc.slice().reverse();
    window.Plotly.react(id, [{
      type: "bar", orientation: "h",
      y: desc.map(r => r.label),
      x: desc.map(r => r.count),
      // Largest bar strongest: the ramp runs light→strong bottom-up.
      marker: {
        color: spreadPalette(colors, desc.length).reverse(),
        line: { color: "rgba(255,255,255,.75)", width: 0.5 }
      },
      hovertemplate: "%{y}: %{x}<extra></extra>"
    }], {
      font: BASE_FONT,
      margin: { t: 20, b: 50, l: 175, r: 20 },
      xaxis: { title: xTitle, gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: bottomUp.map(r => r.label), automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function renderCrossHeatmap(mix) {
    const rows = mix.diseaseMix;
    const cols = mix.evalMix;
    const z = rows.map(d => cols.map(e => {
      const cell = mix.cross[d.code + "|" + e.code];
      return (cell && d.count > 0) ? 100 * cell.count / d.count : 0;
    }));
    const text = rows.map((d, i) => cols.map((e, j) => {
      const cell = mix.cross[d.code + "|" + e.code];
      return cell && cell.count > 0 ? rRound(z[i][j], 1) + "% (n=" + cell.count + ")" : "";
    }));
    const keys = rows.map(d => cols.map(e => d.code + "|" + e.code));
    window.Plotly.react("land-cross-heatmap", [{
      type: "heatmap",
      x: cols.map(e => e.label),
      y: rows.map(d => d.label),
      z,
      customdata: keys,
      text,
      hovertemplate: "%{y} × %{x}<br>%{text}<extra></extra>",
      colorscale: [
        [0, "#f5f3ee"],
        [0.25, "#d7e8e5"],
        [0.55, "#78b7ad"],
        [0.78, "#347f86"],
        [1, "#163b5c"]
      ],
      zmin: 0, zmax: 100,
      colorbar: { title: "row<br>share (%)", thickness: 12, len: 0.8 },
      xgap: 2, ygap: 2
    }], {
      font: BASE_FONT,
      margin: { t: 20, b: 80, l: 175, r: 20 },
      xaxis: { title: "evaluation type", automargin: true },
      yaxis: { title: "disease group", automargin: true, autorange: "reversed" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
    const div = $("land-cross-heatmap");
    if (!div._cellClickBound) {
      div._cellClickBound = true;
      div.on("plotly_click", ev => {
        const p = ev.points && ev.points[0];
        if (!p || !landCrossIndex) return;
        const cell = landCrossIndex.cross[p.customdata];
        if (!cell || cell.count === 0) return;
        openStudiesModal(landCrossIndex.iso3, cell.disease, cell.eval, cell.indices);
      });
    }
  }

  function showCountryMix(iso3) {
    const mix = countryMixes(db, iso3);
    if (!mix) return;
    $("land-eval-mix-title").textContent = mix.country + " — " + fmtNum(mix.n_studies) + " studies";
    $("land-disease-mix-title").textContent = mix.country;
    $("land-cross-title").textContent = mix.country;
    renderMixBar("land-eval-mix", mix.evalMix, "studies",
      ["#c9ddef", "#a8c8e3", "#7faed3", "#568fc0", "#356fa8", "#1f5fa8"]);
    renderMixBar("land-disease-mix", mix.diseaseMix, "disease-group rows",
      ["#d8ebe4", "#b5d9ca", "#86c2ad", "#55a88f", "#2f8b73", "#176b58"]);
    renderCrossHeatmap(mix);
    landCrossIndex = { iso3, cross: mix.cross };
    // Keep the picker in step when a bubble click selected the country.
    if (landSelect && landSelect.getValue() !== iso3) landSelect.setValue(iso3, true);
  }

  async function openStudiesModal(iso3, diseaseLabel, evalLabel, indices) {
    const rec = db.countries.find(r => r.iso3 === iso3);
    $("study-modal-title").textContent =
      (rec ? rec.country : iso3) + " — " + diseaseLabel + " × " + evalLabel;
    $("study-modal-count").textContent =
      fmtNum(indices.length) + (indices.length === 1 ? " study" : " studies");
    const list = $("study-modal-list");
    list.textContent = "";
    const loading = el("div", "study-item study-loading");
    loading.textContent = "Loading study texts…";
    list.appendChild(loading);
    $("study-modal").classList.add("open");

    const payload = await loadDrill(iso3);
    list.textContent = "";
    if (!payload) {
      const miss = el("div", "study-item");
      miss.textContent = "Study texts are not available for this country.";
      list.appendChild(miss);
      return;
    }
    for (const r of drillRecords(db, iso3, indices)) {
      const item = el("div", "study-item");
      const title = el("div", "study-title");
      title.textContent = r.title != null ? r.title : "Title unavailable";
      const meta = el("div", "study-meta");
      meta.textContent = db.studies.year[r.s] + " · " +
        db.levels.econ_eval_type[db.studies.econ_eval_type[r.s]] + " · " + diseaseLabel;
      const abs = el("div", "study-abstract");
      if (r.abstract == null) {
        abs.textContent = "No abstract available.";
        abs.classList.add("study-abstract-missing");
      } else {
        abs.textContent = r.abstract + (r.truncated ? " …" : "");
        if (r.truncated) {
          const note = el("span", "study-note");
          note.textContent = " (abstract truncated)";
          abs.appendChild(note);
        }
      }
      item.appendChild(title);
      item.appendChild(meta);
      const publicationLink = publicationUrl(db.studies, r.s);
      if (publicationLink) {
        const link = el("a", "study-publication-link");
        link.href = publicationLink;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "View publication";
        item.appendChild(link);
      }
      item.appendChild(abs);
      list.appendChild(item);
    }
  }

  function closeStudyModal() {
    $("study-modal").classList.remove("open");
    $("study-modal-list").textContent = "";
  }

  async function boot() {
    for (const b of document.querySelectorAll(".navbar .nav-link")) {
      if (b.id === "thematic-toggle") continue;
      b.addEventListener("click", () => switchTab(b.dataset.tab));
    }
    for (const button of document.querySelectorAll("[data-country-view]")) {
      button.addEventListener("click", () => showCountryView(button.dataset.countryView));
    }
    // "Thematic analysis" opens the theme index and toggles its dropdown menu.
    $("thematic-toggle").addEventListener("click", e => {
      e.stopPropagation();
      const shouldOpen = !$("thematic-nav").classList.contains("open");
      if (!$("pane-gallery").classList.contains("active")) {
        switchTab("gallery");
        hideSection();
      }
      $("thematic-nav").classList.toggle("open", shouldOpen);
      $("thematic-toggle").setAttribute("aria-expanded", String(shouldOpen));
      $("thematic-menu").hidden = !shouldOpen;
    });
    document.addEventListener("click", e => {
      if (!$("thematic-nav").contains(e.target)) closeThematicMenu();
    });
    $("fig-modal-close").addEventListener("click", closeModal);
    $("fig-modal").addEventListener("click", e => { if (e.target === $("fig-modal")) closeModal(); });
    $("fig-zoom-out").addEventListener("click", () => setFigureZoom(figureZoom - 0.25));
    $("fig-zoom-reset").addEventListener("click", () => setFigureZoom(1));
    $("fig-zoom-in").addEventListener("click", () => setFigureZoom(figureZoom + 0.25));
    $("study-modal-close").addEventListener("click", closeStudyModal);
    $("study-modal").addEventListener("click", e => { if (e.target === $("study-modal")) closeStudyModal(); });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") { closeModal(); closeStudyModal(); closeThematicMenu(); }
    });
    $("gal-back").addEventListener("click", goBackFromSection);
    for (const b of document.querySelectorAll("[data-trend-mode]")) {
      b.addEventListener("click", () => setOverviewTrendMode(b.dataset.trendMode));
    }

    const get = async name => {
      // ?v=BUILD cache-buster; BUILD is stamped at publish time (see top).
      const r = await fetch("data/" + name + ".json?v=" + BUILD);
      if (!r.ok) throw new Error("failed to load data/" + name + ".json: " + r.status);
      return r.json();
    };
    const [dict, studies, geo, disease, countries, content] = await Promise.all(
      ["dict", "studies", "geo", "disease", "countries", "content"].map(get));
    db = loadData({ dict, studies, geo, disease, countries, content });

    // Gallery sections, figure entries and the interpolated paper01 PRISMA
    // caption all come from content.json (§15.1) — nothing hardcoded.
    GALLERY = db.content.gallery;
    FIG_INDEX = {};
    for (const sec of GALLERY) {
      for (const f of sec.figs) FIG_INDEX[f.file] = { ...f, sectionTitle: sec.title };
    }

    if (window.Plotly && !window.Plotly.__softColorway) {
      const react = window.Plotly.react;
      window.Plotly.react = (gd, data, layout = {}, cfg) =>
        react.call(window.Plotly, gd, data, Object.assign({ colorway: SOFT_COLORWAY }, layout), cfg);
      window.Plotly.__softColorway = true;
    }

    renderOverview();
    renderOverviewTrend();
    renderGalleryIndex();
    setupExplorerControls();
    refreshExplorer();
    setupCountryPane();
    renderLandscape();
  }

  // err.message can embed data-derived text (URLs, server responses) —
  // textContent only, never el()'s innerHTML path.
  function showBootError(err) {
    const box = el("div", "loading-wrap");
    box.textContent = "Failed to start: " + err.message;
    document.querySelector("main").prepend(box);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => boot().catch(showBootError));
  } else {
    boot().catch(showBootError);
  }
}
