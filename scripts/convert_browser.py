"""Účty stažené přes prohlížeč (ČSOB, UniCredit – chráněné proti robotům) → data/raw/ucty/tx/*.json"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, 'data', 'raw', 'ucty', 'browser'); TX = os.path.join(ROOT, 'data', 'raw', 'ucty', 'tx')
META = {'csob_317516013': ('Komunistická strana Čech a Moravy', '317516013/0300', 'https://www.csob.cz/firmy/bezne-ucty/transparentni-ucty/ucet?account=317516013'),
        'csob_138388888': ('GEN', '138388888/0300', 'https://www.csob.cz/firmy/bezne-ucty/transparentni-ucty/ucet?account=138388888'),
        'csob_369605931': ('Jindřich Růžička', '369605931/0300', 'https://www.csob.cz/firmy/bezne-ucty/transparentni-ucty/ucet?account=369605931'),
        'unicredit_CZ9627000000001780799048': ('Hnutí Generace', '1780799048/2700', 'https://www.unicreditbank.cz/cs/ostatni/transparentni-ucet.html?IBAN=CZ9627000000001780799048')}
for f, bank in (('csob_rows.json', 'csob'), ('unicredit_rows.json', 'unicredit')):
    for acc, rows in json.load(open(os.path.join(B, f), encoding='utf-8')).items():
        key = f'{bank}_{acc}'
        owner, num, url = META[key]
        tx = [{'date': r[0], 'amount': r[1], 'type': r[2], 'counterparty': r[3].strip(), 'message': r[4].replace('§', 'volby Senát - '),
               'note': '', 'ks': r[5], 'vs': r[6], 'ss': '' if r[7] == '0' else r[7]} for r in rows]
        json.dump({'bank': bank, 'id': acc, 'url': url, 'owner': owner, 'name': '', 'number': num, 'summary': {}, 'tx': tx,
                   'zdroj': 'staženo přes prohlížeč 19. 10. 2026'}, open(os.path.join(TX, key + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print(key, len(tx))
