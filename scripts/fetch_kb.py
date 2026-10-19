import re, json, sys, os, urllib.request, http.cookiejar, html
ucty=json.load(open(sys.argv[1])); outdir=sys.argv[2]
def num(s): return float(s.replace('CZK','').replace('\xa0','').replace(' ','').replace(',','.'))
MON={'ledna':1}
for u in ucty:
    url=u['url']
    if not url or 'kb.cz' not in url: continue
    acc=re.search(r'(\d+-\d+)$',url).group(1); q=acc.replace('-','')
    cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders=[('User-Agent','Mozilla/5.0')]
    page=op.open(f'https://www.kb.cz/cs/transparentni-ucty/{acc}',timeout=60).read().decode()
    i=page.index('WIDGETS_CONFIG=')+len('WIDGETS_CONFIG=')
    cfg,_=json.JSONDecoder().raw_decode(page[i:])
    tok=cfg['general']['requestVerificationToken']
    w=[v for k,v in cfg.items() if 'transparentaccount' in k][0]
    items=list(w['items']); total=w['pagination']['rowsCount']
    while len(items)<total:
        body=json.dumps({'query':q,'limit':100,'offset':len(items),'cultureCode':'cs-CZ','maxVisibleDays':1095}).encode()
        req=urllib.request.Request('https://www.kb.cz/api/transparentaccount/detail',data=body,headers={'Content-Type':'application/json','Accept':'application/json','__RequestVerificationToken':tok})
        r=json.loads(op.open(req,timeout=60).read())
        new=r['payload']['data']
        if not new: break
        items+=new
    # dates: "19. 10." with year "" (current year) or explicit year
    tx=[]
    for it in items:
        d,m=[int(x) for x in it['date'].replace(' ','').strip('.').split('.')[:2]]
        y=int(it['year']) if it.get('year') else 2026
        info=it['info']; add=info.get('additionalInfo','') or ''
        sym=dict(re.findall(r'(SS|VS|KS):\s*(\S+?)(?:,|$)',add))
        tx.append({'date':f'{y}-{m:02d}-{d:02d}','amount':num(it['amount']['value']),'type':info.get('title',''),
                   'counterparty':'','message':html.unescape(info.get('transparentAccountInfo','') or '').strip(),'ks':sym.get('KS',''),'vs':sym.get('VS',''),'ss':sym.get('SS',''),'note':''})
    out={'bank':'kb','id':acc,'url':url,'owner':u['cells'][0],'name':'','number':acc+'/0100','summary':{'Běžný zůstatek':num(w['balance']['amount'])},'tx':tx}
    json.dump(out,open(os.path.join(outdir,f'kb_{acc}.json'),'w'),ensure_ascii=False,indent=0)
    inc=sum(x['amount'] for x in tx if x['amount']>0); exp=sum(x['amount'] for x in tx if x['amount']<0)
    print(acc,u['cells'][0][:40],len(tx),'/',total,round(inc),round(exp),w['balance']['amount'],tx[-1]['date'] if tx else '')
