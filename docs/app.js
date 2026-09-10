const CODED_COLS = ["econ_eval_type", "design_basis", "model_label", "qaly_label",
  "oa_label", "geo_scope", "era", "topic_domain"];

export function rRound(x, digits = 0) {
  if (x == null || !isFinite(x)) return x;
  const m = Math.pow(10, digits);
  const v = x * m;
  const fl = Math.floor(v);
  const frac = v - fl;
  let r;
  if (Math.abs(frac - 0.5) < 1e-9) r = (fl % 2 === 0) ? fl : fl + 1;
  else r = Math.round(v);
  return r / m;
}

export function fmtNum(x) {
  if (x == null) return "";
  return Number(x).toLocaleString("en-US");
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

export function loadData({ dict, studies, geo, disease, countries }) {
  const levels = dict.levels;
  const codeOf = {};
  for (const col of CODED_COLS) {
    codeOf[col] = new Map(levels[col].map((lab, i) => [lab, i]));
  }
  const pal = dict.meta.pal_inc;
  const palInc = {};
  if (Array.isArray(pal)) dict.meta.inc_lv.forEach((lv, i) => { palInc[lv] = pal[i]; });
  else Object.assign(palInc, pal);
  const diseaseSets = dict.disease_grps.map(() => new Set());
  for (let i = 0; i < disease.s.length; i++) diseaseSets[disease.g[i]].add(disease.s[i]);
  return {
    dict, levels, studies, geo, disease, countries,
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
      if (!flt.mask[s]) continue;
      add(db.disease_grps[d.g[i]], stacked ? stackOf(s) : null);
    }
  } else {
    const catOf = studyCatGetter(db, xv);
    const stackOf = stacked ? studyCatGetter(db, sv) : null;
    for (const s of flt.studies) add(catOf(s), stacked ? stackOf(s) : null);
  }

  const cmpStr = (a, b) => a < b ? -1 : a > b ? 1 : 0;

  if (!stacked) {
    const rows = [...counts.entries()].map(([x, nn]) => ({ x, n: nn }));
    rows.sort((a, b) => cmpStr(a.x, b.x));
    const total = rows.reduce((a, r) => a + r.n, 0);
    for (const r of rows) r.v = pct ? (total > 0 ? 100 * r.n / total : 0) : r.n;
    rows.sort((a, b) => b.v - a.v);
    return { type: "simple", rows, total, pct };
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
  return { type: "stacked", catOrder, stacks, counts: rawCounts, values, totals: Object.fromEntries(totals), pct };
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
    c_mix: { country: shares(mixC, totC), peer: shares(mixP, totP) }
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

export const TREND_VARS = {
  "Income group": "income",
  "UN region": "un_region",
  "Evaluation type": "econ_eval_type",
  "Design basis": "design_basis",
  "Model vs measured": "model_label",
  "Uses QALY": "qaly_label",
  "Open access": "oa_label",
  "Geographic scope": "geo_scope",
  "Nothing (total)": "none"
};
export const COMP_VARS = {
  "Evaluation type": "econ_eval_type",
  "Design basis": "design_basis",
  "Model vs measured": "model_label",
  "Uses QALY": "qaly_label",
  "Open access": "oa_label",
  "Geographic scope": "geo_scope",
  "Era": "era",
  "Topic domain": "topic_domain",
  "Disease group": "grp",
  "Reports an ICER": "icer_label",
  "Reports a threshold": "thresh_label"
};
export const STACK_VARS = {
  "None": "",
  "Era": "era",
  "Model vs measured": "model_label",
  "Uses QALY": "qaly_label",
  "Geographic scope": "geo_scope"
};
export const MAP_METRICS = {
  "Studies": "studies",
  "Studies per 100k DALYs": "per100k",
  "Studies per US$1bn spending": "per_bn",
  "Studies per million people": "per_million"
};
export const SCAT_X = {
  "Total DALYs (GBD 2023)": "dalys",
  "Population": "pop",
  "Health spending, PPP US$bn (2022)": "total_spend_bn"
};
export const SCAT_Y = {
  "Studies": "studies",
  "Studies per 100k DALYs": "per100k",
  "Studies per US$1bn spending": "per_bn",
  "Studies per million people": "per_million"
};

const OA_COLORS = { "Open access": "#1baf7a", "Not open": "#eb6834", "Unknown": "#adb5bd" };
const ACCENT = "#1f5fa8";
const GREY = "#adb5bd";

export function galleryRegistry(meta) {
  const fmt = fmtNum;
  return [
    {
      title: "Size & growth",
      blurb: `How much research is there, and what kind? ${fmt(meta.n_extracted)} health economic evaluations were
              extracted (${meta.years[0]}–${meta.years[1]}); ${fmt(meta.n_studies)} are eligible for analysis. These panels carry the headline:
              the growth of the corpus, and how its evaluation-method mix has shifted.`,
      figs: [
        { file: "fig_growth.webp", title: "Cumulative growth",
          caption: "The field keeps doubling: half of everything published since 2010 appeared after 2020 (2026 flagged partial)." },
        { file: "fig_method_stream.webp", title: "Evaluation-method composition over time",
          caption: "Cost-utility rose from 45% to 54% of annual output while cost-effectiveness fell from 34% to 25%." }
      ]
    },
    {
      title: "Topics & diseases",
      blurb: `Topic, disease and intervention — the subject of the evidence. OpenAlex topics cover
              88% of the corpus; MeSH disease groups cover 63% (harvested subset, base declared on
              each figure). The emergent-theme maps come from abstract embeddings, not MeSH.`,
      figs: [
        { file: "fig_topic_landscape.webp", title: "Topic landscape",
          caption: "OpenAlex subfields grouped by field — the research areas of the field in one circular view." },
        { file: "fig_disease_circular.webp", title: "Disease landscape",
          caption: "MeSH disease groups: share of studies, coloured by LMIC/HIC lean." },
        { file: "fig_disease_method.webp", title: "Disease × evaluation method",
          caption: "How each disease area is evaluated — cost-utility vs cost-effectiveness heat map." },
        { file: "fig_transition.webp", title: "Epidemiological transition of research",
          caption: "LMIC research shifted communicable → NCD past the burden shares; injuries stayed at ~1% of research vs 11% of burden." },
        { file: "fig_topicmap_income.webp", title: "Thematic landscape by income",
          caption: "Embedding topic map (UMAP + HDBSCAN) coloured by each theme's LMIC share: theme space segregates — malaria 91% LMIC vs dementia 6%." },
        { file: "fig_topicmap.webp", title: "Thematic landscape",
          caption: "The plain theme-space map of the corpus, before income colouring." },
        { file: "fig_theme_rank.webp", title: "Emergent themes ranked by income",
          caption: "The 15 most- and 15 least-LMIC themes: the two ends never overlap (33–91% vs 3–13% LMIC)." }
      ]
    },
    {
      title: "Methods & decision-usefulness",
      blurb: `What gets measured, and how well — the decision-usefulness core. How evidence flows
              from design to method to outcome, which comparable metric is used where, and whether
              abstracts foreground the elements a decision-maker needs.`,
      figs: [
        { file: "fig_alluvial.webp", title: "Source → analysis → outcome",
          caption: "Alluvial of design basis → evaluation type → outcome family: how evidence flows through the field." },
        { file: "fig_metric.webp", title: "The comparable-metric currency",
          caption: "QALYs for rich settings, DALYs for poor: cross-income comparability is broken at the metric level." },
        { file: "fig_model_time.webp", title: "Model vs measurement over 17 years",
          caption: "The drift toward model-based (vs directly measured) evaluations, by income group." },
        { file: "fig_decision.webp", title: "Decision-framing in abstracts",
          caption: "ICER 39%, threshold 22%: few abstracts foreground decision elements — and LMIC studies report them slightly more than HIC, not less." },
        { file: "fig_forest.webp", title: "What predicts decision-usefulness",
          caption: "Adjusted odds ratios: income, design basis, disease and year predict generic-metric use. Observational, never causal." }
      ]
    },
    {
      title: "Geography & authorship",
      blurb: `Where the research is about, and who leads it. Income-comparative figures use
              extracted geography only (the affiliation proxy is income-biased in availability).`,
      figs: [
        { file: "fig_dotmap.webp", title: "Global proportional-symbol map",
          caption: "Where the evidence sits: bubbles by country study count, coloured by income group (Berrang-Ford style, Robinson)." },
        { file: "fig_worldmap.webp", title: "World map of output",
          caption: "The global distribution of eligible evaluations by country." },
        { file: "fig_top_producers.webp", title: "Top producers: volume vs per-capita",
          caption: "Two-rank slope — who leads by count vs by output per person." },
        { file: "fig_authorship_pattern.webp", title: "Who leads research about each setting",
          caption: "Local / mixed / foreign authorship stacked by income: research about poor countries is often led from abroad." },
        { file: "fig_collab_chord.webp", title: "Collaboration structure",
          caption: "Income × income co-authorship chord: how the collaboration network runs between groups." }
      ]
    },
    {
      title: "Gaps vs disease burden",
      blurb: `The map's whole point: research vs the burden of disease (GBD 2023 DALYs, country
              totals and 22 Level-2 causes) and vs health spending (IHME, PPP 2022).`,
      figs: [
        { file: "fig_burden.webp", title: "Evidence per unit of burden",
          caption: "Studies per 100k DALYs vs total burden: an 18× gap between the best- and worst-served countries." },
        { file: "fig_spending.webp", title: "Evidence per dollar of spending",
          caption: "Studies per US$1bn of health spending (PPP 2022 × latest World Bank population, mostly 2025)." },
        { file: "fig_burden_disease_companion.webp", title: "Research share vs burden share, by disease",
          caption: "Maternal-neonatal research runs at 3.6× its burden share in HIC vs 0.37× in LMIC; injuries 0.21× in LMIC." },
        { file: "fig_burden_disease.webp", title: "Burden-weighted disease mismatch (journal finish)",
          caption: "The same mismatch in Lancet register: study share vs DALY share by income." },
        { file: "fig_deficit.webp", title: "Largest absolute evidence deficits",
          caption: "Studies vs burden-expected: India +4,847 short, Nigeria +1,205, Indonesia +920 …" },
        { file: "fig_injustice.webp", title: "High burden, low research",
          caption: "The burden × evidence plane with a burden-proportional diagonal; size = population. The editorial closer." },
        { file: "fig_inequality.webp", title: "Within-LMIC inequality",
          caption: "Lorenz curve: the least-served half of LMIC burden holds 16% of the evidence; top 5 countries hold 55%; Gini 0.50." }
      ]
    },
    {
      title: "Open access & funding",
      blurb: `How the evidence is packaged and reached. Open-access status covers 93% of the
              eligible corpus (post DOI-supplement harvest); the funder field covers ~28% and is a
              floor, not a census.`,
      figs: [
        { file: "fig_openaccess.webp", title: "Open access over time",
          caption: "46% → 80% (2010–24); LMIC research is more open than HIC research." },
        { file: "fig_funder_funders.webp", title: "Who funds it",
          caption: "Top funders by studies, split by income focus: most big funders are HIC-focused; Gates dominates LMIC; Wellcome has a real LMIC share." }
      ]
    },
    {
      title: "Country maps",
      blurb: `The cartographic collection: eligible-only counts, World Bank population, GBD 2023
              burden, extracted geography, Robinson projection. Share maps show only countries
              with ≥5 studies (grey below).`,
      figs: [
        { file: "fig_map_burden.webp", title: "Research intensity vs burden",
          caption: "Studies per 100k DALYs, diverging scale — the map form of the burden mismatch figure." },
        { file: "fig_map_bivariate.webp", title: "Burden × evidence bivariate",
          caption: "The high-burden/low-evidence corner lights up; dark purple is high on both (big countries), not missing data." },
        { file: "fig_map_deserts.webp", title: "Evidence deserts",
          caption: "0 / 1–5 / 6–20 / 21+ studies: 20 countries carry a burden but have no evaluation at all." },
        { file: "fig_map_authorship.webp", title: "Who studies whom",
          caption: "Share of studies with a local author — parachute research, mapped." },
        { file: "fig_map_model.webp", title: "Model-based vs measured",
          caption: "The LMIC lean on modelled evidence, by country." },
        { file: "fig_map_openaccess.webp", title: "Open access by country",
          caption: "Share of output that is open access (93% base)." },
        { file: "fig_map_growth.webp", title: "Where the evidence is youngest",
          caption: "Share of studies published since 2018." },
        { file: "fig_map_method.webp", title: "Dominant evaluation method",
          caption: "Cost-utility North / cost-effectiveness South." },
        { file: "fig_map_disease.webp", title: "Disease atlas",
          caption: "Eleven small-multiple maps, one per GBD disease group; log counts, so the disease contrast is the point." }
      ]
    },
    {
      title: "Trends over time",
      blurb: `Comparative time-series on the year dimension (2010–2025; 2026 partial, dropped).
              Income-comparative panels use single-country extracted geography with a known
              income group.`,
      figs: [
        { file: "fig_equity_time.webp", title: "Equity over time",
          caption: "LMIC share of annual output rose 16% → 36% — still far below their 83% burden share." },
        { file: "fig_qaly_time.webp", title: "QALY-metric convergence",
          caption: "LMIC QALY use 15% → 49% vs HIC 51% → 59%: the gap narrowed, ~10pp remains." },
        { file: "fig_reach_time.webp", title: "Reach over time",
          caption: "Cumulative share of each income group's countries with ≥1 evaluation: high-income covered early, low-income reached last (28% → 96%)." },
        { file: "fig_method_stream.webp", title: "Method streamgraph",
          caption: "Evaluation-type composition: cost-utility 45% → 54%, cost-effectiveness 34% → 25%." },
        { file: "fig_decision_time.webp", title: "Decision-usefulness over time",
          caption: "All four abstract signals rose; threshold most (12% → 29%) — still a minority." }
      ]
    },
    {
      title: "Priority-setting for funders",
      blurb: `Built for a funder asking where the next pound buys the most missing evidence.
              Ranked by gap, never by cost-to-close: there is no cost or research-funding-amount
              data. Proportionality to burden is a reference point, not a target.`,
      figs: [
        { file: "fig_funder_opportunity.webp", title: "Opportunity matrix",
          caption: "Disease × income research-to-burden ratio: injuries, maternal, cardiovascular and neurological in lower-income settings are the reddest." },
        { file: "fig_funder_scorecard.webp", title: "Priority scorecard",
          caption: "Burden × intensity scatter plus the ranked deficit bar — the shortlist." },
        { file: "fig_funder_capacity.webp", title: "Capacity-building quadrant",
          caption: "Burden × local-authorship share: the high-burden, <75%-local set — fund people, not just studies." },
        { file: "fig_funder_trajectory.webp", title: "Self-correcting vs stuck",
          caption: "LMIC research-to-burden ratio, era-1 → era-2 arrows: injuries and maternal are stuck below burden and worsening." },
        { file: "fig_funder_funders.webp", title: "Funder landscape",
          caption: "Top funders by studies, split by income (~28% coverage — a floor, not a census)." }
      ]
    },
    {
      title: "Journal figures",
      blurb: `The tight journal set: each figure carries one finding, greyscale-safe, legends
              present, uncertainty shown.`,
      figs: [
        { file: "paper01.webp", title: "PRISMA flow",
          caption: "Study selection: 44,941 extracted → 38,199 eligible evaluations." },
        { file: "paper02.webp", title: "Decision-relevance cascade",
          caption: "Studies meeting each successive criterion for decision-relevance." },
        { file: "paper03.webp", title: "Density within & between income groups",
          caption: "Studies per 10 million people by country, faceted by income; area = population." },
        { file: "paper04.webp", title: "Disease composition by era and income",
          caption: "The epidemiological transition of the research, journal finish." },
        { file: "paper05.webp", title: "Disease × income heat map",
          caption: "Which diseases dominate the evidence in each income group." },
        { file: "paper06.webp", title: "In-country authorship",
          caption: "Is the evidence produced in the countries it is about? Point + CI by income." },
        { file: "paper07.webp", title: "Evidence vs disease burden",
          caption: "Studies per 100k DALYs vs burden, by income — the 18× gap." },
        { file: "paper08.webp", title: "Research attention vs burden, by disease",
          caption: "Study share vs DALY share across the 11 disease groups." }
      ]
    }
  ];
}

if (typeof document !== "undefined") {

  const $ = id => document.getElementById(id);
  const PLOTLY_CFG = { responsive: true, displayModeBar: false };
  const BASE_FONT = { family: "Inter, sans-serif", size: 12, color: "#1c2733" };

  let db = null;
  let GALLERY = [];
  let FIG_INDEX = {};
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

  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function fillSelect(sel, labels, selected) {
    sel.innerHTML = "";
    for (const lab of labels) {
      const o = document.createElement("option");
      o.value = lab;
      o.textContent = lab;
      if (selected && selected.includes(lab)) o.selected = true;
      sel.appendChild(o);
    }
  }

  function openModal(file) {
    const f = FIG_INDEX[file];
    if (!f) return;
    $("fig-modal-title").textContent = f.title;
    const img = $("fig-modal-img");
    img.src = "figures/" + f.file;
    img.alt = f.title;
    $("fig-modal-caption").textContent = f.caption;
    $("fig-modal").classList.add("open");
  }

  function closeModal() {
    $("fig-modal").classList.remove("open");
    $("fig-modal-img").src = "";
  }

  function switchTab(name) {
    for (const b of document.querySelectorAll(".navbar .nav-link")) {
      b.classList.toggle("active", b.dataset.tab === name);
    }
    for (const p of document.querySelectorAll(".tab-pane")) {
      p.classList.toggle("active", p.id === "pane-" + name);
    }
    if (name === "explorer" && state.result) {
      for (const id of ["x-trend", "x-map", "x-comp", "x-scatter"]) {
        if (window.Plotly && $(id).data) window.Plotly.Plots.resize($(id));
      }
    }
    if (name === "country" && window.Plotly) {
      for (const id of ["c-trend", "c-mix"]) {
        if ($(id).data) window.Plotly.Plots.resize($(id));
      }
    }
  }

  function renderOverview() {
    const m = db.dict.meta;
    $("ov-n-extracted").textContent = fmtNum(m.n_extracted);
    $("ov-n-studies").textContent = fmtNum(m.n_studies);
    $("ov-year-lo").textContent = m.years[0];
    $("ov-year-hi").textContent = m.years[1];
    $("nav-built").textContent = "bundle " + m.built;

    const tiles = [
      { title: "Eligible full evaluations", value: fmtNum(m.n_studies), theme: "primary" },
      { title: "Years covered", value: m.years[0] + "–" + m.years[1], theme: "secondary" },
      { title: "Countries studied", value: fmtNum(m.n_countries_named), sub: "named in extracted geography", theme: "info" },
      { title: "Journals", value: fmtNum(m.n_journals), sub: "of the harvested set", theme: "secondary" },
      { title: "Use QALYs", value: rRound(m.pct_qaly) + "%", theme: "success" },
      { title: "Model-based", value: rRound(m.pct_model) + "%", theme: "info" },
      { title: "Single-country studies", value: rRound(m.pct_single) + "%", theme: "secondary" }
    ];
    const wrap = $("ov-tiles");
    wrap.innerHTML = "";
    for (const t of tiles) {
      const box = el("div", "value-box bg-" + t.theme);
      box.appendChild(el("div", "value-box-title", t.title));
      box.appendChild(el("div", "value-box-value", t.value));
      if (t.sub) box.appendChild(el("div", "value-box-sub", t.sub));
      wrap.appendChild(box);
    }

    const heroes = [
      { file: "fig_dotmap.webp", alt: "Global dot map" },
      { file: "fig_burden.webp", alt: "Evidence vs burden" },
      { file: "fig_transition.webp", alt: "Epidemiological transition" }
    ];
    const hw = $("ov-hero-imgs");
    hw.innerHTML = "";
    for (const h of heroes) {
      const card = el("div", "card");
      const body = el("div", "card-body p-0");
      const img = el("img", "hero-img");
      img.src = "figures/" + h.file;
      img.alt = h.alt;
      img.loading = "lazy";
      img.addEventListener("click", () => openModal(h.file));
      body.appendChild(img);
      card.appendChild(body);
      hw.appendChild(card);
    }
  }

  function renderGalleryIndex() {
    const idx = $("gal-section-index");
    idx.innerHTML = "";
    GALLERY.forEach((sec, i) => {
      const card = el("button", "section-card");
      card.appendChild(el("div", "sec-title", sec.title));
      card.appendChild(el("div", "sec-count", sec.figs.length + " figures"));
      card.addEventListener("click", () => showSection(i));
      idx.appendChild(card);
    });
  }

  function showSection(i) {
    const sec = GALLERY[i];
    $("gal-index").style.display = "none";
    $("gal-section").style.display = "block";
    $("gal-sec-title").textContent = sec.title;
    $("gal-sec-blurb").textContent = sec.blurb.replace(/\s+/g, " ").trim();
    const grid = $("gal-sec-grid");
    grid.innerHTML = "";
    for (const f of sec.figs) {
      const card = el("div", "fig-card");
      const img = el("img");
      img.src = "figures/" + f.file;
      img.alt = f.title;
      img.loading = "lazy";
      img.addEventListener("click", () => openModal(f.file));
      card.appendChild(img);
      const body = el("div", "fig-body");
      body.appendChild(el("div", "fig-title", f.title));
      body.appendChild(el("div", "fig-caption", f.caption.replace(/\s+/g, " ").trim()));
      card.appendChild(body);
      grid.appendChild(card);
    }
    window.scrollTo(0, 0);
  }

  function hideSection() {
    $("gal-section").style.display = "none";
    $("gal-index").style.display = "block";
  }

  function makeRadios(containerId, name, choices) {
    const c = $(containerId);
    c.innerHTML = "";
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

    fillSelect($("x-trend-by"), Object.keys(TREND_VARS), ["Income group"]);
    fillSelect($("x-map-metric"), Object.keys(MAP_METRICS), ["Studies"]);
    fillSelect($("x-comp-var"), Object.keys(COMP_VARS), ["Evaluation type"]);
    fillSelect($("x-comp-stack"), Object.keys(STACK_VARS), ["None"]);
    const compMode = $("x-comp-mode");
    compMode.innerHTML = "";
    for (const [lab, val] of [["Count", "n"], ["Share (%)", "pct"]]) {
      const o = document.createElement("option");
      o.value = val;
      o.textContent = lab;
      compMode.appendChild(o);
    }
    fillSelect($("x-scatter-x"), Object.keys(SCAT_X), ["Total DALYs (GBD 2023)"]);
    fillSelect($("x-scatter-y"), Object.keys(SCAT_Y), ["Studies per 100k DALYs"]);

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
    const v = TREND_VARS[label];
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
        hovertemplate: "%{x} · " + cat + ": %{y} studies<extra></extra>"
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
    const m = MAP_METRICS[label];
    const rows = state.result.byCountry;
    const isCounts = m === "studies";
    const z = rows.map(r => isCounts ? Math.log10(r.studies + 1) : r[m]);
    const text = rows.map(r => isCounts
      ? r.country + "<br>" + fmtNum(r.studies) + " studies"
      : r.country + "<br>" + fmtNum(r.studies) + " studies<br>" +
        (r[m] == null ? "NA" : rRound(r[m], 2)) + " " + label.toLowerCase());
    const colorscale = isCounts
      ? [[0, "#f1f3f5"], [0.0001, "#c6dbef"], [0.5, "#2a78d6"], [1, "#08306b"]]
      : [[0, "#f7fbff"], [0.5, "#6baed6"], [1, "#08306b"]];
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
    const xv = COMP_VARS[label];
    const sv = STACK_VARS[$("x-comp-stack").value];
    const mode = $("x-comp-mode").value;
    const res = compCounts(db, state.result, xv, sv, mode);
    const note = xv === "grp" ? " · a study can sit in several disease groups" : "";
    const annotation = {
      text: label + note, xref: "paper", yref: "paper",
      x: 0, y: 1.06, xanchor: "left", showarrow: false,
      font: { size: 11, color: "#6b7280" }
    };
    let traces, layout;
    if (res.type === "simple") {
      const desc = res.rows;
      const bottomUp = desc.slice().reverse();
      traces = [{
        type: "bar", orientation: "h",
        y: desc.map(r => r.x),
        x: desc.map(r => r.v),
        marker: { color: ACCENT },
        hovertemplate: "%{y}: %{x}<extra></extra>"
      }];
      layout = {
        yaxis: {
          categoryorder: "array",
          categoryarray: bottomUp.map(r => r.x),
          automargin: true
        },
        xaxis: {
          title: res.pct ? "share of filtered studies (%)" : "studies",
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
        hovertemplate: "%{y} · " + k + ": %{x}<extra></extra>"
      }));
      layout = {
        barmode: "stack",
        yaxis: {
          categoryorder: "array",
          categoryarray: bottomUp,
          automargin: true
        },
        xaxis: {
          title: res.pct ? "share within category (%)" : "studies",
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
    const xv = SCAT_X[xLabel];
    const yv = SCAT_Y[yLabel];
    const pts = scatterPoints(db, state.result, xv, yv);
    const traces = db.incLv.map(inc => {
      const rows = pts.filter(r => r.income === inc);
      return {
        type: "scatter", mode: "markers",
        name: inc,
        x: rows.map(r => r[xv]),
        y: rows.map(r => r[yv]),
        text: rows.map(r => r.country + "<br>" + fmtNum(r.studies) + " studies"),
        hoverinfo: "text",
        marker: { color: db.palInc[inc], size: 8, opacity: 0.8 }
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
    let html = "<thead><tr>";
    for (const c of cols) html += `<th${numCols.has(c) ? ' class="num"' : ""}>${c}</th>`;
    html += "</tr></thead><tbody>";
    for (const r of rows) {
      html += "<tr>";
      for (const c of cols) {
        const v = r[c];
        const cell = v == null ? "" : (numCols.has(c) && c !== "Studies" ? v : (c === "Studies" ? fmtNum(v) : v));
        html += `<td${numCols.has(c) ? ' class="num"' : ""}>${cell}</td>`;
      }
      html += "</tr>";
    }
    html += "</tbody>";
    $("x-table").innerHTML = html;
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
    facts.innerHTML = "";
    for (const [k, v] of countryFacts(db, iso3)) {
      facts.appendChild(el("dt", null, k));
      facts.appendChild(el("dd", null, String(v)));
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
        line: { color: ACCENT, width: 3 },
        hovertemplate: "%{x}: %{y} studies<extra>country</extra>"
      },
      {
        x: pYears, y: pYears.map(y => ct.peer[y]),
        mode: "lines", type: "scatter", name: "income-group mean",
        line: { color: GREY, width: 3 },
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
        marker: { color: ACCENT },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: grps, x: grps.map(g => mix.peer[g] != null ? mix.peer[g] : null),
        marker: { color: GREY },
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
  }

  async function boot() {
    for (const b of document.querySelectorAll(".navbar .nav-link")) {
      b.addEventListener("click", () => switchTab(b.dataset.tab));
    }
    $("fig-modal-close").addEventListener("click", closeModal);
    $("fig-modal").addEventListener("click", e => { if (e.target === $("fig-modal")) closeModal(); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });
    $("gal-back").addEventListener("click", hideSection);

    const get = async name => {
      const r = await fetch("data/" + name + ".json");
      if (!r.ok) throw new Error("failed to load data/" + name + ".json: " + r.status);
      return r.json();
    };
    const [dict, studies, geo, disease, countries] = await Promise.all(
      ["dict", "studies", "geo", "disease", "countries"].map(get));
    db = loadData({ dict, studies, geo, disease, countries });

    GALLERY = galleryRegistry(db.dict.meta);
    FIG_INDEX = {};
    for (const sec of GALLERY) for (const f of sec.figs) FIG_INDEX[f.file] = f;

    renderOverview();
    renderGalleryIndex();
    setupExplorerControls();
    refreshExplorer();
    setupCountryPane();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => boot().catch(err => {
      document.querySelector("main").prepend(el("div", "loading-wrap", "Failed to start: " + err.message));
    }));
  } else {
    boot().catch(err => {
      document.querySelector("main").prepend(el("div", "loading-wrap", "Failed to start: " + err.message));
    });
  }
}
