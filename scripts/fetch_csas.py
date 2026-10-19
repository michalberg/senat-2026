import re, json, sys, os, urllib.request
ucty=json.load(open(sys.argv[1])); outdir=sys.argv[2]
K='08aef2f7-8b72-4ae1-831e-2155d81f46dd'; B='https://www.csas.cz/webapi/api/v3/transparentAccounts/'
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={'WEB-API-key':K,'User-Agent':'Mozilla/5.0'}),timeout=60).read())
for u in ucty:
    url=u['url']
    if not url or 'csas.cz' not in url: continue
    acc=re.search(r'(\d{6}-\d+)',url).group(1)
    info=get(B+acc)
    tx=[]; p=0
    while True:
        r=get(B+f'{acc}/transactions?page={p}&size=200&dateFrom=2026-01-01&dateTo=2026-10-19&sort=processingDate&order=DESC')
        for t in r['transactions']:
            s=t.get('sender') or {}; rc=t.get('receiver') or {}
            from datetime import datetime, timedelta
            dt=datetime.fromisoformat(t['processingDate'].replace('+00:00',''))+timedelta(hours=2)
            tx.append({'date':dt.strftime('%Y-%m-%d'),'amount':t['amount']['value'],'type':t.get('typeDescription',''),
                       'counterparty':s.get('name') or '','message':s.get('description') or '','ks':s.get('constantSymbol') or '','vs':s.get('variableSymbol') or '','ss':s.get('specificSymbol') or '','note':''})
        if r.get('nextPage') is None or r['nextPage']<=p or p+1>=r['pageCount']: break
        p=r['nextPage']
    name=u['cells'][0] if u['typ'].startswith('strany') else u['cells'][1]
    out={'bank':'csas','id':acc,'url':url,'owner':info.get('name',name),'name':info.get('description',''),'number':acc+'/0800','summary':{'Běžný zůstatek':info.get('balance'),'actualizationDate':info.get('actualizationDate')},'tx':tx}
    json.dump(out,open(os.path.join(outdir,f'csas_{acc}.json'),'w'),ensure_ascii=False,indent=0)
    inc=sum(x['amount'] for x in tx if x['amount']>0); exp=sum(x['amount'] for x in tx if x['amount']<0)
    print(acc,name[:40],len(tx),r['recordCount'],round(inc),round(exp),info.get('balance'),tx[-1]['date'] if tx else '')
