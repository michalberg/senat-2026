"""Souhrn darovacích účtů vybraných stran: státní příspěvky, strany/organizace, dary FO a PO (počty, součty, průměry, mediány)."""
import json, re, unicodedata, statistics as S, collections, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def n(s): return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
P = [('00409740', 'Zelení'), ('71339698', 'Piráti'), ('00442704', 'KDU-ČSL'), ('16192656', 'ODS'), ('26673908', 'STAN'), ('71339728', 'TOP 09'),
     ('71443339', 'ANO'), ('04134940', 'SPD'), ('05989175', 'Motoristé')]
STATE = re.compile(r'424/1991|uhradu volebnich nakladu|prispevek na cinnost|prispevekna cinnost|na cinnost za \d')
PARTY_CP = re.compile(r'strana|hnuti|^kdu|kdu-csl|top 09|starostove a nezavisli|piratsk|obcanska demokratick|ano 2011|svoboda a prima|motoriste|demokraticky klub|zmena pro|idealist')
SETTLE = re.compile(r'koalicni podil|vyrovnani|za mandat|koalicni smlouv|memorand|prevod zustatku')
PO = re.compile(r's\.? ?r\.? ?o|a\. ?s\.|\ba\.s\b|spol\.|\bz\. ?s\.|v\. ?o\. ?s|k\. ?s\.|druzstvo|\bse\b|o\. ?p\. ?s|o\.s\b|z\. ?u\.|nadace|nadacni|spolek|corporation|holding|investments?\b|group|gmbh|ltd|\bs\.a\.|\binc\b|\bsro\b|\bas$')
out = {}
for ic, nm in P:
    d = json.load(open(os.path.join(ROOT, f'data/raw/darovaci/tx/{ic}.json'), encoding='utf-8'))
    own = n(d['nazev'])[:14]
    cat = collections.defaultdict(list); party = collections.defaultdict(lambda: [0, 0, ''])
    for t in d['tx']:
        a = t['amount']
        if a <= 0: continue
        if a < 1: cat["halerove"].append(a); continue
        cp = n(t['counterparty']).strip(); msg = n(t['message'])
        if STATE.search(cp + ' ' + msg) or cp == 'mf': cat['stat'].append(a); continue
        if cp and own and own in cp: k = 'vlastni'
        elif (cp and PARTY_CP.search(cp) and not PO.search(cp.replace('z.s.', ''))) or SETTLE.search(msg) or (cp and 'demokraticky klub' in cp): k = 'strany'
        elif not cp:  # KB nezobrazuje plátce
            k = 'po' if PO.search(msg) or re.search(r'\bico\b', msg) else ('neurceno' if not msg.strip() else 'fo_kb')
        else: k = 'po' if PO.search(cp) or re.search(r'\bico\b', cp) else 'fo'
        cat[k].append(a)
        if k in ('strany', 'vlastni'):
            g = party[(t['counterparty'].strip() or '(bez plátce)') + (' [vlastní účet]' if k == 'vlastni' else '')]; g[0] += a; g[1] += 1; g[2] = g[2] or t['message'][:70]
    out[nm] = (cat, party, d['ucet'])

f = lambda x: f"{x:,.0f}".replace(',', ' ')
def st(L): return (len(L), sum(L), S.mean(L) if L else 0, S.median(L) if L else 0)
for lbl, keys in (('FYZICKÉ OSOBY', ('fo', 'fo_kb')), ('PRÁVNICKÉ OSOBY', ('po',))):
    print(f"\n{lbl}\n{'Strana':10} {'počet':>6} {'součet':>13} {'průměr':>9} {'medián':>8}")
    for nm, (cat, _, _) in out.items():
        L = sum((cat[k] for k in keys), []); c, s_, m, md = st(L)
        print(f"{nm:10} {c:>6} {f(s_):>13} {f(m):>9} {f(md):>8}")
print("\nOSTATNÍ KATEGORIE\nStrana      státní příspěvky   strany/org.   vlastní převody   neurčeno(KB)  haléřové")
for nm, (cat, _, _) in out.items():
    print(f"{nm:10} {f(sum(cat['stat'])):>17} {f(sum(cat['strany'])):>13} {f(sum(cat['vlastni'])):>17} {f(sum(cat['neurceno'])):>13} {len(cat['halerove']):>9}")
if '-o' in sys.argv:
    print('\nOD STRAN A ORGANIZACÍ')
    for nm, (_, party, _) in out.items():
        print(f"== {nm}: {f(sum(v[0] for v in party.values()))} Kč")
        for k, v in sorted(party.items(), key=lambda x: -x[1][0])[:10]: print(f"   {f(v[0]):>11} ({v[1]}×) {k[:45]} | {v[2]}")

# ---------- malí dárci: struktura darů fyzických osob ----------
if '-m' in sys.argv:
    BANDS = [(1, 100), (100, 500), (500, 1000), (1000, 5000), (5000, 50000), (50000, 10**9)]
    BL = ['<100', '100–499', '500–999', '1–5 tis.', '5–50 tis.', '50 tis.+']
    print('\nDARY FO PODLE VÝŠE PLATBY (podíl počtu plateb / podíl částky)')
    print(f"{'Strana':10} " + ' '.join(f"{b:>15}" for b in BL))
    for ic, nm in P:
        d = json.load(open(os.path.join(ROOT, f'data/raw/darovaci/tx/{ic}.json'), encoding='utf-8'))
        cat, _, _ = out[nm]
        L = cat['fo'] + cat['fo_kb']; tot = sum(L); cnt = len(L)
        cells = []
        for lo, hi in BANDS:
            x = [a for a in L if lo <= a < hi]
            cells.append(f"{len(x)/cnt*100:5.1f}% / {sum(x)/tot*100:5.1f}%")
        print(f"{nm:10} " + ' '.join(f"{c:>15}" for c in cells))
    print('\nUNIKÁTNÍ DÁRCI FO (podle jména plátce), pravidelní = dary ve 3+ různých měsících')
    print(f"{'Strana':10} {'dárců':>6} {'plateb/dárce':>12} {'pravidelných':>12} {'jejich podíl Kč':>15} {'typ. měs. částka':>16} {'roční medián/dárce':>18} {'top 10 % dárců':>15} {'dárci do 1000 Kč/rok':>20}")
    for ic, nm in P:
        if nm == 'ANO': continue
        d = json.load(open(os.path.join(ROOT, f'data/raw/darovaci/tx/{ic}.json'), encoding='utf-8'))
        own = n(d['nazev'])[:14]
        per = collections.defaultdict(list)
        for t in d['tx']:
            a = t['amount']; cp = n(t['counterparty']).strip(); msg = n(t['message'])
            if a < 1 or not cp or STATE.search(cp + ' ' + msg) or cp == 'mf' or (own and own in cp): continue
            if (PARTY_CP.search(cp) and not PO.search(cp)) or SETTLE.search(msg) or PO.search(cp) or re.search(r'\bico\b', cp): continue
            key = ' '.join(sorted(re.sub(r'\b(ing|mgr|bc|judr|mudr|phdr|rndr|dis|phd|mba)\b|[^a-z ]', ' ', cp).split()))
            per[key].append((t['date'][:7], a))
        tots = sorted((sum(a for _, a in v) for v in per.values()), reverse=True)
        reg = {k: v for k, v in per.items() if len({m for m, _ in v}) >= 3}
        top = sum(tots[:max(1, len(tots) // 10)]) / sum(tots) * 100
        typ = S.median([S.median([a for _, a in v]) for v in reg.values()]) if reg else 0
        print(f"{nm:10} {len(per):>6} {sum(len(v) for v in per.values())/len(per):>12.1f} {len(reg):>12} {sum(a for v in reg.values() for _, a in v)/sum(tots)*100:>14.1f}% {f(typ):>16} {f(S.median(tots)):>18} {top:>14.1f}% {sum(1 for x in tots if x <= 1000)/len(tots)*100:>19.1f}%")
    print('\nDARY FO PODLE MĚSÍCŮ (počet plateb)')
    print(f"{'Strana':10} " + ' '.join(f"{m:>6}" for m in ['led', 'úno', 'bře', 'dub', 'kvě', 'čvn', 'čvc', 'srp', 'zář', 'říj*']))
    for ic, nm in P:
        d = json.load(open(os.path.join(ROOT, f'data/raw/darovaci/tx/{ic}.json'), encoding='utf-8'))
        own = n(d['nazev'])[:14]; c = collections.Counter()
        for t in d['tx']:
            a = t['amount']; cp = n(t['counterparty']).strip(); msg = n(t['message'])
            if a < 1 or STATE.search(cp + ' ' + msg) or cp == 'mf': continue
            if cp and ((PARTY_CP.search(cp) and not PO.search(cp)) or PO.search(cp) or (own and own in cp)): continue
            if a < 5000: c[t['date'][5:7]] += 1
        print(f"{nm:10} " + ' '.join(f"{c[f'{m:02d}']:>6}" for m in range(1, 11)))
