"""Dary Zeleným: převody z darovacího účtu (Fio) + dary kartou z veřejné tabulky strany (Action Network/Stripe)."""
import csv, json, re, collections, statistics as S, unicodedata, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def n(s): return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower().strip()
def key(s): return ' '.join(sorted(re.sub(r'\b(ing|mgr|bc|judr|mudr|phdr|rndr|dis|phd|mba|mga|doc|prof)\b|[^a-z ]', ' ', n(s)).split()))
f = lambda x: f"{x:,.0f}".replace(',', ' ')
STATE = re.compile(r'424/1991|uhradu volebnich nakladu|prispevek na cinnost')
NONFO = re.compile(r'stripe|s\.? ?r\.? ?o|a\. ?s\.|spol\.|\bz\. ?s\.|o\.s\b|spolek|nadace|strana|hnuti|kdu|top 09|starostove|obcanska demokrat|demokraticky klub|zmena pro|volt|autocamp|piratsk')
fo = []  # (měsíc, částka, klíč dárce, kanál)
d = json.load(open(os.path.join(ROOT, 'data/raw/darovaci/tx/00409740.json'), encoding='utf-8'))
for t in d['tx']:
    a = t['amount']; cp = n(t['counterparty'])
    if a < 1 or not cp or STATE.search(cp + ' ' + n(t['message'])) or NONFO.search(cp) or re.search(r'koalicni|vyrovnani|mandat|memorand', n(t['message'])): continue
    fo.append((t['date'][:7], a, key(t['counterparty']), 'Převod'))
card = [r for r in csv.DictReader(open(os.path.join(ROOT, 'data/raw/zeleni/karty_min.csv'), encoding='utf-8')) if '2026-01-01' <= r['datum'] <= '2026-10-19']
for r in card: fo.append((r['datum'][:7], float(r['castka']), key(r['jmeno'] + ' ' + r['prijmeni']), 'Kartou'))
tot = sum(x[1] for x in fo)
for ch in ('Převod', 'Kartou'):
    L = [x[1] for x in fo if x[3] == ch]
    print(f"  {ch:7} {len(L):>5} plateb {f(sum(L)):>11} Kč, medián {f(S.median(L))}, dárců {len({x[2] for x in fo if x[3] == ch})}")
print(f"  (na bankovním účtu přišlo přes Stripe 78 177 Kč za 95 výplat; tabulka eviduje {f(sum(float(r['castka']) for r in card))} Kč)")
per = collections.defaultdict(list)
for x in fo: per[x[2]].append(x)
tots = sorted((sum(x[1] for x in v) for v in per.values()), reverse=True)
reg = {k: v for k, v in per.items() if len({x[0] for x in v}) >= 3}
rs = sum(x[1] for v in reg.values() for x in v)
print(f"FO: {len(fo)} plateb, {f(tot)} Kč, dárců {len(per)}, medián platby {f(S.median([x[1] for x in fo]))}, medián dárce/rok {f(S.median(tots))}")
print(f"pravidelní (3+ měsíce): {len(reg)} = {len(reg)/len(per)*100:.0f} % dárců, {f(rs)} Kč = {rs/tot*100:.0f} % částky, medián/rok {f(S.median([sum(x[1] for x in v) for v in reg.values()]))}")
print('  hlavní kanál pravidelných:', dict(collections.Counter(collections.Counter(x[3] for x in v).most_common(1)[0][0] for v in reg.values())))
print('  typická měsíční částka:', collections.Counter(round(S.median([x[1] for x in v])) for v in reg.values()).most_common(8))
print(f"top 1 % dárců {sum(tots[:len(tots)//100])/sum(tots)*100:.0f} %, top 10 % {sum(tots[:len(tots)//10])/sum(tots)*100:.0f} %; dárci do 1000 Kč/rok {sum(1 for t in tots if t <= 1000)} ({sum(1 for t in tots if t <= 1000)/len(tots)*100:.0f} %) = {sum(t for t in tots if t <= 1000)/sum(tots)*100:.1f} % Kč")
B = [(1, 100), (100, 500), (500, 1000), (1000, 5000), (5000, 50000), (50000, 1e9)]
print('pásma plateb (počet/Kč):', ' | '.join(f"{int(lo)}+: {sum(1 for x in fo if lo <= x[1] < hi)/len(fo)*100:.0f}%/{sum(x[1] for x in fo if lo <= x[1] < hi)/tot*100:.0f}%" for lo, hi in B))
months = sorted({x[0] for x in fo})
print('aktivní dárci:', ' '.join(f"{m[5:]}:{len({x[2] for x in fo if x[0] == m})}" for m in months))
seen = set(); new = collections.Counter()
for x in sorted(fo):
    if x[2] not in seen: seen.add(x[2]); new[x[0]] += 1
print('noví dárci:', ' '.join(f"{m[5:]}:{new[m]}" for m in months))
both = {x[2] for x in fo if x[3] == 'Převod'} & {x[2] for x in fo if x[3] == 'Kartou'}
print('dárci převodem i kartou:', len(both))
