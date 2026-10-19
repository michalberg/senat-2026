/* Senát 2026 – kolik stály kampaně. Statická SPA nad data.json */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const app = $("#app"), tip = $("#tip");
  let D, C = {}, O = {}, B = {}, A = {};

  // ---------- formátování ----------
  const nf = new Intl.NumberFormat("cs-CZ");
  const kc = v => v == null ? "—" : nf.format(Math.round(v)) + " Kč";
  const mil = v => v == null ? "—" : (v >= 1e6 ? (v / 1e6).toLocaleString("cs-CZ", { maximumFractionDigits: 2 }) + " mil." : nf.format(Math.round(v / 1000)) + " tis.");
  const pct = v => v == null ? "—" : v.toLocaleString("cs-CZ", { maximumFractionDigits: 1 }) + " %";
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const name = c => `${c.jmeno} ${c.prijmeni}`;
  const col = c => (B[c.blok] || B.ostatni).barva;
  const sw = c => `<i class="sw" style="background:${col(c)}"></i>`;
  const res = c => c.zvolen ? `<span class="pill win">zvolen${c.zvolen_1k ? " v 1. kole" : ""}</span>` : c.postup ? `<span class="pill k2">2. kolo</span>` : "";
  const QCLS = { "vysoká": "vysoka", "střední": "stredni", "nízká": "nizka" };
  const qual = c => `<span class="q ${QCLS[c.kvalita] || "na"}">${esc(c.kvalita)}</span>`;
  const MES = { "01": "led", "02": "úno", "03": "bře", "04": "dub", "05": "kvě", "06": "čvn", "07": "čvc", "08": "srp", "09": "zář", "10": "říj" };
  const cLink = c => `<a href="#/obvod/${c.obvod}#k${c.id}">${esc(name(c))}</a>`;
  const vsShort = c => esc(c.typ === "K" ? c.strany.join("+") : c.vs_zkr);

  // ---------- tooltip ----------
  function bindTips(root) {
    root.querySelectorAll("[data-tip]").forEach(el => {
      el.addEventListener("mousemove", e => {
        tip.innerHTML = el.dataset.tip; tip.hidden = false;
        const w = tip.offsetWidth, h = tip.offsetHeight;
        let x = e.clientX + 14, y = e.clientY + 14;
        if (x + w > innerWidth - 8) x = e.clientX - w - 14;
        if (y + h > innerHeight - 8) y = e.clientY - h - 14;
        tip.style.left = x + "px"; tip.style.top = y + "px";
      });
      el.addEventListener("mouseleave", () => tip.hidden = true);
    });
  }
  const ctip = c => esc(`<b>${esc(name(c))}</b><br>${esc(c.vs_zkr)} · obvod ${c.obvod}<br>výdaje ${kc(c.celkem)}<br>1. kolo ${pct(c.k1_proc)}${c.postup ? ` · 2. kolo ${pct(c.k2_proc)}` : ""}`);

  // ---------- tabulky s řazením ----------
  function table(cols, rows, opt = {}) {
    const id = "t" + Math.random().toString(36).slice(2, 8);
    const head = cols.map((c, i) => `<th data-i="${i}" class="${c.r ? "r" : ""}">${c.l}</th>`).join("");
    const html = `<div class="tbl-wrap"><table class="t" id="${id}"><thead><tr>${head}</tr></thead><tbody></tbody></table></div>`;
    setTimeout(() => {
      const t = document.getElementById(id); if (!t) return;
      let si = opt.sort ?? -1, dir = opt.dir ?? 1;
      const body = t.tBodies[0];
      const draw = () => {
        const rs = rows.slice();
        if (si >= 0) {
          const f = cols[si].s || cols[si].v;
          rs.sort((a, b) => { const x = f(a), y = f(b); if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * dir; });
        }
        body.innerHTML = rs.map(r => `<tr class="${opt.cls ? opt.cls(r) : ""}">${cols.map(c => `<td class="${c.r ? "r" : ""}">${c.h ? c.h(r) : esc(c.v(r))}</td>`).join("")}</tr>`).join("");
        t.querySelectorAll("th").forEach(th => th.removeAttribute("aria-sort"));
        if (si >= 0) t.querySelector(`th[data-i="${si}"]`).setAttribute("aria-sort", dir > 0 ? "ascending" : "descending");
        bindTips(body);
      };
      t.querySelectorAll("th").forEach(th => th.addEventListener("click", () => {
        const i = +th.dataset.i; if (i === si) dir = -dir; else { si = i; dir = cols[i].r ? -1 : 1; } draw();
      }));
      draw();
    });
    return html;
  }
  const inbar = (v, max, color) => `<div class="inbar"><i style="width:${max ? Math.max(1, v / max * 110) : 0}px;background:${color}"></i><span>${kc(v)}</span></div>`;

  // ---------- grafy ----------
  function stackedObvody(list) {
    const max = Math.max(...list.map(o => o.celkem));
    return `<div class="stk">` + list.map(o => {
      const cs = o.kandidati.map(k => C[k]).filter(c => c.celkem).sort((a, b) => b.celkem - a.celkem);
      const segs = cs.map(c => `<i style="width:${c.celkem / max * 100}%;background:${col(c)}" data-tip="${ctip(c)}"></i>`).join("");
      const na = o.neuplne ? `<i class="na" style="width:14px" data-tip="${esc("<b>Chybí data</b><br>" + o.chybi.map(k => esc(name(C[k]))).join(", "))}"></i>` : "";
      return `<a class="stk-row" href="#/obvod/${o.obvod}"><span class="nm"><small>${o.obvod}</small>${esc(o.nazev)}</span><span class="stk-tr">${segs}${na}</span><span class="v">${mil(o.celkem)}<small>${o.neuplne ? "neúplné" : nf.format(o.kc_na_volice) + " Kč/volič"}</small></span></a>`;
    }).join("") + `</div>`;
  }

  function legend(ids) {
    return `<div class="legend">` + D.bloky.filter(b => !ids || ids.has(b.id)).map(b => `<span><i class="sw" style="background:${b.barva}"></i>${esc(b.nazev)}</span>`).join("") + `<span><i class="sw" style="background:repeating-linear-gradient(45deg,var(--grey) 0 2px,transparent 2px 6px)"></i>data chybí</span></div>`;
  }

  function scatter(cs) {
    const W = 760, H = 460, L = 46, R = 16, T = 14, Bm = 40;
    const x = v => L + v / 100 * (W - L - R), y = v => H - Bm - v / 70 * (H - T - Bm);
    let g = "";
    for (let v = 0; v <= 100; v += 20) g += `<line class="ax" x1="${x(v)}" x2="${x(v)}" y1="${T}" y2="${H - Bm}"/><text x="${x(v)}" y="${H - Bm + 16}" text-anchor="middle">${v} %</text>`;
    for (let v = 0; v <= 70; v += 10) g += `<line class="ax" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v} %</text>`;
    g += `<line class="diag" x1="${x(0)}" y1="${y(0)}" x2="${x(70)}" y2="${y(70)}"/>`;
    g += `<text x="${(W + L) / 2}" y="${H - 4}" text-anchor="middle">podíl na výdajích všech kandidátů v obvodu</text>`;
    g += `<text transform="translate(12 ${(H - Bm) / 2}) rotate(-90)" text-anchor="middle">podíl hlasů v 1. kole</text>`;
    const dots = cs.filter(c => c.podil_vydaju != null).sort((a, b) => a.zvolen - b.zvolen).map(c =>
      `<circle class="${c.zvolen ? "win" : ""}" cx="${x(c.podil_vydaju)}" cy="${y(c.k1_proc)}" r="${c.zvolen ? 6 : 5}" fill="${col(c)}" data-tip="${ctip(c)}&lt;br&gt;podíl výdajů v obvodu ${pct(c.podil_vydaju)}" onclick="location.hash='#/obvod/${c.obvod}'"/>`).join("");
    return `<svg class="scatter" viewBox="0 0 ${W} ${H}" role="img" aria-label="Podíl výdajů vs. podíl hlasů">${g}${dots}</svg>`;
  }

  function monthly(cs) {
    const months = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"];
    const by = months.map(m => { const r = {}; cs.forEach(c => { const v = c.mesice[m] || 0; if (v > 0) r[c.blok] = (r[c.blok] || 0) + v; }); return r; });
    const tot = by.map(r => Object.values(r).reduce((a, b) => a + b, 0));
    const max = Math.max(...tot);
    const order = D.bloky.map(b => b.id);
    const bars = by.map((r, i) => `<div class="col" data-tip="${esc(`<b>${MES[months[i].slice(5)]} 2026: ${mil(tot[i])} Kč</b><br>` + order.filter(k => r[k]).map(k => `${esc(B[k].nazev)}: ${mil(r[k])}`).join("<br>"))}">` +
      order.filter(k => r[k]).map(k => `<i style="height:${r[k] / max * 100}%;background:${B[k].barva}"></i>`).join("") + `</div>`).join("");
    return `<div class="cols">${bars}</div><div class="cols-l">${months.map((m, i) => `<span>${MES[m.slice(5)]}<br><b>${mil(tot[i])}</b></span>`).join("")}</div>`;
  }

  // ---------- stránky ----------
  function setNav(k) {
    if (k !== "obvod" && $("#navObv")) $("#navObv").value = "";
    document.querySelectorAll(".nav .tab").forEach(a => a.classList.toggle("on", a.dataset.k === k));
  }

  function findings() {
    const s = D.souhrn, K = D.kandidati.filter(c => c.celkem != null);
    const win = K.filter(c => c.zvolen), fin = K.filter(c => c.postup);
    const cheapW = win.slice().sort((a, b) => a.celkem - b.celkem), richW = cheapW.slice().reverse();
    const top = K.slice().sort((a, b) => b.celkem - a.celkem)[0];
    const obv = D.obvody.slice().sort((a, b) => b.celkem - a.celkem);
    const loserRich = K.filter(c => !c.zvolen).sort((a, b) => b.celkem - a.celkem)[0];
    const real = cheapW.filter(c => c.celkem > 0);
    const bl = D.bloky.slice().sort((a, b) => b.celkem - a.celkem);
    return [
      `Kandidáti utratili přes volební účty dohromady nejméně <b>${mil(s.celkem)} Kč</b> (${s.znamych === s.kandidatu ? `všech ${s.kandidatu} kandidátů` : `${s.znamych} ze ${s.kandidatu} kandidátů`}). Průměrný kandidát utratil ${mil(s.vsichni.prumer)} Kč, medián je ${mil(s.vsichni.median)} Kč.`,
      `Na <b>postup do 2. kola</b> obvykle stačilo kolem ${mil(s.postupujici.median)} Kč (medián finalistů), nejlevněji (s doloženými výdaji) se do finále dostal(a) ${(() => { const f = fin.filter(c => c.celkem > 0).sort((a, b) => a.celkem - b.celkem)[0]; return `${cLink(f)} (${vsShort(f)}) za ${kc(f.celkem)}`; })()}. Kandidáti, kteří nepostoupili, měli medián jen ${mil(s.nepostupujici.median)} Kč.`,
      `<b>Vítězové</b> utratili v mediánu ${mil(s.vitezove.median)} Kč. Nejdražší mandát: ${cLink(richW[0])} (${vsShort(richW[0])}, ${kc(richW[0].celkem)}); nejlevnější s doloženými výdaji: ${cLink(real[0])} (${vsShort(real[0])}, ${kc(real[0].celkem)}). ${cheapW[0].celkem === 0 ? `${cLink(cheapW[0])} vyhrál(a) s volebním účtem bez jediného pohybu.` : ""}`,
      `Kandidát s největším rozpočtem vyhrál ve <b>${s.nejvetsi_vyhral} z ${s.obvodu}</b> obvodů. Ve 2. kole zvítězil bohatší z dvojice v ${s.bohatsi_vyhral_2k} z ${s.duelu} soubojů – peníze pomáhají, ale nerozhodují: ${cLink(loserRich)} utratil(a) ${kc(loserRich.celkem)} a mandát nezískal(a).`,
      `Nejdražší kampaň vedl(a) ${cLink(top)} (${vsShort(top)}, ${kc(top.celkem)}). Nejvíc peněz se protočilo v obvodu <a href="#/obvod/${obv[0].obvod}">${esc(obv[0].nazev)}</a> (${mil(obv[0].celkem)} Kč), nejméně v obvodu <a href="#/obvod/${obv[obv.length - 1].obvod}">${esc(obv[obv.length - 1].nazev)}</a> (${mil(obv[obv.length - 1].celkem)} Kč, jen dva kandidáti).`,
      `Podle politických bloků nejvíc utratily ${esc(bl[0].nazev)} (${mil(bl[0].celkem)} Kč) a ${esc(bl[1].nazev)} (${mil(bl[1].celkem)} Kč). ANO vložilo do 24 kampaní ${mil(D.bloky.find(b => b.id === "ano").celkem)} Kč, ale nezískalo žádný mandát; koalice demokratických stran (ODS/TOP 09/STAN/KDU/Piráti v různých kombinacích) mají průměrně dražší, ale úspěšnější kandidáty.`,
      `Mezi koly utratili finalisté v mediánu ${mil(s.po_1kole_finaliste.median)} Kč navíc; některé subjekty platí faktury i po volbách, čísla jsou proto stav k 19. 10. 2026.`,
      `Ve financování je řada <a href="#/anomalie">nestandardních situací</a>: vítěz s prázdným účtem, 6,66 mil. Kč SPD jedné agentuře bez rozpadu na obvody, „vlastní vklady“ z účtu jiné osoby, strany bez darovacího účtu nebo zprávy podané ještě před volbami.`,
    ];
  }

  function statsTable() {
    const s = D.souhrn;
    const rows = [["Všichni kandidáti s daty", s.vsichni], ["Nepostoupili do 2. kola", s.nepostupujici], ["Postoupili do 2. kola", s.postupujici],
      ["Poražení ve 2. kole", s.porazeni_finaliste], ["Vítězové (všichni)", s.vitezove], ["Vítězové ve 2. kole", s.vitezove_2k]];
    return `<div class="tbl-wrap"><table class="t"><thead><tr><th>Skupina</th><th class="r">Počet</th><th class="r">Minimum</th><th class="r">Medián</th><th class="r">Průměr</th><th class="r">Maximum</th></tr></thead><tbody>` +
      rows.map(([l, x]) => `<tr><td>${l}</td><td class="r">${x.n}</td><td class="r">${kc(x.min)}</td><td class="r"><b>${kc(x.median)}</b></td><td class="r">${kc(x.prumer)}</td><td class="r">${kc(x.max)}</td></tr>`).join("") + `</tbody></table></div>`;
  }

  const candCols = (max, extra = []) => [
    { l: "Kandidát", v: c => c.prijmeni, h: c => `${sw(c)} ${cLink(c)} <span class="small">${esc(c.vs_nazev.length > 60 ? c.vs_zkr : c.vs_nazev)}</span>` },
    { l: "Obvod", v: c => c.obvod, h: c => `<a href="#/obvod/${c.obvod}">${c.obvod} ${esc(O[c.obvod].nazev)}</a>` },
    { l: "Výdaje", r: 1, v: c => c.celkem, h: c => inbar(c.celkem, max, col(c)) },
    { l: "1. kolo", r: 1, v: c => c.k1_proc, h: c => pct(c.k1_proc) },
    ...extra,
    { l: "Kč / hlas", r: 1, v: c => c.kc_na_hlas, h: c => c.kc_na_hlas == null ? "—" : nf.format(c.kc_na_hlas) },
    { l: "Odhad", v: c => c.kvalita, h: qual },
  ];

  function pageOverview() {
    setNav("prehled");
    const s = D.souhrn, K = D.kandidati;
    const known = K.filter(c => c.celkem != null);
    const max = Math.max(...known.map(c => c.celkem));
    const fin = known.filter(c => c.postup || c.zvolen_1k), win = known.filter(c => c.zvolen);
    const obv = D.obvody.slice().sort((a, b) => b.celkem - a.celkem);
    const top = known.slice().sort((a, b) => b.celkem - a.celkem)[0];
    const self = known.filter(c => (c.prijmy.kandidat || 0) > 0).sort((a, b) => b.prijmy.kandidat - a.prijmy.kandidat);
    const duels = D.duely.map(d => { const a = C[d.a], b = C[d.b]; const w = a.zvolen ? a : b, l = a.zvolen ? b : a; return { o: d.obvod, w, l, r: w.celkem && l.celkem ? w.celkem / l.celkem : null }; });
    const vote5 = known.filter(c => c.k1_proc >= 5 && c.kc_na_hlas != null);
    app.innerHTML = `
    <div class="hero"><div><h1>Kolik stály senátní volby 2026</h1>
      <div class="sub">${s.obvodu} obvodů · ${s.kandidatu} kandidátů · výdaje z transparentních volebních účtů, stav k <b>19. 10. 2026</b></div></div></div>
    <nav class="toc"><a href="#s-shrnuti">Shrnutí</a><a href="#s-obvody">Obvody</a><a href="#s-potreba">Kolik je potřeba</a><a href="#s-postup">Postup do 2. kola</a><a href="#s-vitezove">Vítězové</a><a href="#s-duely">Souboje 2. kola</a><a href="#s-efekt">Peníze a hlasy</a><a href="#s-cas">V čase</a><a href="#s-zdroje">Zdroje peněz</a></nav>
    <div class="tiles">
      <div class="tile ours"><span class="lbl">Utraceno celkem</span><span class="val">${mil(s.celkem)}<small>Kč</small></span><span class="d">${s.znamych === s.kandidatu ? "všichni kandidáti" : s.znamych + " kandidátů s daty"}</span></div>
      <div class="tile"><span class="lbl">Medián vítěze</span><span class="val">${mil(s.vitezove.median)}<small>Kč</small></span><span class="d">průměr ${mil(s.vitezove.prumer)}</span></div>
      <div class="tile"><span class="lbl">Medián finalisty</span><span class="val">${mil(s.postupujici.median)}<small>Kč</small></span><span class="d">postup do 2. kola</span></div>
      <div class="tile"><span class="lbl">Medián nepostupujícího</span><span class="val">${mil(s.nepostupujici.median)}<small>Kč</small></span><span class="d">${s.nepostupujici.n} kandidátů</span></div>
      <div class="tile"><span class="lbl">Největší rozpočet vyhrál</span><span class="val">${s.nejvetsi_vyhral}<small>/ ${s.obvodu}</small></span><span class="d">obvodů</span></div>
      <div class="tile"><span class="lbl">Nejdražší kampaň</span><span class="val">${mil(top.celkem)}<small>Kč</small></span><span class="d">${esc(name(top))}</span></div>
    </div>

    <section class="card" id="s-shrnuti"><h2>Manažerské shrnutí</h2><ul class="find">${findings().map(f => `<li>${f}</li>`).join("")}</ul>
      <p class="note">Výdaje = odchozí platby z volebních účtů (vč. poplatků) mínus vrácené přeplatky; bez převodů zpět straně a bez vrácených darů (dary na volební účet posílat nelze, strany je musí vrátit). Sdílené účty stran jsou rozpočítány podle symbolů a popisů plateb, zbytek rovným dílem – viz <a href="#/metodika">metodika</a>.</p></section>

    <section class="card" id="s-obvody"><h2>Kolik se utratilo v jednotlivých obvodech</h2>
      <p class="lead">Každý pruh je součet výdajů všech kandidátů v obvodu, segmenty jsou kandidáti v barvě politického bloku. Klikněte na obvod pro detail.</p>
      ${stackedObvody(obv)}${legend(new Set(known.map(c => c.blok)))}</section>

    <section class="card" id="s-potreba"><h2>Kolik bylo potřeba utratit</h2>
      <p class="lead">Rozložení výdajů podle toho, jak kandidát dopadl. Kampaně s nulovými výdaji (prázdné účty) jsou započteny.</p>${statsTable()}</section>

    <section class="card" id="s-postup"><h2>Postup do 2. kola: nejlevněji a nejdráž</h2>
      <p class="lead">Všichni, kdo postoupili do 2. kola nebo vyhráli rovnou v 1. kole (${fin.length} kandidátů s daty). Řazeno od nejlevnější kampaně; klikem na záhlaví změníte řazení.</p>
      ${table(candCols(max, [{ l: "Výsledek", v: c => c.zvolen ? 2 : 1, h: res }]), fin, { sort: 2, dir: 1 })}</section>

    <section class="card" id="s-vitezove"><h2>Vítězové: nejlevnější a nejdražší mandáty</h2>
      ${table(candCols(max, [{ l: "2. kolo", r: 1, v: c => c.k2_proc, h: c => c.zvolen_1k ? "v 1. kole" : pct(c.k2_proc) }]), win, { sort: 2, dir: 1 })}</section>

    <section class="card" id="s-duely"><h2>Souboje 2. kola</h2>
      <p class="lead">Ve ${s.bohatsi_vyhral_2k} z ${s.duelu} dvojic s úplnými daty vyhrál ten, kdo měl za celou kampaň víc peněz. „Po 1. kole“ = výdaje od 11. 10. 2026.</p>
      ${table([
        { l: "Obvod", v: d => d.o, h: d => `<a href="#/obvod/${d.o}">${d.o} ${esc(O[d.o].nazev)}</a>` },
        { l: "Vítěz", v: d => d.w.prijmeni, h: d => `${sw(d.w)} ${cLink(d.w)} <span class="small">${vsShort(d.w)}</span>` },
        { l: "Výdaje vítěze", r: 1, v: d => d.w.celkem, h: d => kc(d.w.celkem) },
        { l: "Poražený", v: d => d.l.prijmeni, h: d => `${sw(d.l)} ${cLink(d.l)} <span class="small">${vsShort(d.l)}</span>` },
        { l: "Výdaje poraženého", r: 1, v: d => d.l.celkem, h: d => kc(d.l.celkem) },
        { l: "Poměr", r: 1, v: d => d.r, h: d => d.r == null ? "—" : d.r.toLocaleString("cs-CZ", { maximumFractionDigits: 1 }) + "×" },
        { l: "Po 1. kole (V / P)", r: 1, v: d => d.w.po_1kole - d.l.po_1kole, h: d => `${mil(d.w.po_1kole)} / ${mil(d.l.po_1kole)}` },
      ], duels, { sort: 5, dir: 1 })}</section>

    <section class="card" id="s-efekt"><h2>Přinesly peníze hlasy?</h2>
      <p class="lead">Každý bod je kandidát: vodorovně jeho podíl na výdajích v obvodu, svisle podíl hlasů v 1. kole. Body nad čárkovanou úhlopříčkou získaly víc hlasů, než by odpovídalo penězům. Vítězové mají tmavý okraj.</p>
      ${scatter(known)}${legend(new Set(known.map(c => c.blok)))}
      <div class="grid2" style="margin-top:22px">
        <div><h3>Nejdražší hlasy <span class="note">(kandidáti nad 5 %)</span></h3>${table([{ l: "Kandidát", v: c => c.prijmeni, h: c => `${sw(c)} ${cLink(c)} <span class="small">${vsShort(c)}</span>` }, { l: "Kč / hlas", r: 1, v: c => c.kc_na_hlas, h: c => nf.format(c.kc_na_hlas) }, { l: "1. kolo", r: 1, v: c => c.k1_proc, h: c => pct(c.k1_proc) }], vote5.sort((a, b) => b.kc_na_hlas - a.kc_na_hlas).slice(0, 10))}</div>
        <div><h3>Nejlevnější hlasy <span class="note">(kandidáti nad 5 %)</span></h3>${table([{ l: "Kandidát", v: c => c.prijmeni, h: c => `${sw(c)} ${cLink(c)} <span class="small">${vsShort(c)}</span>` }, { l: "Kč / hlas", r: 1, v: c => c.kc_na_hlas, h: c => nf.format(c.kc_na_hlas) }, { l: "1. kolo", r: 1, v: c => c.k1_proc, h: c => pct(c.k1_proc) }], vote5.sort((a, b) => a.kc_na_hlas - b.kc_na_hlas).slice(0, 10))}</div>
      </div></section>

    <section class="card" id="s-cas"><h2>Výdaje v čase</h2><p class="lead">Výdaje všech kandidátů podle měsíce platby a politického bloku. Říjen obsahuje 1. i 2. kolo a doplatky po volbách.</p>${monthly(known)}${legend(new Set(known.map(c => c.blok)))}</section>

    <section class="card" id="s-zdroje"><h2>Odkud peníze šly</h2>
      <p class="lead">Rozpad příjmů volebních účtů (u sdílených účtů poměrem podle výdajů). Seznamy dárců zveřejněné ÚDHPSH neobsahují částky, proto jsou dary vidět jen tam, kde prošly přímo volebním účtem – u většiny stran posílají dárci peníze na centrální účet strany a na volební účet chodí převody strany.</p>
      ${(() => { const sum = k => Math.round(known.reduce((a, c) => a + (c.prijmy[k] || 0), 0)); const tot = ["strana", "dar", "kandidat", "neurceno"].map(sum); const all = tot.reduce((a, b) => a + b, 0);
        return `<div class="tiles"><div class="tile"><span class="lbl">Převody stran a koaličních partnerů</span><span class="val">${pct(tot[0] / all * 100)}</span><span class="d">${mil(tot[0])} Kč</span></div><div class="tile"><span class="lbl">Dary přímo na volební účet</span><span class="val">${pct(tot[1] / all * 100)}</span><span class="d">${mil(tot[1])} Kč</span></div><div class="tile"><span class="lbl">Vlastní peníze kandidátů</span><span class="val">${pct(tot[2] / all * 100)}</span><span class="d">${mil(tot[2])} Kč</span></div><div class="tile"><span class="lbl">Neidentifikovaný plátce</span><span class="val">${pct(tot[3] / all * 100)}</span><span class="d">${mil(tot[3])} Kč</span></div></div>`; })()}
      <h3>Největší dárci</h3>
      <p class="note">Dárci ze seznamů ÚDHPSH (kromě stran) s platbami dohledanými na darovacích účtech stran a volebních účtech, 1. 1.–19. 10. 2026 (všechny dary straně v tomto období). Úplný přehled na stránce <a href="#/darci">Dárci</a>.</p>
      ${donorTable(D.darci.seznam.filter(r => r.typ !== "strana").sort((a, b) => (b.na_darovacich + b.na_uctech) - (a.na_darovacich + a.na_uctech)).slice(0, 15), false)}
      <h3>Kandidáti, kteří platili kampaň ze svého</h3>
      ${table([{ l: "Kandidát", v: c => c.prijmeni, h: c => `${sw(c)} ${cLink(c)} <span class="small">${vsShort(c)}</span>` }, { l: "Vlastní vklad", r: 1, v: c => c.prijmy.kandidat, h: c => kc(c.prijmy.kandidat) }, { l: "Výdaje celkem", r: 1, v: c => c.celkem, h: c => kc(c.celkem) }, { l: "1. kolo", r: 1, v: c => c.k1_proc, h: c => pct(c.k1_proc) }], self, { sort: 1, dir: -1 })}
      <p class="note">Jiří Vosecký vykazuje „vklady“ 640 tis. Kč, které ale přišly z účtu jiné osoby – v tabulce proto nejsou (viz <a href="#/anomalie">anomálie</a>).</p>
    </section>`;
    bindTips(app);
  }

  function pageObvod(n) {
    setNav("obvod");
    const o = O[n]; if (!o) return pageOverview();
    $("#navObv").value = n;
    const cs = o.kandidati.map(k => C[k]);
    const max = Math.max(...cs.map(c => c.celkem || 0), 1);
    const u = o.ucast || {};
    const win = C[o.vitez];
    const an = D.anomalie.filter(a => a.kandidati.some(k => o.kandidati.includes(k)));
    const accLink = key => { const a = A[key]; if (!a) return ""; return `<a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.nazev.length > 50 ? a.nazev.slice(0, 48) + "…" : a.nazev)}</a>${a.dostupny ? "" : " (nedostupný)"}${a.kandidati.length > 1 ? ` · sdílený pro ${a.kandidati.length} obvodů` : ""}`; };
    const card = c => {
      const p = c.prijmy || {}, d = c.darci;
      const months = Object.entries(c.mesice || {}); const mm = Math.max(...months.map(x => x[1]), 1);
      const flags = D.priznaky.filter(f => f.id === c.id);
      return `<div class="ccard" id="k${c.id}">
        <div><h3>${sw(c)} ${esc([c.tp, name(c), c.tz].filter(Boolean).join(" "))} ${res(c)}</h3>
          <div class="meta">${esc(c.vs_nazev)}<br>${c.vek} let · ${esc(c.povolani)} · ${esc(c.bydliste)}${c.typ === "K" ? `<br>Koalice: ${esc(c.strany.join(", "))} · navrhla ${esc(c.nstrana)}` : ""}</div>
          <table class="mini">
            <tr><td>1. kolo</td><td class="r">${nf.format(c.k1_hlasy)} hlasů · ${pct(c.k1_proc)}</td></tr>
            ${c.postup ? `<tr><td>2. kolo</td><td class="r">${nf.format(c.k2_hlasy)} hlasů · ${pct(c.k2_proc)}</td></tr>` : ""}
            <tr class="tot"><td>Výdaje kampaně</td><td class="r">${kc(c.celkem)}</td></tr>
            ${c.stav === "sdileny" ? `<tr><td>z toho přímo přiřazené obvodu</td><td class="r">${kc(c.prime)}</td></tr><tr><td>z toho podíl na sdílených výdajích</td><td class="r">${kc(c.sdilene)}</td></tr>` : ""}
            ${c.nepenezni ? `<tr><td>z toho nepeněžní plnění</td><td class="r">${kc(c.nepenezni)}</td></tr>` : ""}
            ${c.celkem != null ? `<tr><td>po 1. kole (od 11. 10.)</td><td class="r">${kc(c.po_1kole)}</td></tr><tr><td>podíl na výdajích v obvodu</td><td class="r">${pct(c.podil_vydaju)}</td></tr><tr><td>Kč na hlas (1. kolo)</td><td class="r">${c.kc_na_hlas == null ? "—" : nf.format(c.kc_na_hlas)}</td></tr>` : ""}
            <tr><td>Kvalita odhadu</td><td class="r">${qual(c)}</td></tr>
          </table>
          ${c.nepenezni_pozn ? `<p class="note">${esc(c.nepenezni_pozn)}</p>` : ""}
        </div>
        <div>
          <table class="mini">
            <tr><td colspan="2"><b>Příjmy na volební účet</b>${c.stav === "sdileny" ? " (podíl)" : ""}</td></tr>
            <tr><td>od strany / koaličních partnerů</td><td class="r">${kc(p.strana || 0)}</td></tr>
            <tr><td>dary</td><td class="r">${kc(p.dar || 0)}</td></tr>
            <tr><td>vlastní peníze kandidáta</td><td class="r">${kc(p.kandidat || 0)}</td></tr>
            ${p.neurceno ? `<tr><td>neidentifikovaný plátce</td><td class="r">${kc(p.neurceno)}</td></tr>` : ""}
          </table>
          ${months.length ? `<div class="mon">${months.map(([m, v]) => `<i style="height:${Math.max(0, v) / mm * 100}%;background:${col(c)}" data-tip="${esc(`${MES[m.slice(5)]}: ${kc(v)}`)}"></i>`).join("")}</div><div class="mon-l">${months.map(([m]) => `<span>${MES[m.slice(5)]}</span>`).join("")}</div>` : ""}
          <p class="note"><b>Dárci:</b> ${d ? (d.zaznamu ? `${d.darcu} dárců (${d.fo} fyzických, ${d.po} právnických osob${d.opakovane ? `, ${d.opakovane} opakovaně` : ""}) – <a href="${esc(d.url)}" target="_blank" rel="noopener">seznam ÚDHPSH</a>${d.kandidat_darcem ? ". Kandidát(ka) je sám/sama v seznamu dárců" : ""}${d.top_po && d.top_po.length ? `<br>Firmy a organizace: ${d.top_po.slice(0, 6).map(x => esc(x.d)).join("; ")}` : ""}` : esc(d.stav)) : "seznam nenalezen"}${d && d.pozde ? ` <span class="pill">oznámeno pozdě</span>` : ""}</p>
          <p class="note lnks"><b>Účet:</b> ${c.ucty.map(accLink).join("<br>") || "—"}</p>
          ${flags.map(f => `<p class="note">⚑ ${esc(f.text)}</p>`).join("")}
        </div></div>`;
    };
    app.innerHTML = `
      <div class="hero"><div><h1>${o.obvod} · ${esc(o.nazev)}</h1>
      <div class="sub">vítěz: <b>${esc(name(win))}</b> (${esc(win.vs_zkr)})${o.rozhodnuto_1k ? " – už v 1. kole" : ""} · účast ${pct(u["1"]?.ucast)}${u["2"] ? ` / ${pct(u["2"].ucast)}` : ""}</div></div>
      <label class="ctrl">jiný obvod <select class="obv-sel" onchange="location.hash='#/obvod/'+this.value">${D.obvody.map(x => `<option value="${x.obvod}" ${x.obvod === n ? "selected" : ""}>${x.obvod} ${esc(x.nazev)}</option>`).join("")}</select></label></div>
      ${o.neuplne ? `<div class="warnbox">Součet je neúplný – chybí data: ${o.chybi.map(k => esc(name(C[k]))).join(", ")}.</div>` : ""}
      <div class="tiles">
        <div class="tile ours"><span class="lbl">Utraceno v obvodu</span><span class="val">${mil(o.celkem)}<small>Kč</small></span><span class="d">${cs.length} kandidátů</span></div>
        <div class="tile"><span class="lbl">Na voliče</span><span class="val">${o.kc_na_volice == null ? "—" : nf.format(o.kc_na_volice)}<small>Kč</small></span><span class="d">${nf.format(u["1"]?.volici || 0)} voličů</span></div>
        <div class="tile"><span class="lbl">Na platný hlas</span><span class="val">${o.kc_na_hlas == null ? "—" : nf.format(o.kc_na_hlas)}<small>Kč</small></span><span class="d">1. kolo</span></div>
        <div class="tile"><span class="lbl">Výdaje vítěze</span><span class="val">${mil(win.celkem)}<small>${win.celkem == null ? "" : "Kč"}</small></span><span class="d">${o.vyhral_nejvetsi ? "největší rozpočet v obvodu" : "nebyl největší rozpočet"}</span></div>
      </div>
      <section class="card"><h2>Výdaje kandidátů</h2>
      <div class="stk">${cs.map(c => `<a class="stk-row" href="#k${c.id}" onclick="document.getElementById('k${c.id}').scrollIntoView({behavior:'smooth'});return false"><span class="nm">${esc(c.prijmeni)} <small>${vsShort(c)}</small></span><span class="stk-tr">${c.celkem == null ? `<i class="na" style="width:40px"></i>` : `<i style="width:${c.celkem / max * 100}%;background:${col(c)}" data-tip="${ctip(c)}"></i>`}</span><span class="v">${c.celkem == null ? "data chybí" : mil(c.celkem)}<small>${pct(c.k1_proc)}${c.postup ? " → " + pct(c.k2_proc) : ""}</small></span></a>`).join("")}</div>
      <p class="note">Pod částkou je výsledek 1. kola (→ 2. kola).</p></section>
      ${an.length ? `<section class="card int"><h2>Nestandardní situace v obvodu</h2>${an.map(anomCard).join("")}</section>` : ""}
      <section class="card"><h2>Kandidáti podrobně</h2>${cs.map(card).join("")}</section>`;
    bindTips(app);
    const h = location.hash.split("#")[2]; if (h) setTimeout(() => document.getElementById(h)?.scrollIntoView(), 50);
  }

  const DTYP = { fo: "fyzická osoba", po: "právnická osoba", strana: "politická strana" };
  const stranaShort = n => ({ "STAROSTOVÉ A NEZÁVISLÍ": "STAN", "Občanská demokratická strana": "ODS", "Svoboda a přímá demokracie (SPD)": "SPD", "Česká pirátská strana": "Piráti", "Strana zelených": "Zelení", "Komunistická strana Čech a Moravy": "KSČM" }[n] || n);
  function donorTable(rows, sortable = true, opt = {}) {
    const subjLinks = r => {
      const cs = r.kandidati.map(k => C[k]);
      const show = cs.slice(0, 6).map(c => `<a href="#/obvod/${c.obvod}#k${c.id}">${sw(c)} ${esc(c.prijmeni)}</a>`).join(", ");
      return `${show}${cs.length > 6 ? ` a dalších ${cs.length - 6}` : ""}<span class="small">${r.subjekty.map(x => esc(x.s.length > 45 ? x.s.slice(0, 43) + "…" : x.s) + (x.n > 1 ? ` (${x.n}×)` : "")).join(" · ")}</span>`;
    };
    return table([
      { l: "Dárce", v: r => r.jmeno, h: r => `<b>${esc(r.jmeno)}</b><span class="small">${esc([DTYP[r.typ], r.ico ? "IČO " + r.ico : "", r.misto].filter(Boolean).join(" · "))}</span>` },
      { l: "Subjektů", r: 1, v: r => r.n_subj },
      { l: "Záznamů", r: 1, v: r => r.zaznamu },
      { l: "Podpořil(a) kandidáty", v: r => r.kandidati.length, h: subjLinks },
      { l: "Darovací účty stran", r: 1, v: r => r.na_darovacich, h: r => r.na_darovacich ? `<b>${kc(r.na_darovacich)}</b>` + (r.darovaci_ucty.length ? `<span class="small">${r.darovaci_ucty.map(u => `${esc(stranaShort(u.strana))} ${mil(u.castka)} (${u.n}×)`).join("<br>")}</span>` : "") : "—" },
      { l: "Volební účty", r: 1, v: r => r.na_uctech, h: r => r.na_uctech ? kc(r.na_uctech) : "—" },
    ], rows, sortable ? { sort: opt.sort ?? 1, dir: -1 } : {});
  }

  function pageDarci() {
    setNav("darci");
    const L = D.darci.seznam;
    const cnt = t => L.filter(r => r.typ === t).length;
    const subjs = [...new Set(L.flatMap(r => r.subjekty.map(x => x.s)))].sort((a, b) => a.localeCompare(b, "cs"));
    app.innerHTML = `<div class="hero"><div><h1>Dárci</h1><div class="sub">Sloučené seznamy dárců všech kandidujících subjektů zveřejněné ÚDHPSH před 1. a 2. kolem.</div></div></div>
      <div class="warnbox">Seznamy dárců <b>neobsahují částky</b>. Ty jsou dohledány na transparentních účtech: <b>darovací (zvláštní) účty stran</b> – kam musí chodit všechny dary straně – a doplňkově volební účty (dary tam posílat nelze; pokud tam přesto přijdou, musí se vrátit). Platby jsou párovány podle jména plátce nebo textu platby za období 1. 1.–19. 10. 2026; jde o všechny dary straně v tomto období, nejen na senátní kampaň. U častých jmen je možná záměna, KB plátce nezobrazuje (ANO, Naše Česko, rEvoluce – jen podle textu) a ČSOB (KSČM, GEN) byla při stahování mimo provoz. Definitivní částky doplní zprávy o financování kampaně. Data narození fyzických osob neuvádíme.</div>
      <div class="tiles">
        <div class="tile ours"><span class="lbl">Dárců celkem</span><span class="val">${nf.format(L.length)}</span><span class="d">po sloučení duplicit</span></div>
        <div class="tile"><span class="lbl">Fyzické osoby</span><span class="val">${nf.format(cnt("fo"))}</span></div>
        <div class="tile"><span class="lbl">Právnické osoby</span><span class="val">${nf.format(cnt("po"))}</span><span class="d">firmy, spolky</span></div>
        <div class="tile"><span class="lbl">Politické strany</span><span class="val">${nf.format(cnt("strana"))}</span><span class="d">vklady do koalic</span></div>
        <div class="tile"><span class="lbl">Dohledané dary</span><span class="val">${mil(L.reduce((a, r) => a + r.na_darovacich + r.na_uctech, 0))}<small>Kč</small></span><span class="d">${nf.format(L.filter(r => r.na_darovacich || r.na_uctech).length)} dárců s platbou</span></div>
      </div>
      <div class="ctrl">
        <div class="seg" id="dtyp"><button data-t="" class="on">všichni</button><button data-t="po">právnické osoby</button><button data-t="fo">fyzické osoby</button><button data-t="strana">strany</button></div>
        <label>hledat <input id="dq" type="search" placeholder="jméno, firma, IČO, obec" style="font:inherit;font-size:15px;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);min-width:220px"></label>
        <label>subjekt <select id="ds"><option value="">všechny</option>${subjs.map(x => `<option>${esc(x)}</option>`).join("")}</select></label>
        <label class="chk"><input id="dm" type="checkbox"> jen dárci více subjektů</label>
        <label class="chk"><input id="dp" type="checkbox"> jen s dohledanou platbou</label>
      </div>
      <p class="note" id="dn"></p><div id="dt"></div>
      <section class="card"><h2>Darovací účty stran</h2><p class="lead">Všechny příchozí platby na darovací účty stran, které kandidovaly samostatně nebo v koalici, 1. 1.–19. 10. 2026. „Haléřové“ = platby pod 1 Kč, které slouží jen jako vzkaz.</p>
      ${table([{ l: "Strana", v: o => o.nazev, h: o => `<a href="${esc(o.url)}" target="_blank" rel="noopener">${esc(o.nazev.slice(0, 60))}</a><span class="small">${esc(o.ucet)}</span>` }, { l: "Příchozích plateb", r: 1, v: o => o.prijmu, h: o => nf.format(o.prijmu) }, { l: "Částka", r: 1, v: o => o.castka, h: o => kc(o.castka) }, { l: "Haléřové", r: 1, v: o => o.halerove, h: o => o.halerove ? nf.format(o.halerove) : "" }], D.darovaci, { sort: 2, dir: -1 })}
      <p class="note">Bez darovacího účtu v registru ÚDHPSH („dosud nedodán“): Srdcem a Rozumem, Hnutí Hlas regionů. ČSOB (KSČM, GEN) byla 19. 10. 2026 nedostupná.</p></section>`;
    let typ = "";
    const draw = () => {
      const q = $("#dq").value.trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, ""), sj = $("#ds").value, m = $("#dm").checked, pp = $("#dp").checked;
      const rows = L.filter(r => (!typ || r.typ === typ) && (!sj || r.subjekty.some(x => x.s === sj)) && (!m || r.n_subj > 1) && (!pp || r.na_darovacich || r.na_uctech) &&
        (!q || (r.jmeno + " " + r.ico + " " + r.misto).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").includes(q)));
      $("#dn").textContent = `Zobrazeno ${nf.format(rows.length)} dárců` + (rows.length > 400 ? " (prvních 400 – upřesněte filtr)" : "");
      rows.sort((a, b) => (b.na_darovacich + b.na_uctech) - (a.na_darovacich + a.na_uctech) || b.n_subj - a.n_subj);
      $("#dt").innerHTML = donorTable(rows.slice(0, 400), true, { sort: 4 });
    };
    $("#dtyp").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return; typ = b.dataset.t; $("#dtyp").querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b)); draw(); });
    $("#dq").addEventListener("input", draw); $("#ds").onchange = draw; $("#dm").onchange = draw; $("#dp").onchange = draw;
    const pre = decodeURIComponent((location.hash.split("?q=")[1] || ""));
    if (pre) $("#dq").value = pre;
    draw();
  }

  function anomCard(a) {
    const SEV = { vysoka: "vysoká závažnost", stredni: "střední", nizka: "nízká" };
    return `<div class="anom ${a.zavaznost}"><h3>${esc(a.nazev)} <span class="sev">${SEV[a.zavaznost]}</span></h3><p>${esc(a.text)}</p>${a.kandidati.length ? `<div class="who">${a.kandidati.map(k => C[k]).map(c => `<a href="#/obvod/${c.obvod}#k${c.id}">${sw(c)} ${esc(c.prijmeni)} (${c.obvod})</a>`).join("")}</div>` : ""}</div>`;
  }

  function pageAnomalie() {
    setNav("anomalie");
    const fl = D.priznaky.filter(f => ["sdilene", "vlastni_zdroje"].includes(f.typ));
    app.innerHTML = `<div class="hero"><div><h1>Nestandardní situace</h1><div class="sub">Co je na účtech, v registrech a ve zprávách ÚDHPSH neobvyklé. Ověřeno ručně k 19. 10. 2026.</div></div></div>
      ${D.anomalie.map(anomCard).join("")}
      <section class="card"><h2>Automatické příznaky</h2><p class="lead">Kandidáti, u nichž většina výdajů nejde přiřadit k obvodu, nebo kteří vložili výraznou částku z vlastních zdrojů.</p>
      ${table([{ l: "Kandidát", v: f => C[f.id].prijmeni, h: f => `${sw(C[f.id])} ${cLink(C[f.id])} <span class="small">${vsShort(C[f.id])}</span>` }, { l: "Obvod", v: f => C[f.id].obvod }, { l: "Příznak", v: f => f.text }], fl)}</section>
      <section class="card"><h2>Dárci u více subjektů</h2><p class="lead">Stejný dárce (podle jména a data narození / IČO) v seznamech více kandidujících subjektů. Jména fyzických osob neuvádíme.</p>
      ${table([{ l: "Dárce", v: x => x.darce }, { l: "Počet subjektů", r: 1, v: x => x.subjekty.length }, { l: "Subjekty", v: x => x.subjekty.join(" · ") }], D.darci.vice_subjektu, { sort: 1, dir: -1 })}</section>`;
    bindTips(app);
  }

  function pageStrany() {
    setNav("strany");
    const bl = D.bloky.slice().sort((a, b) => b.celkem - a.celkem);
    const mb = Math.max(...bl.map(b => b.celkem));
    const subj = D.subjekty.map(s => ({ ...s, c: C[s.kandidati[0]] }));
    const ms = Math.max(...subj.map(s => s.celkem));
    const coal = D.ucty.filter(a => a.druh === "koalice" && a.dostupny);
    app.innerHTML = `<div class="hero"><div><h1>Výdaje podle stran a koalic</h1><div class="sub">${D.subjekty.length} kandidujících subjektů, z toho ${D.subjekty.filter(s => s.typ === "K").length} koalic. Tři pohledy: bloky, subjekty a jednotlivé strany.</div></div></div>
      <nav class="toc"><a href="#p-bloky">Bloky</a><a href="#p-subj">Kandidující subjekty</a><a href="#p-strany">Strany v koalicích</a><a href="#p-vklady">Kdo platil koalice</a></nav>
      <section class="card" id="p-bloky"><h2>Politické bloky</h2>
      <p class="lead">Koalice jsou přiřazeny podle strany, která kandidáta navrhla (např. Padevět – navrhl STAN, Šimetka – ODS). Barvy odpovídají povolební analýze Brno 2026.</p>
      ${table([
        { l: "Blok", v: b => b.nazev, h: b => `<i class="sw" style="background:${b.barva};display:inline-block"></i> ${esc(b.nazev)}` },
        { l: "Kandidátů", r: 1, v: b => b.kandidatu },
        { l: "Výdaje", r: 1, v: b => b.celkem, h: b => inbar(b.celkem, mb, b.barva) + (b.neznamych ? `<span class="small">bez dat: ${b.neznamych}</span>` : "") },
        { l: "Na kandidáta", r: 1, v: b => b.celkem / Math.max(1, b.kandidatu - b.neznamych), h: b => kc(b.celkem / Math.max(1, b.kandidatu - b.neznamych)) },
        { l: "Hlasy 1. kolo", r: 1, v: b => b.hlasy, h: b => nf.format(b.hlasy) },
        { l: "Kč / hlas", r: 1, v: b => b.celkem / b.hlasy, h: b => nf.format(Math.round(b.celkem / b.hlasy)) },
        { l: "Do 2. kola", r: 1, v: b => b.postup },
        { l: "Mandáty", r: 1, v: b => b.mandaty },
        { l: "Kč / mandát", r: 1, v: b => b.mandaty ? b.celkem / b.mandaty : null, h: b => b.mandaty ? mil(b.celkem / b.mandaty) : "—" },
      ], bl, { sort: 2, dir: -1 })}</section>
      <section class="card" id="p-subj"><h2>Kandidující subjekty</h2><p class="lead">Každá strana, koalice a nezávislý kandidát, jak byli zaregistrováni. Koalice se stejným složením v různých obvodech jsou samostatné subjekty.</p>
      ${table([
        { l: "Subjekt", v: s => s.nazev, h: s => `${sw(s.c)} ${esc(s.nazev.length > 80 ? s.nazev.slice(0, 78) + "…" : s.nazev)} <span class="small">${s.typ === "K" ? "koalice: " + esc(s.strany.join(", ")) : s.typ === "N" ? "nezávislý" : "strana/hnutí"}</span>` },
        { l: "Kandidátů", r: 1, v: s => s.kandidatu },
        { l: "Výdaje", r: 1, v: s => s.celkem, h: s => inbar(s.celkem, ms, col(s.c)) + (s.neznamych ? `<span class="small">bez dat: ${s.neznamych}</span>` : "") },
        { l: "Na kandidáta", r: 1, v: s => s.celkem / Math.max(1, s.kandidatu - s.neznamych), h: s => kc(s.celkem / Math.max(1, s.kandidatu - s.neznamych)) },
        { l: "Hlasy", r: 1, v: s => s.hlasy, h: s => nf.format(s.hlasy) },
        { l: "2. kolo", r: 1, v: s => s.postup },
        { l: "Mandáty", r: 1, v: s => s.mandaty },
      ], subj, { sort: 2, dir: -1 })}</section>
      <section class="card" id="p-strany"><h2>Jednotlivé strany: samostatně a v koalicích</h2>
      <p class="lead">„Koalice plně“ = celé výdaje všech koalic, kde strana byla členem (výdaje se tak započítávají vícekrát). „Poměrně“ = výdaje koalice rozdělené rovným dílem mezi členy + samostatné kandidatury. „Vklady do koalic“ = skutečné převody strany na koaliční účty podle protiúčtu.</p>
      ${table([
        { l: "Strana", v: p => p.strana },
        { l: "Samostatně", r: 1, v: p => p.samostatne },
        { l: "V koalici", r: 1, v: p => p.v_koalici },
        { l: "Výdaje samostatně", r: 1, v: p => p.vydaje_samostatne, h: p => kc(p.vydaje_samostatne) },
        { l: "Koalice plně", r: 1, v: p => p.vydaje_koalice_plne, h: p => kc(p.vydaje_koalice_plne) },
        { l: "Poměrně", r: 1, v: p => p.vydaje_pomerne, h: p => `<b>${kc(p.vydaje_pomerne)}</b>` },
        { l: "Vklady do koalic", r: 1, v: p => p.vklady_do_koalic, h: p => p.vklady_do_koalic ? kc(p.vklady_do_koalic) : "—" },
        { l: "Mandáty (sam. + koal.)", r: 1, v: p => p.mandaty_samostatne + p.mandaty_koalice, h: p => `${p.mandaty_samostatne} + ${p.mandaty_koalice}` },
      ], D.strany.filter(p => p.samostatne + p.v_koalici > 0), { sort: 5, dir: -1 })}</section>
      <section class="card" id="p-vklady"><h2>Kdo platil koaliční kampaně</h2>
      <p class="lead">Příchozí převody stran na koaliční volební účty podle názvu protiúčtu. Majitelem koaličního účtu je vždy jedna ze stran (sloupec Účet vede).</p>
      ${table([
        { l: "Koalice", v: a => a.nazev, h: a => { const c = C[a.kandidati[0]]; return c ? `${sw(c)} ${cLink(c)} <span class="small">${esc(a.nazev.slice(0, 60))} · ${esc(a.slozeni)}</span>` : esc(a.nazev); } },
        { l: "Účet vede", v: a => a.owner },
        { l: "Vklady stran", v: a => Object.values(a.zdroje).reduce((x, y) => x + y, 0), r: 1, h: a => Object.entries(a.zdroje).sort((x, y) => y[1] - x[1]).map(([k, v]) => `${esc(k)} ${mil(v)}`).join("<br>") },
        { l: "Výdaje", r: 1, v: a => a.vydaje, h: a => kc(a.vydaje) },
      ], coal, { sort: 3, dir: -1 })}</section>`;
    bindTips(app);
  }

  function pageKandidati() {
    setNav("kandidati");
    const K = D.kandidati;
    const max = Math.max(...K.map(c => c.celkem || 0));
    app.innerHTML = `<div class="hero"><div><h1>Všichni kandidáti</h1><div class="sub">${K.length} kandidátů, řazení klikem na záhlaví.</div></div></div>
      <div class="ctrl"><label>blok <select id="fb"><option value="">všechny</option>${D.bloky.map(b => `<option value="${b.id}">${esc(b.nazev)}</option>`).join("")}</select></label>
      <label>výsledek <select id="fr"><option value="">všichni</option><option value="z">zvolení</option><option value="p">ve 2. kole</option><option value="n">nepostoupili</option></select></label></div>
      <div id="kt"></div>`;
    const draw = () => {
      const b = $("#fb").value, r = $("#fr").value;
      const rows = K.filter(c => (!b || c.blok === b) && (!r || (r === "z" ? c.zvolen : r === "p" ? c.postup : !c.postup && !c.zvolen)));
      $("#kt").innerHTML = table(candCols(max, [{ l: "Výsledek", v: c => c.zvolen ? 2 : c.postup ? 1 : 0, h: res }, { l: "Sdíleno", r: 1, v: c => c.podil_sdilenych, h: c => c.stav === "sdileny" ? pct(c.podil_sdilenych * 100) : "" }]), rows, { sort: 2, dir: -1 });
    };
    $("#fb").onchange = draw; $("#fr").onchange = draw; draw();
  }

  function pageMetodika() {
    setNav("metodika");
    const s = D.souhrn;
    const acc = D.ucty;
    app.innerHTML = `<div class="hero"><div><h1>Metodika a zdroje</h1><div class="sub">Jak čísla vznikla a kde mají limity.</div></div></div>
    <section class="card"><h2>Zdroje</h2><ul class="find">
      <li>Výsledky a kandidáti: <a href="https://volby.gov.cz/opendata/se2026/se2026_opendata.htm">otevřená data ČSÚ</a> (registr kandidátů a číselníky stav 17. 10. 2026 po 2. kole).</li>
      <li>Seznamy dárců před 1. a 2. kolem: <a href="https://zpravy.udh.gov.cz/public/report/sponzori.php?volby=s2026&seq=1">ÚDHPSH – 1. kolo</a>, <a href="https://zpravy.udh.gov.cz/public/report/sponzori.php?volby=s2026&seq=2">2. kolo</a>. Neobsahují částky.</li>
      <li>Registr volebních účtů ÚDHPSH (strany a hnutí, koalice, nezávislí) a z něj transparentní účty u Fio (56), KB (8), České spořitelny (4), ČSOB (3), Raiffeisenbank (2), Moneta (2) a UniCredit (1) – pohyby od 1. 1. 2026 do 19. 10. 2026. ČSOB a UniCredit chrání účty proti robotům, jejich data byla stažena ručně přes prohlížeč.</li>
      <li>Darovací (zvláštní) účty stran: <a href="https://registrace.udh.gov.cz/public/seznam.php?token=eb79c36108cb30b2f4e93702e3b9472135363fc4">registr ÚDHPSH</a> – 62 stran, které kandidovaly samostatně nebo v koalici, pohyby 1. 1.–19. 10. 2026. Slouží k dohledání částek u dárců ze seznamů (strana <a href="#/darci">Dárci</a>).</li>
      <li>Zprávy o financování kampaně: <a href="https://zpravy.udh.gov.cz/zpravy/s2026">zpravy.udh.gov.cz</a> – zatím 6 zpráv, všechny podané před volbami; použity jen pro nepeněžní plnění a kontrolu.</li>
    </ul></section>
    <section class="card"><h2>Jak se počítají výdaje</h2><ul class="find">
      <li><b>Výdaj</b> = odchozí platba z volebního účtu (včetně bankovních poplatků) mínus příchozí vratky přeplatků a dobropisy. Nezapočítává se vracení darů (dary na volební účet zákon nepřipouští, strany je musí vrátit – typicky s výzvou poslat je na darovací účet), mylných plateb ani převody peněz zpět straně.</li>
      <li><b>Vlastní účet</b> (koalice, nezávislí, strany s jedním kandidátem): všechny výdaje patří kandidátovi – odhad <span class="q vysoka">vysoká</span> kvalita.</li>
      <li><b>Sdílený účet</b> (strana s více kandidáty): každá platba se přiřazuje k obvodu postupně podle (1) specifického symbolu – ANO, STAN a KDU-ČSL dávají do SS číslo obvodu, SPD 100+obvod; (2) čísla obvodu v popisu („24/…“ u ODS, „SS 60“, „VO 81“, „75 - …“); (3) příjmení kandidáta; (4) města v obvodu (např. „SPlzeň_“ u SEN 21). Platby, které takto přiřadit nejdou (centrální kampaň, grafický manuál, průzkumy), se dělí rovným dílem mezi kandidáty účtu. Pokud je takto rozdělena méně než 40 % výdajů kandidáta, je odhad <span class="q stredni">střední</span>, jinak <span class="q nizka">nízký</span>.</li>
      <li>Ruční opravy přiřazení jsou v souboru <code>config/prirazeni.json</code>. Celkem je rovným dílem rozpočítáno ${mil(s.sdilene_celkem)} Kč, z toho 7,1 mil. Kč tvoří centrální platby SPD.</li>
      <li><b>Příjmy</b> se dělí na převody strany/koaličních partnerů, dary, vlastní peníze kandidáta (plátcem je přímo kandidát) a neidentifikované (banka plátce nezobrazuje). U sdílených účtů se nepřiřazené příjmy dělí poměrem výdajů.</li>
      <li><b>Nepeněžní plnění</b> (pronájem obytného vozu u ČZS, billboard u rEvoluce) je ze zpráv ÚDHPSH přičteno k výdajům.</li>
    </ul></section>
    <section class="card"><h2>Limity</h2><ul class="find">
      <li>Data jsou stav k 19. 10. 2026, dva dny po 2. kole. Část faktur se proplatí později; konečné zprávy o financování podají subjekty až v zákonné lhůtě.</li>
      <li>Kampaň placená z centrálních účtů stran mimo volební účet (což zákon nepřipouští) v datech není. Stejně tak nejsou vidět dary posílané na centrální účty stran.</li>
      ${s.nedostupnych.length ? `<li>Nedostupné účty: ${s.nedostupnych.map(k => esc(name(C[k]))).join(", ")}.</li>` : ""}
      <li>Seznamy dárců v 2. kole jsou kumulativní; použita je vždy novější verze.</li>
    </ul></section>
    <section class="card"><h2>Volební účty</h2>${table([
      { l: "Subjekt", v: a => a.nazev, h: a => `<a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.nazev.slice(0, 70))}</a>` },
      { l: "Druh", v: a => a.druh },
      { l: "Kandidátů", r: 1, v: a => a.kandidati.length },
      { l: "Pohybů", r: 1, v: a => a.n_tx, h: a => a.dostupny ? nf.format(a.n_tx) : "nedostupné" },
      { l: "Příjmy", r: 1, v: a => a.prijmy, h: a => kc(a.prijmy) },
      { l: "Výdaje", r: 1, v: a => a.vydaje, h: a => kc(a.vydaje) },
      { l: "Zůstatek", r: 1, v: a => a.zustatek, h: a => a.zustatek == null ? "—" : kc(a.zustatek) },
    ], acc, { sort: 5, dir: -1 })}
    <p class="note">Data a skripty: <a href="https://github.com/michalberg/senat-2026">github.com/michalberg/senat-2026</a>.</p></section>`;
    bindTips(app);
  }

  // ---------- router ----------
  function route() {
    tip.hidden = true;
    const h = location.hash.replace(/^#\/?/, "").split("#")[0].split("?")[0];
    const [p, a] = h.split("/");
    if (p === "obvod") pageObvod(+a);
    else if (p === "strany") pageStrany();
    else if (p === "kandidati") pageKandidati();
    else if (p === "anomalie") pageAnomalie();
    else if (p.startsWith("darci")) pageDarci();
    else if (p === "metodika") pageMetodika();
    else pageOverview();
    if (!location.hash.split("#")[2]) window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", route);
  // kotvy v obsahu (#s-...) nesmí rozbít router
  document.addEventListener("click", e => {
    const a = e.target.closest("a[href^='#s-'],a[href^='#p-']");
    if (a) { e.preventDefault(); document.getElementById(a.getAttribute("href").slice(1))?.scrollIntoView({ behavior: "smooth" }); }
  });

  $("#themeBtn").addEventListener("click", () => {
    const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = t; try { localStorage.setItem("s26-theme", t); } catch (e) {}
    $("#themeBtn").textContent = t === "dark" ? "světlý režim" : "tmavý režim";
    if (B.pirati) { B.pirati.barva = t === "dark" ? "#f0efec" : "#111111"; route(); }
  });

  fetch("data.json").then(r => r.json()).then(d => {
    D = d;
    d.kandidati.forEach(c => C[c.id] = c);
    d.obvody.forEach(o => O[o.obvod] = o);
    d.bloky.forEach(b => B[b.id] = b);
    d.ucty.forEach(a => A[a.key] = a);
    if (document.documentElement.dataset.theme === "dark") { B.pirati.barva = "#f0efec"; $("#themeBtn").textContent = "světlý režim"; }
    $("#navObv").innerHTML = `<option value="">vyberte</option>` + d.obvody.map(o => `<option value="${o.obvod}">${o.obvod} ${esc(o.nazev)}</option>`).join("");
    $("#navObv").onchange = e => { if (e.target.value) location.hash = "#/obvod/" + e.target.value; };
    route();
  }).catch(e => { app.innerHTML = `<p class="err">Data se nepodařilo načíst: ${esc(e.message)}</p>`; });
})();
