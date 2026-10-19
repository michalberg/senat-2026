import re, html, json, sys, glob
out=[]
for f in sorted(glob.glob(sys.argv[1]+'/seznam_*.html')):
    t=open(f).read()
    title=re.search(r'senátní volby 2026 - ([^<]+)',t).group(1).strip()
    tbody=t.split('<tbody')[1].split('</tbody>')[0] if '<tbody' in t else t
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>',tbody,re.S):
        tds=re.findall(r'<td[^>]*>(.*?)</td>',r,re.S)
        if not tds: continue
        href=re.findall(r'href="([^"]+)"',r)
        cells=[html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]+>','',c))).strip() for c in tds]
        out.append({'typ':title,'cells':cells,'url':html.unescape(href[0]) if href else None})
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False,indent=1)
for o in out: print(o['typ'][:6],o['cells'][:4],o['url'])
