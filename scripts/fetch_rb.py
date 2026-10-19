import json, sys, os, urllib.request
outdir=sys.argv[1]
ids={'1288753005':(50431651,'PRO Právo Respekt Odbornost'),'1406289005':(50520013,'SPD a PRO Právo Respekt Odbornost')}
for acc,(idb,owner) in ids.items():
    tx=[]; fi=0
    while True:
        u=f'https://www.rb.cz/frontend-controller/backend-data/transparent-account/transactionList?idBankAccount={idb}&language=cs&fromIndex={fi}&maxResults=100&dateFrom=2026-01-01&dateTo=2026-10-19&q='
        r=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read())
        for t in r['transactions']:
            tx.append({'date':t['datum'][:10],'amount':t['amount'],'type':t.get('transactionType',''),'counterparty':t.get('accountName') or '','message':t.get('info') or '','ks':t.get('constSymbol') or '','vs':t.get('varSymbol') or '','ss':t.get('specSymbol') or '','note':''})
        if r['endOfRecords'] or not r['transactions']: break
        fi=r['nextStartIndex']
    json.dump({'bank':'rb','id':acc,'url':'https://www.rb.cz/povinne-zverejnovane-informace/transparentni-ucty?path=transactions&accountNumber='+acc,'owner':owner,'name':'','number':acc+'/5500','summary':{},'tx':tx},open(os.path.join(outdir,f'rb_{acc}.json'),'w'),ensure_ascii=False,indent=0)
    print(acc,owner,len(tx),round(sum(x['amount'] for x in tx if x['amount']>0)),round(sum(x['amount'] for x in tx if x['amount']<0)), tx[-1]['date'] if tx else '')
