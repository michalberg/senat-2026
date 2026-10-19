"""Darovací (zvláštní) účty stran, které kandidovaly do Senátu 2026 → data/raw/darovaci/tx/*.json
Pohyby od 1. 1. 2026 do 19. 10. 2026. ČSOB (KSČM, GEN) chrání účty proti robotům – stahují se přes prohlížeč."""
import json, os, re, sys, html, urllib.request, http.cookiejar
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'raw', 'darovaci', 'tx')
os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0'}
FROM, TO = '2026-01-01', '2026-10-19'
# opravy URL z registru (zastaralé nebo nejednoznačné odkazy)
FIX = {'71339728': 'https://ib.fio.cz/ib/transparent?a=2103311257', '06695205': 'https://www.csas.cz/cs/transparentni-ucty#/000000-6705433399',
       '21005826': 'https://ib.fio.cz/ib/transparent?a=2103258572'}
SKIP = {'64933911'}  # Volte Pravý Blok – nesouvisí


def num(s): return float(s.replace('CZK', '').replace('\xa0', '').replace(' ', '').replace(',', '.'))


def get(url, headers=None, data=None):
    return urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}, data=data), timeout=120).read()


def fio(a):
    # Fio vrací nejvýš 2000 pohybů na dotaz – stahujeme po měsících
    tx = []
    for m in range(1, 11):
        end = '19.10.2026' if m == 10 else (datetime(2026, m + 1, 1) - timedelta(days=1)).strftime('%d.%m.%Y')
        tx += fio_range(a, f'01.{m:02d}.2026', end)
    return tx


def fio_range(a, f, t_):
    t = get(f'https://ib.fio.cz/ib/transparent?a={a}&f={f}&t={t_}').decode()
    tabs = re.findall(r'<table[^>]*>(.*?)</table>', t, re.S)
    tx = []
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>', tabs[-1], re.S)[1:]:
        c = [html.unescape(re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', x))).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
        if len(c) < 9: continue
        d, m, y = c[0].split('.')
        tx.append({'date': f'20{y}-{m}-{d}', 'amount': num(c[1]), 'counterparty': c[3], 'message': c[4] + ' ' + c[8], 'vs': c[6], 'ss': c[7]})
    if len(tx) >= 2000: print('  ! 2000 pohybů v rozsahu', a, f, t_)
    return tx


def kb(acc):
    cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); op.addheaders = list(UA.items())
    page = op.open(f'https://www.kb.cz/cs/transparentni-ucty/{acc}', timeout=60).read().decode()
    i = page.index('WIDGETS_CONFIG=') + len('WIDGETS_CONFIG=')
    cfg, _ = json.JSONDecoder().raw_decode(page[i:])
    tok = cfg['general']['requestVerificationToken']
    w = [v for k, v in cfg.items() if 'transparentaccount' in k][0]
    items, total = list(w['items']), w['pagination']['rowsCount']
    while len(items) < total:
        body = json.dumps({'query': w['query'], 'limit': 100, 'offset': len(items), 'cultureCode': 'cs-CZ', 'maxVisibleDays': 1095}).encode()
        r = json.loads(op.open(urllib.request.Request('https://www.kb.cz/api/transparentaccount/detail', data=body, headers={'Content-Type': 'application/json', 'Accept': 'application/json', '__RequestVerificationToken': tok}), timeout=60).read())
        new = r['payload']['data']
        if not new: break
        items += new
        # KB řadí od nejnovějších – starší než FROM už nepotřebujeme
        if new[-1].get('year') and int(new[-1]['year']) < 2026: break
    tx = []
    for it in items:
        d, m = [int(x) for x in it['date'].replace(' ', '').strip('.').split('.')[:2]]
        y = int(it['year']) if it.get('year') else 2026
        info = it['info']
        tx.append({'date': f'{y}-{m:02d}-{d:02d}', 'amount': num(it['amount']['value']), 'counterparty': '',
                   'message': html.unescape(info.get('transparentAccountInfo') or '').strip(), 'vs': '', 'ss': ''})
    return [t for t in tx if t['date'] >= FROM]


def csas(acc):
    K = '08aef2f7-8b72-4ae1-831e-2155d81f46dd'; B = 'https://www.csas.cz/webapi/api/v3/transparentAccounts/'
    tx, p = [], 0
    while True:
        r = json.loads(get(B + f'{acc}/transactions?page={p}&size=200&dateFrom={FROM}&dateTo={TO}&sort=processingDate&order=DESC', {'WEB-API-key': K}))
        for t in r['transactions']:
            s = t.get('sender') or {}
            dt = datetime.fromisoformat(t['processingDate'].replace('+00:00', '')) + timedelta(hours=2)
            tx.append({'date': dt.strftime('%Y-%m-%d'), 'amount': t['amount']['value'], 'counterparty': s.get('name') or '', 'message': s.get('description') or '', 'vs': s.get('variableSymbol') or '', 'ss': s.get('specificSymbol') or ''})
        if r.get('nextPage') is None or p + 1 >= r['pageCount']: break
        p = r['nextPage']
    return tx


RB_LIST = None


def rb(number):
    global RB_LIST
    if RB_LIST is None: RB_LIST = json.loads(get('https://www.rb.cz/frontend-controller/backend-data/transparent-account/list?language=cs'))
    idb = next(x['currencyItems'][0]['idBankAccount'] for x in RB_LIST if x['numberPart2'] == number)
    tx, fi = [], 0
    while True:
        r = json.loads(get(f'https://www.rb.cz/frontend-controller/backend-data/transparent-account/transactionList?idBankAccount={idb}&language=cs&fromIndex={fi}&maxResults=200&dateFrom={FROM}&dateTo={TO}&q='))
        for t in r['transactions']:
            tx.append({'date': t['datum'][:10], 'amount': t['amount'], 'counterparty': t.get('accountName') or '', 'message': t.get('info') or '', 'vs': t.get('varSymbol') or '', 'ss': t.get('specSymbol') or ''})
        if r['endOfRecords'] or not r['transactions']: break
        fi = r['nextStartIndex']
    return tx


def moneta(a):
    t = get(f'https://transparentniucty.moneta.cz/{a}?from={FROM}&to={TO}').decode()
    i = t.index('apiDetailResponse\\":') + len('apiDetailResponse\\":')
    s = t[i:].encode().decode('unicode_escape').encode('latin1').decode('utf-8')
    d, _ = json.JSONDecoder().raw_decode(s.replace('\\"', '"'))
    return [{'date': x['transactionDate'], 'amount': (-1 if x['creditDebitFlag'] == 7 else 1) * x['amount'], 'counterparty': x.get('counterpartyAccountName', ''),
             'message': x.get('messageForRecipient', ''), 'vs': str(x.get('variableSymbol', '')), 'ss': ''} for x in d['transactions']]


sel = json.load(open(os.path.join(ROOT, 'data', 'darovaci_vyber.json'), encoding='utf-8'))
for s in sel:
    ic = s['ico']
    if ic in SKIP: continue
    url = FIX.get(ic, s['url']).strip()
    path = os.path.join(OUT, f'{ic}.json')
    if os.path.exists(path) and '-f' not in sys.argv: continue
    try:
        if 'fio.cz' in url: tx = fio(re.search(r'a=(-?\d+)', url).group(1)); bank = 'fio'
        elif 'kb.cz' in url: tx = kb(url.rstrip('/').split('/')[-1]); bank = 'kb'
        elif 'csas.cz' in url: tx = csas(re.search(r'(\d{6}-\d+)', url).group(1)); bank = 'csas'
        elif 'rb.cz' in url: tx = rb(re.search(r'(\d{8,10})/5500', s['ucet']).group(1)); bank = 'rb'
        elif 'moneta' in url: tx = moneta(url.rstrip('/').split('/')[-1]); bank = 'moneta'
        else: print('SKIP', ic, s['nazev'][:40], url[:60]); continue
    except Exception as e:
        print('ERR', ic, s['nazev'][:40], url[:60], e); continue
    json.dump({'ico': ic, 'nazev': s['nazev'], 'ucet': s['ucet'], 'url': url, 'bank': bank, 'tx': tx}, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    inc = [t for t in tx if t['amount'] > 0]
    print(ic, s['nazev'][:40], bank, len(tx), 'příjmů', len(inc), round(sum(t['amount'] for t in inc)))
