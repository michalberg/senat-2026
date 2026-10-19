"""Z data/model.json a data/darci.json spočítá všechno pro web → site/data.json"""
import json, os, re, csv, unicodedata, statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = json.load(open(os.path.join(ROOT, 'data', 'model.json'), encoding='utf-8'))
D = json.load(open(os.path.join(ROOT, 'data', 'darci.json'), encoding='utf-8'))
ANOM = json.load(open(os.path.join(ROOT, 'config', 'anomalie.json'), encoding='utf-8'))
cns = {int(r['NSTRANA']): r['ZKRATKAN8'] for r in csv.DictReader(open(os.path.join(ROOT, 'data/raw/cis/csv_od/cns.csv'), encoding='utf-8'))}


def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()).strip()


ROUND2 = '2026-10-11'  # výdaje od tohoto dne = mezi 1. a 2. kolem a po něm
cands = M['kandidati']
C = {c['id']: c for c in cands}

# ---------- bloky a barvy (analogicky povolebni-analyza/barvy.json) ----------
BLOKY = {
    'ano': ('ANO 2011', '#1C9BD8'), 'stan': ('STAN a koalice vedené STAN', '#A2387E'), 'ods_top': ('ODS / TOP 09 a jejich koalice', '#1F3F8F'),
    'kdu': ('KDU-ČSL', '#F2B300'), 'pirati': ('Piráti a jejich koalice', '#111111'), 'zeleni': ('Zelení a koalice se Zelenými', '#2E9B47'),
    'spd': ('SPD a koalice SPD + PRO', '#6B4226'), 'naplno': ('Svobodní, Trikolora, PRO', '#6A1B9A'), 'restart': ('Levice (KSČM, SOCDEM, Stačilo!, Levice, ČSSD)', '#7A1F3D'),
    'sen21': ('SEN 21', '#1FB5AD'), 'nc': ('Naše Česko', '#D32F2F'), 'nezavisli': ('Nezávislí kandidáti', '#8E6CC4'), 'ostatni': ('Místní a ostatní', '#C8C8C8'),
}
SINGLE = {'ANO': 'ano', 'STAN': 'stan', 'SLK': 'stan', 'ODS': 'ods_top', 'TOP 09': 'ods_top', 'KDU-ČSL': 'kdu', 'Piráti': 'pirati', 'Zelení': 'zeleni',
          'SPD': 'spd', 'PRO': 'naplno', 'Svobodní': 'naplno', 'KSČM': 'restart', 'SOCDEM': 'restart', 'Stačilo!': 'restart', 'Levice': 'restart', 'ČSSD': 'restart',
          'SEN 21': 'sen21', 'NČ': 'nc'}


def blok(c):
    members = [cns.get(x, str(x)) for x in c['slozeni']]
    c['strany'] = members
    if c['typ'] == 'N': return 'nezavisli'
    if c['typ'] == 'S': return SINGLE.get(c['vs_zkr'], 'ostatni')
    if 'SPD' in members and 'Svobodní' not in members: return 'spd'
    if 'Svobodní' in members: return 'naplno'
    if set(members) <= {'Zelení', 'Piráti', 'SEN 21'}: return 'zeleni'
    big = {'ODS', 'TOP 09', 'STAN', 'KDU-ČSL', 'Piráti', 'Zelení'}
    if set(members) & big:
        return SINGLE.get(c['nstrana'], 'ostatni') if c['nstrana'] in SINGLE else 'ostatni'
    return 'ostatni'


for c in cands:
    c['blok'] = blok(c)

# ---------- finance ----------
for c in cands:
    c.update(vydaje=0.0, prime=0.0, sdilene=0.0, poplatky=0.0, vratky=0.0, po_1kole=0.0, prijmy={}, mesice={}, ucty=[], stav='chybi', nepenezni=0.0)

acc_out = []
for a in M['ucty']:
    ks = a['kandidati']
    tx = a.get('tx', [])
    s = defaultdict(float)
    for t in tx: s[t['druh']] += t['amount']
    spend = -(s['vydaj'] + s['poplatek']) - s['vratka']
    acc_rec = {k: a[k] for k in ('key', 'nazev', 'druh', 'obvody_reg', 'url', 'kandidati', 'owner', 'cislo', 'nazev_uctu', 'dostupny', 'slozeni')}
    acc_rec.update(souhrn={k: round(v) for k, v in s.items()}, vydaje=round(spend), n_tx=len(tx),
                   prijmy=round(sum(t['amount'] for t in tx if t['amount'] > 0)),
                   zustatek=(a.get('souhrn') or {}).get('Běžný zůstatek'))
    # zdroje u koalic podle protiúčtu
    z = defaultdict(float)
    for t in tx:
        if t['amount'] > 0 and t['druh'] == 'strana': z[t.get('zdroj') or (a['owner'] or '?')] += t['amount']
    acc_rec['zdroje'] = {k: round(v) for k, v in z.items()}
    acc_out.append(acc_rec)
    if not ks: continue
    if not a['dostupny']:
        for k in ks: C[k]['stav'] = 'chybi'; C[k]['ucty'].append(a['key'])
        continue
    if not tx:
        for k in ks: C[k]['stav'] = 'prazdny'; C[k]['ucty'].append(a['key'])
        continue
    n = len(ks)
    by_ob = {C[k]['obvod']: k for k in ks}
    # výdaje
    direct = defaultdict(float); shared = 0.0
    inc_direct = defaultdict(lambda: defaultdict(float)); inc_shared = defaultdict(float)
    for t in tx:
        d = t['druh']
        if d in ('vydaj', 'poplatek', 'vratka'):
            v = -t['amount']
            k = by_ob.get(t['obvod'])
            mon = t['date'][:7]
            if k:
                direct[k] += v
                C[k]['mesice'][mon] = C[k]['mesice'].get(mon, 0) + v
                if t['date'] >= ROUND2: C[k]['po_1kole'] += v
            else:
                shared += v
                for kk in ks:
                    C[kk]['mesice'][mon] = C[kk]['mesice'].get(mon, 0) + v / n
                    if t['date'] >= ROUND2: C[kk]['po_1kole'] += v / n
            if d == 'poplatek':
                for kk in ([k] if k else ks): C[kk]['poplatky'] += v / (1 if k else n)
        elif t['amount'] > 0:
            k = by_ob.get(t['obvod'])
            if k and n > 1 and t['jak'] != 'jediny': inc_direct[k][d] += t['amount']
            else: inc_shared[d] += t['amount']
    tot_direct = sum(direct.values())
    for k in ks:
        c = C[k]
        c['prime'] += direct[k]
        c['sdilene'] += shared / n
        c['vydaje'] += direct[k] + shared / n
        c['stav'] = 'vlastni' if n == 1 else 'sdileny'
        c['ucty'].append(a['key'])
        # příjmy: přímé + podíl sdílených podle podílu na výdajích
        w = (direct[k] + shared / n) / (tot_direct + shared) if (tot_direct + shared) > 0 else 1 / n
        for d, v in inc_shared.items(): c['prijmy'][d] = c['prijmy'].get(d, 0) + v * w
        for d, v in inc_direct[k].items(): c['prijmy'][d] = c['prijmy'].get(d, 0) + v
    for k in ks:
        C[k]['podil_sdilenych'] = round(C[k]['sdilene'] / C[k]['vydaje'], 3) if C[k]['vydaje'] else 0

# nepeněžní plnění ze zpráv ÚDH (nejdou přes účet)
NEPEN = {'18-6': (149640, 'Nájem obytného automobilu a nafta – bezúplatné plnění od fyzické osoby (zpráva ČZS)'),
         '69-7': (20000, 'Billboardová plocha – bezúplatné plnění GEPAS Group (zpráva rEvoluce)')}
for k, (v, why) in NEPEN.items():
    C[k]['nepenezni'] = v; C[k]['nepenezni_pozn'] = why

for c in cands:
    c['celkem'] = round(c['vydaje'] + c['nepenezni']) if c['stav'] in ('vlastni', 'sdileny', 'prazdny') else None
    if c['stav'] == 'prazdny': c['celkem'] = round(c['nepenezni'])
    for f in ('vydaje', 'prime', 'sdilene', 'poplatky', 'po_1kole'): c[f] = round(c[f])
    c['prijmy'] = {k: round(v) for k, v in c['prijmy'].items()}
    c['mesice'] = {k: round(v) for k, v in sorted(c['mesice'].items())}
    c['kc_na_hlas'] = round(c['celkem'] / c['k1_hlasy'], 1) if c['celkem'] and c['k1_hlasy'] else None
    # kvalita odhadu
    if c['stav'] == 'vlastni': c['kvalita'] = 'vysoká'
    elif c['stav'] == 'sdileny': c['kvalita'] = 'střední' if c.get('podil_sdilenych', 0) < 0.4 else 'nízká'
    elif c['stav'] == 'prazdny': c['kvalita'] = 'účet bez pohybů'
    else: c['kvalita'] = 'data nedostupná'

# ---------- dárci ----------
subj = {}
for s in D['subjekty']:
    if s['seq'] == 2 or s['nazev'] not in subj: subj[s['nazev']] = s


def match_subject(c):
    names = [c['vs_nazev']]
    best = None
    for nm, s in subj.items():
        a, b = re.sub(r'[^a-z0-9]', '', norm(nm)), re.sub(r'[^a-z0-9]', '', norm(c['vs_nazev']))
        if a == b or a.startswith(b[:25]) or b.startswith(a[:25]): best = s
    if c['typ'] == 'N':
        for nm, s in subj.items():
            if norm(c['prijmeni']) in norm(nm): best = s
    return best


cross = defaultdict(set)
for nm, s in subj.items():
    for d in s['darci']:
        key = norm(d['dárce'].split(',')[0] + ',' + (d['dárce'].split(',')[1] if ',' in d['dárce'] else '')) + '|' + d['id']
        cross[key].add(nm)
for c in cands:
    s = match_subject(c)
    if not s:
        c['darci'] = None; continue
    ds = s['darci']
    uniq = {}
    for d in ds:
        key = norm(d['dárce'].split(',')[0] + ',' + (d['dárce'].split(',')[1] if ',' in d['dárce'] else ''))
        uniq.setdefault(key, {'n': 0, **d}); uniq[key]['n'] += 1
    me = norm(c['prijmeni'] + ', ' + c['jmeno'])
    c['darci'] = {'subjekt': s['nazev'], 'stav': s['stav'], 'url': s['url'], 'zaznamu': len(ds), 'darcu': len(uniq),
                  'po': sum(1 for u in uniq.values() if u['po']), 'fo': sum(1 for u in uniq.values() if not u['po']),
                  'opakovane': sum(1 for u in uniq.values() if u['n'] > 1), 'kandidat_darcem': any(k.startswith(me) for k in uniq),
                  'top_po': sorted([{'d': u['dárce'].split(',')[0], 'ico': u['id'], 'n': u['n']} for u in uniq.values() if u['po']], key=lambda x: -x['n'])[:12],
                  'pozde': s['nazev'] in D['neoznamili_1kolo'] or any(norm(x)[:20] == norm(s['nazev'])[:20] for x in D['neoznamili_1kolo'])}

multi = [{'darce': k.split('|')[0], 'po': bool(re.fullmatch(r'\d{6,8}', k.split('|')[1])) or bool(re.search(r'strana|hnuti|spolek|s\.r\.o|a\.s\.|top 09|kdu|cz\b', k)), 'subjekty': sorted(v)} for k, v in cross.items() if len(v) > 1]
# kandidáti, kteří figurují v seznamech dárců (vlastní strany)
cand_donors = [{'id': c['id'], 'subjekt': c['darci']['subjekt']} for c in cands if c.get('darci') and c['darci']['kandidat_darcem']]

subjekty_out = [{'nazev': nm, 'stav': s['stav'], 'url': s['url'], 'zaznamu': len(s['darci']), 'po': sum(d['po'] for d in s['darci']),
                 'pozde': nm in D['neoznamili_1kolo']} for nm, s in subj.items()]

# ---------- dárci: souhrnná tabulka ----------
PARTY_DONOR = re.compile(r'^stan$|strana|hnuti|top 09|kdu-csl|piratsk|starostove|obcanska demokraticka|sen 21|svobodni|trikolora|fakt brno|volt|liberalne ekologick|praha sobe|pro pravo|hlas regionu|zeleni|soukromnik', re.I)
subj_cands = defaultdict(list)
for c in cands:
    if c.get('darci'): subj_cands[c['darci']['subjekt']].append(c['id'])
acc_by_key = {a['key']: a for a in M['ucty']}
udh_amounts = defaultdict(float)  # ze zpráv ÚDHPSH
for f in __import__('glob').glob(os.path.join(ROOT, 'data/raw/udh/zpravy/s2026-*-penize*.json')):
    for r in json.load(open(f, encoding='utf-8')):
        nm = norm(r.get('company') or f"{r.get('lastName','')} {r.get('firstName','')}")
        udh_amounts[nm] += r.get('money') or 0


def donor_key(d):
    ident = d['id'].strip()
    parts = [x.strip() for x in d['dárce'].split(',')]
    if d['po']:
        if re.fullmatch(r'\d{6,8}', ident): return 'ico:' + ident.zfill(8)
        return 'po:' + re.sub(r'[^a-z0-9]', '', norm(parts[0]))
    return 'fo:' + norm(parts[0] + ' ' + (parts[1] if len(parts) > 1 else '')) + '|' + ident


donors = {}
for nm, s in subj.items():
    for d in s['darci']:
        k = donor_key(d)
        parts = [x.strip() for x in d['dárce'].split(',')]
        r = donors.setdefault(k, {'k': k, 'po': d['po'], 'jmeno': parts[0] if d['po'] else (parts[1] + ' ' + parts[0] if len(parts) > 1 else parts[0]),
                                  'misto': (parts[-1] if d['po'] and len(parts) > 1 else (parts[2] if len(parts) > 2 else '')),
                                  'ico': d['id'].zfill(8) if d['po'] and re.fullmatch(r'\d{6,8}', d['id']) else '', 'subjekty': {}, 'zaznamu': 0})
        if d['po'] and len(parts) > 2: r['misto'] = re.sub(r'\d{3}\s?\d{2}$', '', parts[-2] if re.fullmatch(r'\d{5}|\d{3} \d{2}', parts[-1]) else parts[-1]).strip()
        r['subjekty'][nm] = r['subjekty'].get(nm, 0) + 1
        r['zaznamu'] += 1


# sloučit fyzické osoby uvedené jednou s datem narození a jednou bez
for k in [k for k in donors if k.startswith('fo:') and k.endswith('|')]:
    base = k[:-1]
    twins = [x for x in donors if x.startswith(base) and x != k]
    if len(twins) == 1:
        t = donors[twins[0]]
        for nm, n in donors[k]['subjekty'].items(): t['subjekty'][nm] = t['subjekty'].get(nm, 0) + n
        t['zaznamu'] += donors[k]['zaznamu']; t['misto'] = t['misto'] or donors[k]['misto']
        del donors[k]


def tokens(r):
    t = [x for x in re.split(r'[^a-z0-9]+', norm(r['jmeno'])) if len(x) >= 3 and x not in ('sro', 'spol', 'cesko', 'czech', 'republika', 'cr', 'group')]
    return t[:3]


for r in donors.values():
    r['typ'] = 'strana' if r['po'] and PARTY_DONOR.search(norm(r['jmeno'])) and not re.search(r's\.?\s?r\.?\s?o|a\.\s?s\.', r['jmeno'], re.I) else ('po' if r['po'] else 'fo')
    tk = tokens(r); amt = 0.0; n = 0
    keys = set()
    for nm in r['subjekty']:
        for cid in subj_cands.get(nm, []): keys.update(C[cid]['ucty'])
    for ak in keys:
        for t in acc_by_key[ak].get('tx', []):
            if t['amount'] > 0 and t['druh'] in (('dar', 'kandidat') if r['typ'] == 'fo' else ('dar', 'strana', 'neurceno')) and tk:
                txt = norm(t['counterparty'])
                if all(x in txt for x in tk): amt += t['amount']; n += 1
    r['na_uctech'] = round(amt); r['plateb'] = n
    r['zprava'] = round(udh_amounts.get(norm(r['jmeno'].split(' ', 1)[-1] + ' ' + r['jmeno'].split(' ', 1)[0]) if not r['po'] else norm(r['jmeno']), 0))
    r['kandidati'] = sorted({cid for nm in r['subjekty'] for cid in subj_cands.get(nm, [])}, key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1])))
    r['subjekty'] = [{'s': k, 'n': v} for k, v in sorted(r['subjekty'].items(), key=lambda x: -x[1])]
    r['n_subj'] = len(r['subjekty'])
    del r['k']
donor_list = sorted(donors.values(), key=lambda r: (-r['n_subj'], -r['zaznamu']))
print('darcu', len(donor_list), 'po', sum(r['typ'] == 'po' for r in donor_list), 'strany', sum(r['typ'] == 'strana' for r in donor_list), 's castkou', sum(r['na_uctech'] > 0 for r in donor_list), round(sum(r['na_uctech'] for r in donor_list)))

# ---------- obvody ----------
obvody = []
for o, nazev in sorted(M['obvody'].items(), key=lambda x: int(x[0])):
    o = int(o)
    cs = sorted([c for c in cands if c['obvod'] == o], key=lambda c: -c['k1_proc'])
    if not cs: continue
    known = [c for c in cs if c['celkem'] is not None]
    total = sum(c['celkem'] for c in known)
    win = next(c for c in cs if c['zvolen'])
    top = max(known, key=lambda c: c['celkem']) if known else None
    for c in cs:
        c['podil_vydaju'] = round(c['celkem'] / total * 100, 1) if total and c['celkem'] is not None else None
    obvody.append({'obvod': o, 'nazev': nazev, 'kandidati': [c['id'] for c in cs], 'celkem': round(total),
                   'neuplne': len(known) < len(cs), 'chybi': [c['id'] for c in cs if c['celkem'] is None],
                   'vitez': win['id'], 'rozhodnuto_1k': win['zvolen_1k'], 'nejvic_utratil': top['id'] if top else None,
                   'vyhral_nejvetsi': bool(top and top['id'] == win['id']), 'ucast': M['ucast'].get(str(o)),
                   'kc_na_volice': round(total / M['ucast'][str(o)]['1']['volici'], 2) if str(o) in M['ucast'] else None,
                   'kc_na_hlas': round(total / sum(c['k1_hlasy'] for c in known), 1) if known else None})


# ---------- souhrny ----------
def stats(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs: return None
    return {'n': len(xs), 'min': xs[0], 'max': xs[-1], 'median': round(statistics.median(xs)), 'prumer': round(statistics.mean(xs)), 'soucet': round(sum(xs))}


known = [c for c in cands if c['celkem'] is not None]
finalists = [c for c in cands if c['postup'] or c['zvolen_1k']]
souhrn = {
    'kandidatu': len(cands), 'obvodu': len(obvody), 'celkem': round(sum(c['celkem'] for c in known)),
    'znamych': len(known), 'nedostupnych': [c['id'] for c in cands if c['stav'] == 'chybi'],
    'prazdnych': [c['id'] for c in cands if c['stav'] == 'prazdny'],
    'vsichni': stats([c['celkem'] for c in known]),
    'postupujici': stats([c['celkem'] for c in cands if c['postup'] and c['celkem'] is not None]),
    'nepostupujici': stats([c['celkem'] for c in cands if not c['postup'] and not c['zvolen_1k'] and c['celkem'] is not None]),
    'vitezove': stats([c['celkem'] for c in cands if c['zvolen'] and c['celkem'] is not None]),
    'porazeni_finaliste': stats([c['celkem'] for c in cands if c['postup'] and not c['zvolen'] and c['celkem'] is not None]),
    'vitezove_2k': stats([c['celkem'] for c in cands if c['zvolen'] and not c['zvolen_1k'] and c['celkem'] is not None]),
    'po_1kole_finaliste': stats([c['po_1kole'] for c in cands if c['postup'] and c['celkem'] is not None]),
    'nejvetsi_vyhral': sum(1 for o in obvody if o['vyhral_nejvetsi']),
    'souboje_2k': sum(1 for o in obvody if not o['rozhodnuto_1k']),
    'bohatsi_vyhral_2k': 0, 'sdilene_celkem': round(sum(c['sdilene'] for c in known)),
}
# ve 2. kole vyhrál ten s vyšším rozpočtem?
duels = []
for o in obvody:
    if o['rozhodnuto_1k']: continue
    f = [C[k] for k in o['kandidati'] if C[k]['postup']]
    if len(f) == 2 and all(x['celkem'] is not None for x in f):
        rich = max(f, key=lambda x: x['celkem'])
        duels.append({'obvod': o['obvod'], 'a': f[0]['id'], 'b': f[1]['id'], 'bohatsi_vyhral': rich['zvolen']})
souhrn['bohatsi_vyhral_2k'] = sum(d['bohatsi_vyhral'] for d in duels)
souhrn['duelu'] = len(duels)

# ---------- strany / bloky ----------
by_blok = defaultdict(lambda: {'kandidatu': 0, 'celkem': 0, 'hlasy': 0, 'postup': 0, 'mandaty': 0, 'neznamych': 0})
by_vs = defaultdict(lambda: {'kandidatu': 0, 'celkem': 0, 'hlasy': 0, 'postup': 0, 'mandaty': 0, 'neznamych': 0, 'kandidati': []})
by_party = defaultdict(lambda: {'samostatne': 0, 'v_koalici': 0, 'vydaje_samostatne': 0, 'vydaje_koalice_plne': 0, 'vydaje_pomerne': 0, 'mandaty_samostatne': 0, 'mandaty_koalice': 0, 'vklady_do_koalic': 0})
for c in cands:
    for agg, key in ((by_blok, c['blok']), (by_vs, c['vs_nazev'])):
        r = agg[key]; r['kandidatu'] += 1; r['hlasy'] += c['k1_hlasy']; r['postup'] += c['postup'] or c['zvolen_1k']; r['mandaty'] += c['zvolen']
        if c['celkem'] is None: r['neznamych'] += 1
        else: r['celkem'] += c['celkem']
    by_vs[c['vs_nazev']]['kandidati'].append(c['id']); by_vs[c['vs_nazev']]['blok'] = c['blok']; by_vs[c['vs_nazev']]['typ'] = c['typ']
    by_vs[c['vs_nazev']]['zkr'] = c['vs_zkr']; by_vs[c['vs_nazev']]['strany'] = c['strany']
    if c['typ'] == 'N': continue
    ms = c['strany']; v = c['celkem'] or 0
    for p in ms:
        r = by_party[p]
        if c['typ'] == 'S':
            r['samostatne'] += 1; r['vydaje_samostatne'] += v; r['mandaty_samostatne'] += c['zvolen']; r['vydaje_pomerne'] += v
        else:
            r['v_koalici'] += 1; r['vydaje_koalice_plne'] += v; r['mandaty_koalice'] += c['zvolen']; r['vydaje_pomerne'] += v / len(ms)
for a in acc_out:
    if a['druh'] == 'koalice':
        for p, v in a['zdroje'].items(): by_party[p]['vklady_do_koalic'] += v
for r in by_party.values():
    r['vydaje_pomerne'] = round(r['vydaje_pomerne'])

# ---------- příznaky (automaticky) ----------
flags = []
for c in cands:
    if c['stav'] == 'prazdny': flags.append({'id': c['id'], 'typ': 'prazdny_ucet', 'text': 'Volební účet bez jediného pohybu.'})
    if c['stav'] == 'chybi': flags.append({'id': c['id'], 'typ': 'nedostupny', 'text': 'Transparentní účet nebylo možné stáhnout.'})
    if c['stav'] == 'sdileny' and c.get('podil_sdilenych', 0) >= 0.5: flags.append({'id': c['id'], 'typ': 'sdilene', 'text': f"{round(c['podil_sdilenych']*100)} % výdajů nejde z účtu přiřadit k obvodu – rozpočítáno rovným dílem."})
    if c['prijmy'].get('kandidat', 0) >= 50000: flags.append({'id': c['id'], 'typ': 'vlastni_zdroje', 'text': f"Kandidát(ka) vložil(a) na účet {c['prijmy']['kandidat']:,} Kč z vlastních zdrojů.".replace(',', ' ')})
    if c['darci'] and c['darci']['pozde']: flags.append({'id': c['id'], 'typ': 'pozde_darci', 'text': 'Seznam dárců před 1. kolem nebyl oznámen včas (do 6. 10. 2026).'})

out = {'vygenerovano': '2026-10-19', 'souhrn': souhrn, 'obvody': obvody, 'kandidati': cands, 'ucty': acc_out,
       'bloky': [{'id': k, 'nazev': BLOKY[k][0], 'barva': BLOKY[k][1], **{kk: (round(vv) if isinstance(vv, float) else vv) for kk, vv in by_blok[k].items()}} for k in BLOKY if k in by_blok],
       'subjekty': [{'nazev': k, **v} for k, v in by_vs.items()], 'strany': [{'strana': k, **v} for k, v in sorted(by_party.items(), key=lambda x: -x[1]['vydaje_pomerne'])],
       'duely': duels, 'darci': {'seznam': donor_list, 'subjekty': subjekty_out, 'vice_subjektu': multi, 'kandidati_darci': cand_donors, 'pozde': D['neoznamili_1kolo']},
       'priznaky': flags, 'anomalie': ANOM['polozky']}
os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'docs', 'data.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('celkem', souhrn['celkem'], 'znamych', souhrn['znamych'], 'postup', souhrn['postupujici'], 'vitezove', souhrn['vitezove'])
print('nejvetsi vyhral', souhrn['nejvetsi_vyhral'], '/', len(obvody), 'bohatsi 2k', souhrn['bohatsi_vyhral_2k'], '/', souhrn['duelu'])
