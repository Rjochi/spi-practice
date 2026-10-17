import itertools
import json
import math
import re
import sys
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.questions import QUESTIONS as Q, AUDIT

assert len(Q)==600
assert len({q['id'] for q in Q})==600
assert Counter(q['category'] for q in Q)=={'言語':240,'非言語':360}
assert set(Counter(q['topic'] for q in Q).values())=={40}
assert len({(q['prompt'],json.dumps(q.get('table'))) for q in Q})==600
for q in Q:
    assert 0<=q['answer']<len(q['choices'])
    assert len(set(q['choices']))==len(q['choices'])
    assert q['explanation'].strip() and q['tip'].strip()
    assert not any('<' in s or '</script' in s for s in [q['prompt'],*q['choices'],q['explanation']])

def value(q):
    text=q['choices'][q['answer']]
    return F(re.match(r'^([\d/]+)',text)[1])

for topic in ['割合・比','損益算','速さ','仕事算','集合','場合の数','確率','表の読み取り']:
    qs=[q for q in Q if q['topic']==topic and int(q['id'][1:])<=300]
    for j,q in enumerate(qs):
        p=j%5;i=j//5
        if topic=='割合・比':
            if p==0: expected=sum(1 for n in range(80+40*i) if n<(80+40*i)*(15+5*i)/100)
            elif p==1: expected=12*(2+i)
            elif p==2: expected=200+100*i
            elif p==3: expected=F((400+100*i)-(300+75*i),400+100*i)*100
            else:
                x,y=24+6*i,36+9*i
                candidates=[t for t in range(x+1) if y+t==2*(x-t)]
                assert len(candidates)==1;expected=candidates[0]
        elif topic=='損益算':
            if p==0: expected=(800+200*i)+F(800+200*i,4)
            elif p==1: expected=(2000+500*i)-F(2000+500*i,5)
            elif p==2: expected=F((1500+500*i)-(1200+400*i),1200+400*i)*100
            elif p==3: expected=F(1000+500*i,5)
            else:expected=(100+20*i)*(2*(25+5*i)-(40+10*i))
        elif topic=='速さ':
            if p==0:expected=F((48+12*i)*25,60)
            elif p==1:expected=F(18+6*i,6)
            elif p==2:expected=F(30+10*i,6+i)
            elif p==3:expected=F((2+i)*60,4+i)
            else:
                # Take a concrete common-multiple distance for each leg.
                a,b=30+10*i,60+20*i;distance=a*b
                expected=F(2*distance,F(distance,a)+F(distance,b))
        elif topic=='仕事算':
            if p==0:
                a,b=[(6,3),(12,6),(8,8),(10,15)][i];expected=F(a*b,a+b)
            elif p==1:expected=F((4+i)*12,6+i)
            elif p==2:expected=F(12+4*i-3,2)
            elif p==3:expected=12+4*i
            else:expected=F(240+120*i,(2+i)*4)
        elif topic=='集合':
            total,a,b,both=60+10*i,30+5*i,25+4*i,10+2*i
            A=set(range(a));B=set(range(a-both,a-both+b));universe=set(range(total))
            expected=[len(A|B),len(universe-(A|B)),len(A-B),len(A&B),len(A^B)][p]
        elif topic=='場合の数':
            n=5+i
            if p==0:expected=len(list(itertools.combinations(range(n),2)))
            elif p==1:expected=len(list(itertools.permutations(range(n),2)))
            elif p==2:expected=len(list(itertools.product(range(3+i),range(2+i))))
            elif p==3:expected=sum(abs(order.index(0)-order.index(1))==1 for order in itertools.permutations(range(4+i)))
            else:expected=sum(sum(bits)==2+i for bits in itertools.product((0,1),repeat=5+i))
        elif topic=='確率':
            red,blue=3+i,5
            combos=list(itertools.combinations(range(red+blue),2))
            if p==0:expected=F(red,red+blue)
            elif p==1:expected=F(sum(a<red and b<red for a,b in combos),len(combos))
            elif p==2:expected=F(sum(a<red or b<red for a,b in combos),len(combos))
            elif p==3:expected=F(sum(a+b==3+i for a,b in itertools.product(range(1,7),repeat=2)),36)
            else:expected=F(1,len(list(itertools.product((0,1),repeat=2+i))))
        else:
            rows=q['table']['rows']
            expected=[sum(row[2] for row in rows),rows[2][2]-rows[2][1],sum(rows[1][1:]),rows[0][2]-rows[1][2],sum(row[2]-row[1] for row in rows)][p]
        assert value(q)==expected,(q['id'],q['prompt'],value(q),expected)
        for c in q['choices']:
            v=F(re.match(r'^([\d/]+)',c)[1]);assert v>=0
            if topic=='確率':assert v<=1

for audit in AUDIT:
    if audit.get('kind')=='order':
        possibilities=[p for p in itertools.permutations('ABCD') if all(p.index(a)<p.index(b) for a,b in audit['edges'])]
        truths=[all(p.index(a)<p.index(b) for p in possibilities) for a,b in audit['options']]
        assert truths==[True,False,False,False]
    elif audit.get('kind')=='adjacency':
        possibilities=[p for p in itertools.permutations('ABCD') if p[0]==audit['fixed'] and p.index(audit['right'])-p.index(audit['left'])==1]
        q=next(q for q in Q if q['id']==audit['id'])
        assert q['choices'][q['answer']]=='・'.join(map(str,sorted({p.index(audit['person'])+1 for p in possibilities})))+'番目'

source=(ROOT/'dist/SPI練習.html').read_text()
assert not re.search(r'<(?:script|link|img|iframe)[^>]+(?:src|href)=["\']https?://',source,re.I)
assert 'fetch(' not in source and 'XMLHttpRequest' not in source and 'WebSocket' not in source
assert "connect-src 'none'" in source
assert '/* QUESTIONS */' not in source
print('Questions: 600 records, legacy 160 numeric/20 logic answers and offline dependencies passed.')
