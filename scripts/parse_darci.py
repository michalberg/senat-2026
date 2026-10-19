"""Seznamy dárců ze zpravy.udh.gov.cz → data/darci.json"""
import re, html, json, os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U = os.path.join(ROOT, 'data', 'raw', 'udh')
out = {'subjekty': []}
for seq in (1, 2):
    t = open(os.path.join(U, f'sponzori{seq}.html'), encoding='utf-8').read()
    for r in re.findall(r'<tr>(.*?)</tr>', t, re.S):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)
        if len(tds) < 2: continue
        name = html.unescape(re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', tds[0]))).strip()
        link = re.search(r'href="([^"]+)"', r)
        status = html.unescape(re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', tds[1]))).strip()
        rec = {'seq': seq, 'nazev': name, 'url': link.group(1) if link else None, 'stav': status, 'darci': []}
        if link:
            slug = link.group(1).split('/s2026/')[1].replace('/', '_')
            rec['slug'] = slug.split('_')[0]
            d = open(os.path.join(U, 'darci', slug + '.html'), encoding='utf-8').read()
            for row in re.findall(r'<tr>(.*?)</tr>', d, re.S):
                c = [html.unescape(re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', x))).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)]
                if len(c) >= 2 and c[0]:
                    ident = c[1]
                    po = bool(re.search(r's\.\s?r\.\s?o|a\.\s?s\.|spol\.|z\.\s?s\.|o\.\s?p\.\s?s|v\.\s?o\.\s?s|k\.\s?s\.|družstvo|s\.r\.o|SE\b|z\.ú\.|nadace|ltd|gmbh', c[0], re.I)) or bool(re.fullmatch(r'\d{6,8}', ident))
                    rec['darci'].append({'dárce': c[0], 'id': ident, 'po': po})
        out['subjekty'].append(rec)
missing = re.search(r'neoznámily své dárce a sponzory:.*?<ul[^>]*>(.*?)</ul>', open(os.path.join(U, 'sponzori1.html'), encoding='utf-8').read(), re.S)
out['neoznamili_1kolo'] = [html.unescape(re.sub('<[^>]+>', '', x)).strip() for x in re.findall(r'<li>(.*?)</li>', missing.group(1), re.S)] if missing else []
json.dump(out, open(os.path.join(ROOT, 'data', 'darci.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(out['subjekty']), sum(len(s['darci']) for s in out['subjekty']), out['neoznamili_1kolo'][:30])
