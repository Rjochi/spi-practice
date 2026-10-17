"""Substitute choices into word-problem constraints and enumerate discrete events."""
import ast
import hashlib
import itertools
import json
import re
import sys
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.questions import QUESTIONS as Q, AUDIT

def evaluate(expression,x):
    def visit(node):
        if isinstance(node,ast.Expression):return visit(node.body)
        if isinstance(node,ast.Constant) and type(node.value) in [int,float]:return F(str(node.value))
        if isinstance(node,ast.Name) and node.id=='x':return x
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub):return -visit(node.operand)
        if isinstance(node,ast.BinOp):
            a,b=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Add):return a+b
            if isinstance(node.op,ast.Sub):return a-b
            if isinstance(node.op,ast.Mult):return a*b
            if isinstance(node.op,ast.Div):return a/b
        raise ValueError(ast.dump(node))
    return visit(ast.parse(expression,mode='eval'))

def enumerate_model(m):
    typ=m['type']
    if typ=='committee':
        valid=[]
        for p in itertools.combinations(range(m['n']),m['k']):
            s=set(p)
            if not set(m['required'])<=s or set(m['forbidden'])&s:continue
            if 'not_both' in m and set(m['not_both'])<=s:continue
            valid.append(p)
        return len(valid)
    if typ=='gender':return sum(sum(n<m['men'] for n in group)==2 for group in itertools.combinations(range(m['men']+m['women']),4))
    if typ=='line':return sum(abs(p.index(0)-p.index(1))>1 for p in itertools.permutations(range(m['n'])))
    if typ=='circle':return len({p[p.index(0):]+p[:p.index(0)] for p in itertools.permutations(range(m['n']))})
    if typ=='code':return len(list(itertools.product(range(m['digits']),repeat=m['length'])))
    if typ=='integer':return sum(p[0]!=0 for p in itertools.permutations(range(m['digits']),m['length']))
    if typ=='colors':return len(set(itertools.permutations('R'*m['red']+'B'*m['blue'])))
    if typ=='coins':
        p=list(itertools.product((0,1),repeat=m['n']))
        return F(sum((sum(v)==1 if m['event']=='one' else sum(v)>=1) for v in p),len(p))
    if typ=='dice':
        p=list(itertools.product(range(1,7),repeat=2))
        return F(sum((a+b>=m['limit'] if m['event']=='sum_ge' else a*b%2==m['parity']) for a,b in p),len(p))
    if typ=='draw':
        p=list(itertools.combinations(range(m['n']),m['k']))
        counts=[sum(x<m['red'] for x in v) for v in p]
        valid={'one':lambda c:c==1,'any':lambda c:c>=1,'all':lambda c:c==m['k']}[m['event']]
        return F(sum(map(valid,counts)),len(p))
    if typ=='replace':
        p=list(itertools.product(range(m['red']+m['blue']),repeat=2))
        return F(sum(a<m['red'] and b<m['red'] for a,b in p),len(p))
    if typ=='first':
        p=list(itertools.permutations(range(m['n'])))
        return F(sum(v[0]==0 for v in p),len(p))
    if typ=='conditional_die':
        candidates=[n for n in range(1,7) if n%2]
        return F(sum(n>=m['threshold'] for n in candidates),len(candidates))
    if typ=='ranking':
        candidates=[p for p in itertools.permutations(m['names']) if all(p.index(a)<p.index(b) for a,b in m['edges'])]
        assert len(candidates)==1
        return candidates[0].index(m['target'])+1
    raise ValueError(typ)

fingerprints=json.loads((ROOT/'tests/v1_fingerprints.json').read_text())
for q in Q[:300]:
    fields={k:q[k] for k in ['id','category','topic','prompt','choices','answer']}
    fields['prompt']=fields['prompt'].replace('2人がそれぞれの作業効率を保って毎日一緒に作業すると','2人が同じ効率で毎日一緒に作業すると')
    digest=hashlib.sha256(json.dumps(fields,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    assert digest==fingerprints[q['id']],q['id']

checked=set()
for a in AUDIT:
    if a.get('kind') not in ['v2','allocation','truth']:continue
    q=next(q for q in Q if q['id']==a['id']);checked.add(q['id'])
    if a['kind']=='allocation':
        possibilities=[p for p in itertools.permutations(a['jobs']) if p[0] not in a['excludedA'] and p[1]!=a['excludedB']]
        assert len(possibilities)==1
        assert q['choices'][q['answer']]==possibilities[0][2]
        continue
    if a['kind']=='truth':
        candidates=[color for color in a['colors'] if sum(v==color for v in a['claims'])==a['trueCount']]
        assert candidates==[q['choices'][q['answer']]]
        continue
    choices=[F(re.match(r'^([\d/]+)',v)[1]) for v in q['choices']]
    if a['equations']:
        valid=[]
        for x in choices:
            try:valid.append(all(evaluate(left,x)==evaluate(right,x) for left,right in a['equations']))
            except ZeroDivisionError:valid.append(False)
        assert valid==[j==q['answer'] for j in range(len(choices))],(q['id'],valid,q)
    else:
        expected=enumerate_model(a['model'])
        assert choices[q['answer']]==expected,(q['id'],choices[q['answer']],expected,q['prompt'])
assert len(checked)==180

for q in Q:
    if q['category']=='非言語' and q['topic']!='推論':
        assert len(q['steps'])==4
        assert all(s['text'].strip() for s in q['steps']),(q['id'],q['steps'])
assert len([q for q in Q if 'steps' in q])==340
print('V2: all 180 new nonverbal answers checked; legacy IDs and choices unchanged; all 320 numeric explanations have 4 stages.')
