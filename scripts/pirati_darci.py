"""Dary Pirátům z veřejného výpisu darypiratum.cz (export CSV) – drobní a pravidelní dárci."""
import csv, collections, statistics as S, unicodedata, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def n(s): return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower().strip()
f = lambda x: f"{x:,.0f}".replace(',', ' ')
R = list(csv.DictReader(open(os.path.join(ROOT, 'data/raw/darypiratum/dary_2026.csv'), encoding='utf-8-sig')))
NEDAR = {'sen 21', 'fakt brno', 'tomas repa'}  # koaliční podíly / vklady stran evidované jako osoby (Repa: "za stranu GEN")
fo, ex = [], []
for r in R:
    r['a'] = float(r['Částka'].replace('Kč', '').replace(' ', '').replace('\xa0', '').replace(',', '.'))
    d, m, y = r['Datum přijetí daru'].split('.'); r['m'] = f'{y}-{int(m):02d}'
    r['k'] = (n(r['Jméno']) + ' ' + n(r['Příjmení'])).strip()
    firm = n(r['Název firmy'])
    if r['k'] in NEDAR or 'koalicni' in n(r['Projekt']) or (firm and not r['k']): ex.append(r); continue
    fo.append(r)
tot = sum(r['a'] for r in fo)
print(f"vyřazeno (strany, koaliční podíly, firmy): {len(ex)} plateb, {f(sum(r['a'] for r in ex))} Kč")
for meth in ('Převod', 'Online'):
    L = [r['a'] for r in fo if r['Metoda platby'] == meth]
    print(f"  {meth:7} {len(L):>5} plateb {f(sum(L)):>11} Kč, medián {f(S.median(L))}")
per = collections.defaultdict(list)
for r in fo: per[r['k']].append(r)
tots = sorted((sum(x['a'] for x in v) for v in per.values()), reverse=True)
reg = {k: v for k, v in per.items() if len({x['m'] for x in v}) >= 3}
rs = sum(x['a'] for v in reg.values() for x in v)
print(f"FO: {len(fo)} plateb, {f(tot)} Kč, dárců {len(per)}, medián platby {f(S.median([r['a'] for r in fo]))}, medián dárce/rok {f(S.median(tots))}")
print(f"pravidelní (3+ měsíce): {len(reg)} = {len(reg)/len(per)*100:.0f} % dárců, {f(rs)} Kč = {rs/tot*100:.0f} % částky, medián/rok {f(S.median([sum(x['a'] for x in v) for v in reg.values()]))}")
print('  hlavní kanál pravidelných:', dict(collections.Counter(collections.Counter(x['Metoda platby'] for x in v).most_common(1)[0][0] for v in reg.values())))
print('  typická měsíční částka:', collections.Counter(round(S.median([x['a'] for x in v])) for v in reg.values()).most_common(8))
print(f"top 1 % dárců {sum(tots[:len(tots)//100])/sum(tots)*100:.0f} %, top 10 % {sum(tots[:len(tots)//10])/sum(tots)*100:.0f} %; dárci do 1000 Kč/rok {sum(1 for t in tots if t <= 1000)} ({sum(1 for t in tots if t <= 1000)/len(tots)*100:.0f} %) = {sum(t for t in tots if t <= 1000)/sum(tots)*100:.1f} % Kč")
B = [(1, 100), (100, 500), (500, 1000), (1000, 5000), (5000, 50000), (50000, 1e9)]
print('pásma plateb (počet/Kč):', ' | '.join(f"{int(lo)}+: {sum(1 for r in fo if lo <= r['a'] < hi)/len(fo)*100:.0f}%/{sum(r['a'] for r in fo if lo <= r['a'] < hi)/tot*100:.0f}%" for lo, hi in B))
months = sorted({r['m'] for r in fo})
print('aktivní dárci:', ' '.join(f"{m[5:]}:{len({r['k'] for r in fo if r['m'] == m})}" for m in months))
seen = set(); new = collections.Counter()
for r in sorted(fo, key=lambda r: r['m']):
    if r['k'] not in seen: seen.add(r['k']); new[r['m']] += 1
print('noví dárci:', ' '.join(f"{m[5:]}:{new[m]}" for m in months))
