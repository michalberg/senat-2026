import re, html, json, sys, urllib.request, os
ucty=json.load(open(sys.argv[1])); outdir=sys.argv[2]; os.makedirs(outdir,exist_ok=True)
def num(s): return float(s.replace('\xa0CZK','').replace('CZK','').replace(' ','').replace('\xa0','').replace(',','.'))
for u in ucty:
    url=u['url']
    if not url or 'ib.fio.cz' not in url: continue
    a=re.search(r'a=(-?\d+)',url).group(1)
    raw=os.path.join(outdir,f'fio_{a}.html')
    if not os.path.exists(raw):
        req=urllib.request.Request(f'https://ib.fio.cz/ib/transparent?a={a}&f=01.01.2026&t=19.10.2026',headers={'User-Agent':'Mozilla/5.0'})
        open(raw,'wb').write(urllib.request.urlopen(req,timeout=60).read())
    t=open(raw,encoding='utf-8').read()
    def field(lbl):
        m=re.search(lbl+r'.*?</[^>]+>\s*(.*?)</',t,re.S)
        return html.unescape(re.sub('<[^>]+>','',m.group(1))).strip() if m else ''
    tabs=re.findall(r'<table[^>]*>(.*?)</table>',t,re.S)
    summ=[html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]+>','',c))).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',tabs[0],re.S)]
    summ=dict(zip(summ[:len(summ)//2],[num(x) for x in summ[len(summ)//2:]])) if summ else {}
    tx=[]
    rows=re.findall(r'<tr[^>]*>(.*?)</tr>',tabs[-1],re.S)
    for r in rows[1:]:
        c=[html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]+>','',x))).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>',r,re.S)]
        if len(c)<9: continue
        d,m,y=c[0].split('.')
        tx.append({'date':f'20{y}-{m}-{d}','amount':num(c[1]),'type':c[2],'counterparty':c[3],'message':c[4],'ks':c[5],'vs':c[6],'ss':c[7],'note':c[8]})
    out={'bank':'fio','id':a,'url':url,'owner':field('Majitel účtu:'),'name':field('Název účtu:'),'number':field('Číslo účtu:'),
         'summary':summ,'tx':tx}
    json.dump(out,open(os.path.join(outdir,f'fio_{a}.json'),'w'),ensure_ascii=False,indent=0)
    inc=sum(x['amount'] for x in tx if x['amount']>0); exp=sum(x['amount'] for x in tx if x['amount']<0)
    print(a, out['owner'][:40], '|', out['name'][:50], len(tx), round(inc), round(exp), summ)
