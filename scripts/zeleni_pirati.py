"""Porovnání drobného a pravidelného dárcovství Zelených a Pirátů (darovací účty 1. 1.–19. 10. 2026)."""
import json, re, unicodedata, statistics as S, collections, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def n(s): return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
STATE = re.compile(r'424/1991|uhradu volebnich nakladu|prispevek na cinnost|na cinnost za \d')
PROC = re.compile(r'global payments|stripe|gopay|comgate|darujme|paypal|akceptace platebnich karet')
PO = re.compile(r'^sen 21|volt|fakt|autocamp|s\.? ?r\.? ?o|a\. ?s\.|spol\.|\bz\. ?s\.|o\.s\b|druzstvo|spolek|nadace|strana|hnuti|kdu|top 09|starostove|obcanska demokrat|demokraticky klub|idealist|zmena pro')
f = lambda x: f"{x:,.0f}".replace(',', ' ')
D = {}; P_ = {}
for ic, nm in (('00409740', 'Zelení'), ('71339698', 'Piráti')):
    d = json.load(open(os.path.join(ROOT, f'data/raw/darovaci/tx/{ic}.json'), encoding='utf-8'))
    per = collections.defaultdict(list); proc = collections.Counter(); procn = collections.Counter()
    for t in d['tx']:
        a = t['amount']; cp = n(t['counterparty']).strip()
        if a >= 1 and PROC.search(cp + ' ' + n(t['message'])): proc[t['counterparty'].strip()[:25]] += a; procn[t['counterparty'].strip()[:25]] += 1; continue
        if 'za stranu' in n(t['message']) or 'koalic' in n(t['message']): continue
        if a < 1 or not cp or STATE.search(cp + ' ' + n(t['message'])) or cp == 'mf' or PO.search(cp): continue
        key = ' '.join(sorted(re.sub(r'\b(ing|mgr|bc|judr|mudr|phdr|rndr|dis|phd|mba|mga|doc|prof)\b|[^a-z ]', ' ', cp).split()))
        per[key].append((t['date'], a, t['message']))
    D[nm] = per; P_[nm] = (proc, procn)

months = [f'2026-{m:02d}' for m in range(1, 11)]
for nm, per in D.items():
    allp = [a for v in per.values() for _, a, _ in v]
    reg = {k: v for k, v in per.items() if len({d[:7] for d, _, _ in v}) >= 3}  # pravidelný = dával aspoň ve 3 různých měsících
    regsum = sum(a for v in reg.values() for _, a, _ in v)
    mon_amt = collections.Counter(round(S.median([a for _, a, _ in v])) for v in reg.values())
    tots = sorted((sum(a for _, a, _ in v) for v in per.values()), reverse=True)
    big = [(k, sum(a for _, a, _ in v), len(v)) for k, v in per.items()]
    big.sort(key=lambda x: -x[1])
    first = collections.Counter(min(d for d, _, _ in v)[:7] for v in per.values())
    active = {m: sum(1 for v in per.values() if any(d.startswith(m) for d, _, _ in v)) for m in months}
    mrr = {m: sum(a for v in reg.values() for d, a, _ in v if d.startswith(m)) for m in months}
    print(f"\n===== {nm} =====")
    print('platby kartou/online souhrnně (nelze rozlišit dárce):', '; '.join(f"{k} {f(v)} Kč ({P_[nm][1][k]}×)" for k, v in P_[nm][0].items()) or '—')
    gw = sum(P_[nm][0].values())
    print(f"FO celkem vč. bran: {f(sum(allp)+gw)} Kč; pravidelní = {regsum/(sum(allp)+gw)*100:.0f} % všech darů FO")
    print(f"dárců FO: {len(per)}, plateb: {len(allp)}, součet: {f(sum(allp))} Kč, medián platby {f(S.median(allp))}, medián dárce/rok {f(S.median(tots))}")
    print(f"pravidelní (3+ různých měsíců): {len(reg)} = {len(reg)/len(per)*100:.0f} % dárců, {f(regsum)} Kč = {regsum/sum(allp)*100:.0f} % částky; medián ročně/dárce {f(S.median([sum(a for _, a, _ in v) for v in reg.values()]))}")
    print('typická měsíční částka pravidelných:', ', '.join(f"{k} Kč: {v}×" for k, v in sorted(mon_amt.items(), key=lambda x: -x[1])[:8]))
    print('aktivních dárců po měsících:', ' '.join(f"{m[5:]}:{active[m]}" for m in months))
    print('pravidelní – příjem po měsících:', ' '.join(f"{m[5:]}:{f(mrr[m])}" for m in months))
    print('noví dárci po měsících (1. platba v roce):', ' '.join(f"{m[5:]}:{first[m]}" for m in months))
    shares = [(10, sum(tots[:max(1, len(tots)//10)])), (1, sum(tots[:max(1, len(tots)//100)]))]
    print(f"top 1 % dárců: {shares[1][1]/sum(tots)*100:.0f} % částky; top 10 %: {shares[0][1]/sum(tots)*100:.0f} %; dárci do 1 000 Kč/rok: {sum(1 for x in tots if x<=1000)} ({sum(1 for x in tots if x<=1000)/len(tots)*100:.0f} %), dávají {sum(x for x in tots if x<=1000)/sum(tots)*100:.1f} % částky")
    print('největší dárci FO (součet, počet plateb, ukázka zprávy):')
    for k, s_, c in big[:10]:
        msg = per[k][0][2][:60]
        print(f"   {f(s_):>10} ({c}×) {k[:30]} | {msg}")
both = set(D['Zelení']) & set(D['Piráti'])
print(f"\nDárci obou stran (stejné jméno): {len(both)}")
