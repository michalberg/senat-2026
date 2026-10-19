"""Sestaví data/model.json: kandidáti, výsledky, účty, transakce s přiřazením k obvodům, odhady výdajů."""
import csv, json, re, os, sys, glob, unicodedata
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
TX = os.path.join(RAW, 'ucty', 'tx')


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s)


def rcsv(p):
    return list(csv.DictReader(open(os.path.join(RAW, p), encoding='utf-8')))


# ---------- volby ----------
obvody = {r['OBVOD']: r['NAZEV_OBV'] for r in rcsv('cis/csv_od/secobv.csv')}
cvs = {r['VSTRANA']: r for r in rcsv('cis/csv_od/cvs.csv')}
cns = {r['NSTRANA']: r for r in rcsv('cis/csv_od/cns.csv')}
cpp = {r['PSTRANA']: r for r in rcsv('cis/csv_od/cpp.csv')}
cand = []
for r in rcsv('reg/csv_od/serk.csv'):
    v = cvs[r['VSTRANA']]
    cand.append({
        'id': f"{r['OBVOD']}-{r['CKAND']}", 'obvod': int(r['OBVOD']), 'ck': int(r['CKAND']),
        'jmeno': r['JMENO'], 'prijmeni': r['PRIJMENI'], 'tp': r['TITULPRED'], 'tz': r['TITULZA'],
        'vek': int(r['VEK']), 'povolani': r['POVOLANI'], 'bydliste': r['BYDLISTEN'],
        'vstrana': int(r['VSTRANA']), 'vs_nazev': r['NAZEV_VS'], 'vs_zkr': v['ZKRATKAV8'], 'typ': v['TYPVS'],
        'slozeni': [int(x) for x in v['SLOZENI'].split(',') if x],
        'nstrana': cns.get(r['NSTRANA'], {}).get('ZKRATKAN8', ''), 'pstrana': cpp.get(r['PSTRANA'], {}).get('ZKRATKAP8', ''),
        'k1_hlasy': int(r['HLASY_K1']), 'k1_proc': float(r['PROC_K1'] or 0), 'k1': int(r['ZVOLEN_K1']),
        'k2_hlasy': int(r['HLASY_K2'] or 0), 'k2_proc': float(r['PROC_K2'] or 0), 'k2': int(r['ZVOLEN_K2'] or 0),
    })
for c in cand:
    c['postup'] = c['k1'] == 2
    c['zvolen'] = c['k1'] == 1 or c['k2'] == 1
    c['zvolen_1k'] = c['k1'] == 1

# účast z XML
ucast = {}
for m in re.finditer(r'<OBVOD CISLO="(\d+)" NAZEV="([^"]+)">(.*?)</OBVOD>', open(os.path.join(RAW, 'vysledky.xml'), encoding='utf-8').read(), re.S):
    u = {}
    for k in re.finditer(r'<UCAST KOLO="(\d)"([^>]*)/>', m.group(3)):
        a = dict(re.findall(r'(\w+)="([^"]*)"', k.group(2)))
        u[k.group(1)] = {'volici': int(a['ZAPSANI_VOLICI']), 'ucast': float(a['UCAST_PROC']), 'platne': int(a['PLATNE_HLASY'])}
    ucast[int(m.group(1))] = u

# ---------- registr účtů ----------
cfg = json.load(open(os.path.join(ROOT, 'config', 'ucty_map.json'), encoding='utf-8'))
reg = json.load(open(os.path.join(ROOT, 'data', 'ucty.json'), encoding='utf-8'))


def file_key(url):
    if 'ib.fio.cz' in url: return 'fio_' + re.search(r'a=(-?\d+)', url).group(1)
    if 'kb.cz' in url: return 'kb_' + re.search(r'(\d+-\d+)$', url).group(1)
    if 'csas.cz' in url: return 'csas_' + re.search(r'(\d{6}-\d+)', url).group(1)
    if 'rb.cz' in url: return 'rb_' + re.search(r'accountNumber=(\d+)', url).group(1)
    if 'moneta' in url: return 'moneta_' + url.rstrip('/').split('/')[-1]
    if 'csob.cz' in url: return 'csob_' + re.search(r'account=(\d+)', url).group(1)
    if 'unicredit' in url: return 'unicredit_' + re.search(r'IBAN=(\w+)', url).group(1)


cand_by_id = {c['id']: c for c in cand}
accounts = []
for e in reg:
    typ = e['typ'].split()[0]
    c = e['cells']
    if typ == 'strany':
        name, ob = c[0], [int(x) for x in c[2].split(',') if x and x != '0']
        vs = cfg['strany'][name]
        cands = [x for x in cand if x['vstrana'] in vs and x['obvod'] in ob]
        kind = 'strana'
        if not cands and vs:  # registr uvádí jiný obvod, než kde strana kandidovala
            cands = [x for x in cand if x['vstrana'] in vs]
    elif typ == 'koalice':
        name, ob = c[1], [int(x) for x in c[0].split(',')]
        vs = [v for k, v in cfg['koalice'].items() if name.startswith(k) or k in name][0]
        cands = [x for x in cand if x['vstrana'] == vs and x['obvod'] in ob]
        kind = 'koalice'
    else:
        name, ob = c[1], [int(c[3])]
        cands = [x for x in cand if x['vstrana'] == 80 and x['obvod'] in ob and x['prijmeni'] in name]
        kind = 'nezavisly'
    key = file_key(e['url'])
    path = os.path.join(TX, key + '.json')
    d = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else None
    accounts.append({'key': key, 'nazev': name, 'druh': kind, 'obvody_reg': ob, 'url': e['url'],
                     'kandidati': [x['id'] for x in cands], 'data': d, 'slozeni': c[2] if typ == 'koalice' else ''})

# ---------- klasifikace transakcí ----------
RE_FEE = re.compile(r'poplatek|cena za vedeni|vedeni uctu|za vedeni|bankovni poplatek|^fee', re.I)
RE_REFUND_DONATION = re.compile(r'vraceni daru|vratka daru|vraceni prispevku|vraceni platby|vraceni penez|vraceni.*dar\b|mylna platba|vratka platby|chybne cislo uctu|nespravny ucet|spatny ucet')
RE_TRANSFER_OUT = re.compile(r'prevod (zpet|zustatku|financi|prostredku|na (provozni|bezny|hlavni|transparentni|ucet strany))|zpet na (ucet|provozni)|prevod mezi ucty|vraceni (nevycerpanych|zustatku|prostredku)')
RE_REFUND_IN = re.compile(r'vratk|vracen|storno|dobropis|preplat|refund|chybn|zaloha zpet|neuskutecn|nerealizov')
RE_PARTY_IN = re.compile(r'prevod|provozni|na volebni ucet|volebni ucet|z uctu|prispevek (strany|hnuti)|kampan.*strana|financovani kampane|vklad')
RE_DAR = re.compile(r'\bdar\b|dar na|darujeme|darek|sponzor|podpora kampane|podporuji|fandim|drzim palce|hodne stesti')


def classify(t, acc):
    txt = norm(' '.join([t['counterparty'], t['message'], t['note']]))
    owner = norm(acc['data'].get('owner', '')) if acc['data'] else ''
    a = t['amount']
    if a < 0:
        if RE_FEE.search(txt) and abs(a) < 2000: return 'poplatek'
        if RE_REFUND_DONATION.search(txt): return 'vraceni_daru'
        if RE_TRANSFER_OUT.search(txt): return 'prevod_ven'
        return 'vydaj'
    else:
        if 'urok' in txt and a < 500: return 'urok'
        if RE_REFUND_IN.search(txt) and not RE_DAR.search(txt): return 'vratka'
        if CAND_SELF(t, acc): return 'kandidat'
        if RE_DAR.search(txt) and not ('prevod' in txt and owner and owner[:12] in txt): return 'dar'
        cp = norm(t['counterparty'])
        if acc['druh'] == 'nezavisly': return 'dar'
        if owner and cp and (cp[:12] == owner[:12] or owner[:12] in cp): return 'strana'
        if owner and owner[:10] in txt: return 'strana'
        if PARTY_NAMES.search(cp or ''): return 'strana'
        if RE_PARTY_IN.search(txt): return 'strana'
        if not cp.strip(): return 'neurceno'
        return 'dar'


def CAND_SELF(t, acc):
    cp = norm(t['counterparty'])
    for i in acc['kandidati']:
        c = cand_by_id[i]
        if norm(c['prijmeni']).split()[0] in cp and norm(c['jmeno']) in cp: return True
    return False


PARTY_LIST = [('ODS', r'obcanska demokraticka|^ods\b'), ('STAN', r'starostove a nezavisli|^stan\b'), ('TOP 09', r'top 09|top09'),
              ('Piráti', r'piratska'), ('KDU-ČSL', r'kdu|krestanska a demokraticka'), ('Zelení', r'strana zelenych'), ('SLK', r'starostove pro liberecky'),
              ('SPD', r'svoboda a prima demokracie|\bspd\b'), ('PRO', r'pro pravo respekt'), ('Svobodní', r'svobodni'), ('Fakt Brno', r'fakt brno'),
              ('Volt', r'volt'), ('SEN 21', r'sen 21'), ('ANO', r'ano 2011'), ('PRAHA SOBĚ', r'praha sobe|prazska mestska')]


def party_of(cp):
    n = norm(cp)
    for nm, pat in PARTY_LIST:
        if re.search(pat, n): return nm
    return None


PARTY_NAMES = re.compile(r'obcanska demokraticka|starostove a nezavisli|top 09|ceska piratska|piratska strana|krestanska a demokraticka|kdu-csl|strana zelenych|svoboda a prima demokracie|ano 2011|komunisticka strana|sen 21|svobodni|trikolora|volt cesko|pro pravo respekt|prazska mestska strana|nase cesko|stacilo|socialni demokracie|hnuti generace|levice|prisaha|naplno|^ods$|^stan$')

# ---------- přiřazení k obvodu ----------
TOWN = {}  # klíčová slova pro obvody
for o, n in obvody.items():
    base = norm(n).replace('-mesto', '').replace(' nad ', ' ').split()
    TOWN[int(o)] = [norm(n).replace('-mesto', '')]
EXTRA = {3: ['cheb', 'tachov', 'marianske lazne', 'as '], 6: ['louny', 'zatec', 'podborany'], 9: ['plzen', 'plzni'], 12: ['strakonice', 'pisek', 'prachen'],
         15: ['pelhrimov', 'jihlav', 'humpolec', 'pacov'], 18: ['pribram', 'dobris'], 21: ['praha 5', 'praha 13', 'praha 16', 'zbraslav', 'radotin', 'praze 5', 'p5', 'stodulk'],
         24: ['praha 9', 'praha 14', 'praha 18', 'praha 19', 'praha 20', 'praha 21', 'kbely', 'letnany', 'cerny most'], 27: ['praha 1', 'praha 7', 'praha 2', 'praze 1', 'holesovic'],
         30: ['kladno', 'slany', 'velvary', 'stochov'], 33: ['decin', 'ceske svycarsko', 'rumburk', 'varnsdorf'], 36: ['ceska lipa', 'liberec', 'novy bor', 'mimon'],
         39: ['trutnov', 'dvur kralove', 'vrchlabi'], 42: ['kolin', 'kutna hora', 'cesky brod'], 45: ['hradec kralove', 'hradec', 'hradecko'], 48: ['rychnov', 'orlick', 'dobruska'],
         51: ['zdar', 'novem meste na morave', 'nove mesto na morave', 'bystrice nad pernstejnem', 'velke mezirici'], 54: ['znojm', 'moravsky krumlov'], 57: ['vyskov', 'slavkov', 'bucovic'],
         60: ['brno', 'brne'], 63: ['prerov', 'hranice', 'lipnik'], 66: ['litovel', 'olomouc', 'unicov', 'sternberk'], 69: ['frydek', 'mistek', 'f-m', 'frydlant'],
         72: ['ostrava', 'ostrav'], 75: ['karvin', 'havirov', 'orlova', 'bohumin'], 78: ['zlin', 'otrokovic', 'vizovic'], 81: ['uherske hradiste', 'uh. hradiste', 'uherske', 'stare mesto', 'slovacko', 'hodonin', 'uh ']}
for k, v in EXTRA.items(): TOWN[k] += v


def assign(t, acc, cands_by_ob):
    obs = sorted(cands_by_ob)
    if len(obs) == 1: return obs[0], 'jediny'
    if not obs: return None, 'zadny'
    # 1) specifický symbol
    ss = (t['ss'] or '').lstrip('0')
    if ss.isdigit():
        n = int(ss)
        if n in cands_by_ob: return n, 'ss'
        if 10000 <= n < 10100 and n - 10000 in cands_by_ob: return n - 10000, 'ss'  # SPD 100NN
    txt = ' ' + norm(' '.join([t['message'], t['note'], t['counterparty']])) + ' '
    # 2) explicitní číslo obvodu v textu
    for pre, o in (('splzen', 9), ('spraha', 21), ('szlin', 78)):
        if pre in txt.replace('(', '').replace(')', '').replace(' ', '') and o in cands_by_ob: return o, 'text_mesto'
    for pat in [r'(?<![0-9])(\d{1,2})\s+-\s', r'\bss[ :]*(\d{1,2})\b', r'^\s*(\d{1,2})\s*/', r'\bvo[ .:-]*(\d{1,2})\b', r'obvod[u]?[ .:c-]*(?:c\.|cislo)?\s*(\d{1,2})\b', r'\bso[ .:-]*(\d{1,2})\b', r'\b(\d{1,2})\s*/\s*[a-z]']:
        m = re.search(pat, txt)
        if m and int(m.group(1)) in cands_by_ob: return int(m.group(1)), 'text_cislo'
    # 3) příjmení kandidáta
    hits = set()
    for o, cs in cands_by_ob.items():
        for c in cs:
            for p in norm(c['prijmeni']).split():
                if len(p) >= 4 and re.search(r'\b' + re.escape(p[:-1]), txt): hits.add(o)
    if len(hits) == 1: return hits.pop(), 'prijmeni'
    # 4) město / region
    hits = set()
    for o in cands_by_ob:
        for w in TOWN.get(o, []):
            if w.strip() and re.search(r'(?<![a-z0-9])' + re.escape(w.strip()) + r'(?![0-9])', txt): hits.add(o)
    if len(hits) == 1: return hits.pop(), 'mesto'
    return None, 'sdilene'


OVR = json.load(open(os.path.join(ROOT, 'config', 'prirazeni.json'), encoding='utf-8')) if os.path.exists(os.path.join(ROOT, 'config', 'prirazeni.json')) else {}

for acc in accounts:
    d = acc['data']
    cs = [cand_by_id[i] for i in acc['kandidati']]
    by_ob = defaultdict(list)
    for c in cs: by_ob[c['obvod']].append(c)
    acc['tx'] = []
    if not d: continue
    for i, t in enumerate(d['tx']):
        if t['date'] < '2026-01-01' or t['date'] > '2026-10-19': continue
        k = classify(t, acc)
        o, how = assign(t, acc, by_ob)
        ov = OVR.get(acc['key'], {}).get(f"{t['date']}|{t['amount']}")
        if ov is not None:
            if 'obvod' in ov: o, how = ov['obvod'], 'rucne'
            if 'druh' in ov: k = ov['druh']
        zs = party_of(t['counterparty']) if t['amount'] > 0 and k == 'strana' else None
        acc['tx'].append({'zdroj': zs, **{x: t[x] for x in ('date', 'amount', 'counterparty', 'message', 'note', 'ss', 'vs', 'ks', 'type')}, 'druh': k, 'obvod': o, 'jak': how})

json.dump({'obvody': obvody, 'kandidati': cand, 'ucast': ucast,
           'ucty': [{k: v for k, v in a.items() if k not in ('data',)} | {'owner': (a['data'] or {}).get('owner'), 'cislo': (a['data'] or {}).get('number'),
                     'nazev_uctu': (a['data'] or {}).get('name'), 'souhrn': (a['data'] or {}).get('summary'), 'dostupny': a['data'] is not None} for a in accounts]},
          open(os.path.join(ROOT, 'data', 'model.json'), 'w', encoding='utf-8'), ensure_ascii=False)

# kontrolní výpis
if '-v' in sys.argv:
    for a in accounts:
        if not a['tx']: print('!!', a['key'], a['nazev'][:40], 'bez dat' if not a['data'] else 'bez pohybů', a['kandidati']); continue
        s = defaultdict(float)
        for t in a['tx']: s[t['druh']] += t['amount']
        sh = sum(t['amount'] for t in a['tx'] if t['druh'] == 'vydaj' and t['jak'] == 'sdilene')
        print(a['key'], a['nazev'][:38], a['kandidati'], {k: round(v) for k, v in s.items()}, 'sdilene:', round(sh))
