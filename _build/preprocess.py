import re, sys

CHAPTERS = ['1_introducao.tex','2_am.tex','3_ranking.tex','4_roc.tex','5_calibracao.tex','7_conclusoes.tex']

def strip_comments(s):
    out = []
    for line in s.splitlines(True):
        res = ''
        i = 0
        had_comment = False
        while i < len(line):
            c = line[i]
            if c == '%' and (i == 0 or line[i-1] != '\\'):
                had_comment = True
                break
            res += c
            i += 1
        if had_comment and res.strip() == '':
            continue
        out.append(res.rstrip() + ('\n' if line.endswith('\n') else ''))
    return ''.join(out)

IMG = r'\\includegraphics(?:\[[^\]]*\])?\s*\{[^}]+\}'

for f in CHAPTERS:
    s = open(f, encoding='utf-8').read()
    s = strip_comments(s)
    s = re.sub(r'\\(?:vspace|hspace)\s*\{[^{}]*\}', '', s)
    s = re.sub(r'\\scalebox\{[^}]*\}\{\s*(\\begin\{tabular\}.*?\\end\{tabular\})\s*\}', r'\1', s, flags=re.S)
    s = re.sub(r'\\subfloat(?:\[[^\]]*\])?\s*\{\s*(' + IMG + r')\s*\}', r'\1', s, flags=re.S)
    s = re.sub(r'\\noindent\s*\\makebox\s*\[[^\]]*\]\s*\{\s*(' + IMG + r')\s*\}', r'\1', s, flags=re.S)
    s = s.replace('\\centering', '').replace('\\noindent', '')
    open(f, 'w', encoding='utf-8').write(s)
    print('preprocessado', f)
