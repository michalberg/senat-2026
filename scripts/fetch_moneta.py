import re, json, sys, os, urllib.request
ucty=json.load(open(sys.argv[1])); outdir=sys.argv[2]
def grab(a,q):
    t=urllib.request.urlopen(urllib.request.Request(f'https://transparentniucty.moneta.cz/{a}{q}',headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read().decode()
    i=t.index('apiDetailResponse\\":')+len('apiDetailResponse\\":')
    s=t[i:]; s=s.encode().decode('unicode_escape').encode('latin1').decode('utf-8')
    d,_=json.JSONDecoder().raw_decode(s.replace('\\"','"'))
    return d
for u in ucty:
    url=u['url']
    if not url or 'moneta' not in url: continue
    a=url.rstrip('/').split('/')[-1]
    d=grab(a,'?from=2026-01-01&to=2026-10-19')
    print(a,d['shortName'],d['balance'],len(d['transactions']),d['endOfTransactions'], set(t['creditDebitFlag'] for t in d['transactions']))
    tx=[]
    for t in d['transactions']:
        sign=-1 if t['creditDebitFlag']==7 else 1
        tx.append({'date':t['transactionDate'],'amount':sign*t['amount'],'type':t.get('descr1',''),'counterparty':t.get('counterpartyAccountName',''),'message':t.get('messageForRecipient',''),'ks':str(t.get('constantSymbol','')),'vs':str(t.get('variableSymbol','')),'ss':str(t.get('specificSymbol','')),'note':''})
    json.dump({'bank':'moneta','id':a,'url':url,'owner':d['shortName'],'name':'','number':a+'/0600','summary':{'Běžný zůstatek':d['balance']},'tx':tx,'raw':d['transactions']},open(os.path.join(outdir,f'moneta_{a}.json'),'w'),ensure_ascii=False,indent=0)
    for x in tx: print('  ',x['date'],x['amount'],x['counterparty'][:30],x['message'][:60])
