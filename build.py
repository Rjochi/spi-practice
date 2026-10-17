"""Build the static web app with Python 3. No packages required."""
import html
import json
import re
from pathlib import Path
from src.questions import QUESTIONS, AUDIT

ROOT=Path(__file__).parent
OUT=ROOT/'dist'
OUT.mkdir(exist_ok=True)
template=(ROOT/'src/index.html').read_text()
template=template.replace('/* QUESTIONS */','const QUESTIONS = '+json.dumps(QUESTIONS,ensure_ascii=False).replace('</','<\\/')+';')
template=template.replace('/* CORE */',(ROOT/'src/core.js').read_text()).replace('/* APP */',(ROOT/'src/app.js').read_text())
(OUT/'SPI練習.html').write_text(template)
(ROOT/'docs/index.html').write_text(template)
(ROOT/'docs/.nojekyll').write_text('')
(OUT/'questions.json').write_text(json.dumps(QUESTIONS,ensure_ascii=False,indent=2))
(OUT/'audit.json').write_text(json.dumps(AUDIT,ensure_ascii=False,indent=2))

# A readable offline design document, generated from the project documentation.
def inline(text):
    text=html.escape(text)
    return re.sub(r'\[([^]]+)\]\((https://[^)]+)\)',r'<a href="\2">\1</a>',text)

blocks=[]
table=False
ul=False
for line in (ROOT/'docs/DESIGN.md').read_text().splitlines():
    if line.startswith('|'):
        if not table:
            blocks.append('<table>');table=True
        if re.match(r'^\|[\s:|\-]+\|$',line):continue
        cells=line.strip('|').split('|')
        blocks.append('<tr>'+''.join('<td>'+inline(x.strip())+'</td>' for x in cells)+'</tr>')
        continue
    if table:blocks.append('</table>');table=False
    if line.startswith('- ') or re.match(r'^\d+\. ',line):
        if not ul:blocks.append('<ul>');ul=True
        blocks.append('<li>'+inline(re.sub(r'^(?:- |\d+\. )','',line))+'</li>');continue
    if ul:blocks.append('</ul>');ul=False
    if line.startswith('#'):
        level=len(line)-len(line.lstrip('#'));blocks.append(f'<h{level}>{inline(line[level:].strip())}</h{level}>')
    elif line.strip():blocks.append('<p>'+inline(line)+'</p>')
if table:blocks.append('</table>')
if ul:blocks.append('</ul>')
design='''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SPI練習 Web版設計書</title><style>body{font:16px/1.9 -apple-system,BlinkMacSystemFont,"Segoe UI",Meiryo,sans-serif;color:#243931;max-width:900px;margin:auto;padding:36px 24px;background:#fafbf7}h1{font-size:29px}h2{font-size:22px;margin-top:42px;border-bottom:1px solid #d5dfd1;padding-bottom:8px}h3{font-size:18px}table{border-collapse:collapse;width:100%;font-size:14px}td{border:1px solid #d5dfd1;padding:9px 12px}tr:first-child{background:#e9f0e3;font-weight:700}a{color:#245a46}@media print{body{background:white;font-size:11pt}h2{break-after:avoid}tr{break-inside:avoid}}</style><body>'''+''.join(blocks)+'</body></html>'
(OUT/'設計書.html').write_text(design)
(ROOT/'docs/design.html').write_text(design)
print(f'Built {len(QUESTIONS)} questions; app {len(template.encode()):,} bytes')
