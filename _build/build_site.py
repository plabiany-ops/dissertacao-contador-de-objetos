import os, re, copy, html, posixpath
from bs4 import BeautifulSoup, Tag, NavigableString
from PIL import Image

ROOT = os.path.expanduser('~/dissertacao-contador-de-objetos')
BUILD = os.path.join(ROOT, '_build')
WEB = os.path.join(BUILD, 'web')

CHAPTERS = [
    dict(slug='01-introducao', hid='introdução', num=1, title='Introdução'),
    dict(slug='02-revisao-bibliografica', hid='chap:am', num=2, title='Revisão Bibliográfica'),
    dict(slug='03-metodo-proposto', hid='sec:MetodoPrincipal', num=3, title='Método Proposto'),
    dict(slug='04-experimentos-e-resultados', hid='chap:experimentos', num=4, title='Experimentos e Resultados'),
    dict(slug='05-conclusoes', hid='chap:conclusoes', num=5, title='Conclusões'),
]

PDF2PNG = {
    'image/model.pdf': 'image/model.png',
    'image/VD.pdf': 'image/VD.png',
    'image/heatmap2.pdf': 'image/heatmap2.png',
    'image/VID06_frame000147.pdf': 'image/VID06_frame000147.png',
    'image/VE.pdf': 'image/VE.png',
}

def strip_comments(s):
    out = []
    for line in s.splitlines(True):
        res = ''
        i = 0
        while i < len(line):
            c = line[i]
            if c == '%' and (i == 0 or line[i-1] != '\\'):
                break
            res += c
            i += 1
        if '%' in line[i:i+1] and res.strip() == '':
            continue
        out.append(res.rstrip() + ('\n' if line.endswith('\n') else ''))
    return ''.join(out)

def parse_width(opts):
    m = re.search(r'width\s*=\s*([0-9.]+)\\(?:textwidth|columnwidth)', opts or '')
    if m:
        return max(8, min(100, int(round(float(m.group(1)) * 100))))
    return None

def inline_latex_to_html(t):
    t = (t or '').strip()
    t = re.sub(r'\\textit\{([^{}]*)\}', r'<em>\1</em>', t)
    t = re.sub(r'\\textbf\{([^{}]*)\}', r'<strong>\1</strong>', t)
    t = t.replace('$\\sigma = 1.5$', 'σ = 1.5').replace('$\\sigma = 2.5$', 'σ = 2.5')
    t = re.sub(r'\$([^$]*)\$', r'\1', t)
    t = re.sub(r'\\[a-zA-Z]+\s*', '', t)
    t = t.replace('{', '').replace('}', '')
    return t.strip()

def parse_labels():
    labels = {}
    for fn in os.listdir(BUILD):
        if not fn.endswith('.aux'):
            continue
        text = open(os.path.join(BUILD, fn), encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'\\newlabel\{([^}]+)\}\{\{([^}]*)\}', text):
            labels[m.group(1)] = m.group(2)
    return labels

def parse_toc():
    toc = {}
    path = os.path.join(BUILD, 'tese.toc')
    current = None
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.search(r'\\contentsline \{(chapter|section|subsection|subsubsection)\}\{\\numberline \{([^}]*)\}', line)
        if not m:
            continue
        level, num = m.group(1), m.group(2)
        if level == 'chapter':
            current = int(num)
            toc[current] = {'sections': [], 'subsections': [], 'subsubsections': []}
        elif current is not None:
            if level == 'section':
                toc[current]['sections'].append(num)
            elif level == 'subsection':
                toc[current]['subsections'].append(num)
            elif level == 'subsubsection':
                toc[current]['subsubsections'].append(num)
    return toc

def parse_figmeta():
    meta = {}
    files = ['1_introducao.tex','2_am.tex','3_ranking.tex','4_roc.tex','5_calibracao.tex','7_conclusoes.tex']
    for fn in files:
        s = strip_comments(open(os.path.join(BUILD, fn), encoding='utf-8').read())
        for m in re.finditer(r'\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}', s, re.S):
            block = m.group(1)
            lm = re.search(r'\\label\{([^}]+)\}', block)
            if not lm:
                continue
            label = lm.group(1)
            items = []
            for sm in re.finditer(r'\\subfloat(?:\[([^\]]*)\])?\s*\{\s*(\\includegraphics(?:\[([^\]]*)\])?\s*\{([^}]+)\})\s*\}', block, re.S):
                cap = sm.group(1) or ''
                opts = sm.group(3) or ''
                path = sm.group(4).strip()
                path = PDF2PNG.get(path, path)
                items.append(dict(path=path, width=parse_width(opts), cap=cap))
            if not items:
                for im in re.finditer(r'\\includegraphics(?:\[([^\]]*)\])?\s*\{([^}]+)\}', block, re.S):
                    opts = im.group(1) or ''
                    path = im.group(2).strip()
                    path = PDF2PNG.get(path, path)
                    items.append(dict(path=path, width=parse_width(opts), cap=''))
            meta[label] = items
    return meta

def append_html(tag, s):
    frag = BeautifulSoup(s, 'html.parser')
    for child in list(frag.contents):
        tag.append(child.extract())

LABELS = parse_labels()
TOC = parse_toc()
FIGMETA = parse_figmeta()

soup = BeautifulSoup(open(os.path.join(WEB, 'tese.html'), encoding='utf-8').read(), 'html.parser')

DEDICATION = ''
ded_path = os.path.join(BUILD, 'agradecimentos.tex')
if os.path.exists(ded_path):
    raw = open(ded_path, encoding='utf-8').read()
    m = re.search(r'\\begin\{flushright\}(.*?)\\end\{flushright\}', raw, re.S)
    if m:
        block = m.group(1)
        block = re.sub(r'\\vspace\{[^}]*\}', '\n\n', block)
        block = re.sub(r'\\it\b', '', block)
        block = block.replace('\\\\', '\n')
        lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in block.splitlines()]
        out = []
        for ln in lines:
            if not ln and (not out or not out[-1]):
                continue
            out.append(ln)
        DEDICATION = '\n'.join(out).strip()

def section_nodes(h):
    nodes = []
    for s in h.next_siblings:
        if isinstance(s, Tag) and (s.name == 'h1' or s.get('id') == 'refs'):
            break
        nodes.append(copy.deepcopy(s))
    return nodes

def build_fragment(nodes):
    frag = BeautifulSoup('', 'html.parser')
    for n in nodes:
        frag.append(n)
    return frag

def number_headings(frag, cnum):
    secs = iter(TOC.get(cnum, {}).get('sections', []))
    subs = iter(TOC.get(cnum, {}).get('subsections', []))
    subsubs = iter(TOC.get(cnum, {}).get('subsubsections', []))
    outline = []
    for h in frag.find_all(['h2', 'h3', 'h4']):
        text = h.get_text(' ', strip=True)
        num = None
        try:
            if h.name == 'h2':
                num = next(secs)
            elif h.name == 'h3':
                num = next(subs)
            else:
                num = next(subsubs)
        except StopIteration:
            num = LABELS.get(h.get('id'))
        h['class'] = list(h.get('class', [])) + ['section-title']
        if num:
            span = frag.new_tag('span', class_='sec-num')
            span.string = str(num)
            h.insert(0, span)
            h.insert(1, NavigableString(' '))
        outline.append((h.name, h.get('id'), str(num) if num else '', text))
    return outline

def fix_class_attrs(frag):
    for el in frag.find_all(True):
        if 'class_' in el.attrs:
            val = el.attrs.pop('class_')
            if isinstance(val, str):
                val = val.split()
            el['class'] = val

def fix_equations(frag):
    for m in frag.find_all('math', attrs={'display': 'block'}):
        ann = m.find('annotation')
        if not ann:
            continue
        lm = re.search(r'\\label\{([^}]+)\}', ann.get_text())
        if not lm:
            continue
        label = lm.group(1)
        m['id'] = label
        num = LABELS.get(label)
        if not num:
            continue
        parent = m.parent
        if parent and parent.name == 'p':
            parent['class'] = list(parent.get('class', [])) + ['eq-line']
            span = frag.new_tag('span', class_='eq-num')
            span.string = f'({num})'
            parent.append(span)

def fix_missing_citations(frag):
    for span in frag.find_all('span', class_='citation'):
        if 'f1' not in (span.get('data-cites') or ''):
            continue
        prev = span.previous_sibling
        span.extract()
        if isinstance(prev, NavigableString) and prev.endswith('0 '):
            prev.replace_with(prev[:-1])

def restructure(frag):
    for fig in frag.find_all('figure'):
        label = fig.get('id')
        imgs = fig.find_all('img')
        items = FIGMETA.get(label, [])
        cap = fig.find('figcaption')
        if cap:
            cap.extract()
        for child in list(fig.children):
            child.extract()
        if imgs:
            subfigs = frag.new_tag('div', class_='subfigs')
            for i, img in enumerate(imgs):
                meta = items[i] if i < len(items) else None
                sub = frag.new_tag('div', class_='subfig')
                if meta and meta.get('width'):
                    w = meta['width']
                    sub['style'] = f'flex:0 1 {w}%;max-width:{w}%'
                img['class'] = list(img.get('class', [])) + ['figimg']
                img['loading'] = 'lazy'
                if meta and meta.get('cap'):
                    img['alt'] = inline_latex_to_html(meta['cap'])
                sub.append(img)
                if meta and meta.get('cap'):
                    capspan = frag.new_tag('span', class_='subcap')
                    append_html(capspan, inline_latex_to_html(meta['cap']))
                    sub.append(capspan)
                subfigs.append(sub)
            fig.append(subfigs)
        if cap:
            num = LABELS.get(label)
            if num:
                p = frag.new_tag('span', class_='fig-num')
                p.string = f'Figura {num}.'
                cap.insert(0, p)
                cap.insert(1, NavigableString(' '))
            fig.append(cap)
        fig['class'] = list(fig.get('class', [])) + ['figura']

    for table in frag.find_all('table'):
        tid = table.get('id')
        cap = table.find('caption')
        if cap and tid and LABELS.get(tid):
            p = frag.new_tag('span', class_='tab-num')
            p.string = f'Tabela {LABELS[tid]}.'
            cap.insert(0, p)
            cap.insert(1, NavigableString(' '))
        table['class'] = list(table.get('class', [])) + ['tabela']
        wrap = frag.new_tag('div', class_='table-wrap')
        table.wrap(wrap)

    for table in frag.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        for tr in rows:
            for cell in tr.find_all(['th', 'td'], recursive=False):
                if re.fullmatch(r'\d+-\d+', cell.get_text(strip=True)):
                    cell.decompose()
        r0 = rows[0].find_all(['th', 'td'], recursive=False)
        r1 = rows[1].find_all(['th', 'td'], recursive=False)
        if r1 and not r1[0].get_text(strip=True):
            r1[0].decompose()
            r1 = rows[1].find_all(['th', 'td'], recursive=False)
        if r0 and r1 and len(r0) == len(r1) // 2 + 1:
            r0[0]['rowspan'] = '2'

def prepare_images():
    srcs = set()
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src.startswith('image/'):
            srcs.add(src)
    total = 0
    for src in sorted(srcs):
        srcpath = os.path.join(WEB, src)
        dst = os.path.join(ROOT, 'assets', 'figuras', src[len('image/'):])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = Image.open(srcpath)
        if im.width > 1600:
            h = round(im.height * 1600 / im.width)
            im = im.resize((1600, h), Image.LANCZOS)
        if dst.lower().endswith(('.jpg', '.jpeg')):
            im.convert('RGB').save(dst, quality=88, optimize=True, progressive=True)
        else:
            im.save(dst, optimize=True)
        total += os.path.getsize(dst)
    print(f'imagens: {len(srcs)} arquivos, {total/1024/1024:.2f} MB')

def collect_figures():
    entries = []
    for ch in CHAPTERS:
        h = soup.find('h1', id=ch['hid'])
        for s in h.next_siblings:
            if isinstance(s, Tag) and (s.name == 'h1' or s.get('id') == 'refs'):
                break
            if isinstance(s, Tag) and s.name == 'figure':
                label = s.get('id')
                cap = s.find('figcaption')
                cap_html = cap.decode_contents() if cap else ''
                imgs = s.find_all('img')
                items = FIGMETA.get(label, [])
                media = []
                for i, img in enumerate(imgs):
                    meta = items[i] if i < len(items) else None
                    media.append(dict(
                        src=img.get('src', ''),
                        width=meta.get('width') if meta else None,
                        cap=inline_latex_to_html(meta.get('cap', '')) if meta else '',
                    ))
                entries.append(dict(label=label, num=LABELS.get(label), caption=cap_html,
                                    media=media, chapter=ch))
    return entries

FIGURE_ENTRIES = collect_figures()

def build_chapter(ch):
    h = soup.find('h1', id=ch['hid'])
    frag = build_fragment(section_nodes(h))
    outline = number_headings(frag, ch['num'])
    fix_equations(frag)
    fix_missing_citations(frag)
    restructure(frag)
    header = frag.new_tag('header', class_='chapter-header')
    kicker = frag.new_tag('p', class_='chapter-kicker')
    kicker.string = f'Capítulo {ch["num"]}'
    title = frag.new_tag('h1', class_='chapter-title')
    title['id'] = ch['hid']
    title.string = ch['title']
    header.append(kicker)
    header.append(title)
    frag.insert(0, header)
    ch['outline'] = outline
    fix_class_attrs(frag)
    return frag

def build_preliminares():
    frag = BeautifulSoup('', 'html.parser')
    h = frag.new_tag('h1', class_='chapter-title')
    h.string = 'Preliminares'
    frag.append(h)
    if DEDICATION:
        block = frag.new_tag('blockquote', class_='dedicatoria')
        block.string = DEDICATION
        frag.append(block)
    for hid, title in [('agradecimentos', 'Agradecimentos'), ('resumo', 'Resumo'), ('abstract', 'Abstract')]:
        src = soup.find('h1', id=hid)
        h2 = frag.new_tag('h2', class_='section-title')
        h2['id'] = hid
        h2.string = title
        frag.append(h2)
        for n in section_nodes(src):
            frag.append(n)
    fix_class_attrs(frag)
    return frag

def clean_references(frag):
    for el in frag.find_all(string=True):
        t = str(el)
        if not t.strip():
            continue
        n = re.sub(r'\s+([,.;:])', r'\1', t)
        n = re.sub(r'<\s+', '<', n)
        n = re.sub(r'\s+>', '>', n)
        n = re.sub(r'\.\s*,', '.', n)
        n = re.sub(r'\s{2,}', ' ', n)
        if n != t:
            el.replace_with(n)

def build_referencias():
    frag = BeautifulSoup('', 'html.parser')
    h = frag.new_tag('h1', class_='chapter-title')
    h.string = 'Referências'
    frag.append(h)
    p = frag.new_tag('p')
    p.string = 'Referências citadas nesta dissertação, geradas a partir do arquivo BibTeX do trabalho.'
    frag.append(p)
    refs = soup.find(id='refs')
    if refs:
        rc = copy.deepcopy(refs)
        rc['class'] = list(rc.get('class', [])) + ['referencias']
        frag.append(rc)
    clean_references(frag)
    fix_class_attrs(frag)
    return frag

def build_figuras():
    frag = BeautifulSoup('', 'html.parser')
    h = frag.new_tag('h1', class_='chapter-title')
    h.string = 'Figuras'
    frag.append(h)
    p = frag.new_tag('p')
    p.string = 'Todas as figuras da dissertação, organizadas por capítulo.'
    frag.append(p)
    for ch in CHAPTERS:
        entries = [e for e in FIGURE_ENTRIES if e['chapter']['slug'] == ch['slug']]
        if not entries:
            continue
        sec = frag.new_tag('section', class_='gallery-chapter')
        h2 = frag.new_tag('h2', class_='section-title')
        h2.string = f'Capítulo {ch["num"]} — {ch["title"]}'
        sec.append(h2)
        grid = frag.new_tag('div', class_='gallery-grid')
        for e in entries:
            item = frag.new_tag('article', class_='gallery-item')
            item['id'] = 'galeria-' + (e['label'] or '')
            media = frag.new_tag('div', class_='subfigs gallery-media')
            for m in e['media']:
                sub = frag.new_tag('div', class_='subfig')
                if m['width']:
                    sub['style'] = f'flex:0 1 {m["width"]}%;max-width:{m["width"]}%'
                img = frag.new_tag('img', class_='figimg')
                img['src'] = 'assets/figuras/' + m['src'][len('image/'):]
                img['loading'] = 'lazy'
                img['alt'] = BeautifulSoup(m['cap'], 'html.parser').get_text(' ', strip=True) if m['cap'] else ''
                sub.append(img)
                if m['cap']:
                    capspan = frag.new_tag('span', class_='subcap')
                    append_html(capspan, m['cap'])
                    sub.append(capspan)
                media.append(sub)
            item.append(media)
            capdiv = frag.new_tag('div', class_='gallery-caption')
            caption = frag.new_tag('p')
            if e['num']:
                num = frag.new_tag('span', class_='fig-num')
                num.string = f'Figura {e["num"]}.'
                caption.append(num)
                caption.append(NavigableString(' '))
            append_html(caption, e['caption'])
            capdiv.append(caption)
            link = frag.new_tag('a', href=f'capitulos/{ch["slug"]}.html#{e["label"]}')
            link.string = 'Ver no capítulo →'
            capdiv.append(link)
            item.append(capdiv)
            grid.append(item)
        sec.append(grid)
        frag.append(sec)
    fix_class_attrs(frag)
    return frag

def rewrite_links(pages):
    id_to_page = {}
    for rel, p in pages.items():
        for el in p['content'].find_all(id=True):
            id_to_page.setdefault(el['id'], rel)
    for rel, p in pages.items():
        base = posixpath.dirname(rel)
        for a in p['content'].find_all('a', href=True):
            href = a['href']
            if href.startswith('#') and len(href) > 1:
                target = href[1:]
                tpage = id_to_page.get(target)
                if tpage and tpage != rel:
                    a['href'] = posixpath.relpath(tpage, base or '.') + '#' + target

def rewrite_images(frag, prefix):
    for img in frag.find_all('img'):
        src = img.get('src', '')
        if src.startswith('image/'):
            img['src'] = prefix + 'assets/figuras/' + src[len('image/'):]

def link_from(rel, target):
    return posixpath.relpath(target, posixpath.dirname(rel) or '.')

def sidebar_html(rel, current_chapter=None):
    def L(t):
        return link_from(rel, t)
    active_prelim = ' active' if rel == 'preliminares.html' else ''
    active_fig = ' active' if rel == 'figuras.html' else ''
    active_ref = ' active' if rel == 'capitulos/referencias.html' else ''
    active_home = ' active' if rel == 'index.html' else ''
    out = [f'''<aside class="sidebar" id="sidebar">
  <div class="sidebar-inner">
    <a class="brand" href="{L('index.html')}">
      <strong>Contador de objetos em vídeos</strong>
      <span>Dissertação · Plabiany R. Acosta</span>
    </a>
    <nav class="toc" aria-label="Sumário">
      <a class="toc-chapter{active_home}" href="{L('index.html')}">Capa</a>
      <a class="toc-chapter{active_prelim}" href="{L('preliminares.html')}">Preliminares</a>
      <div class="toc-sep"></div>''']
    for ch in CHAPTERS:
        page = f'capitulos/{ch["slug"]}.html'
        active = ' active' if current_chapter == ch['slug'] else ''
        out.append(f'      <a class="toc-chapter{active}" href="{L(page)}"><span class="toc-num">{ch["num"]}.</span> {html.escape(ch["title"])}</a>')
        if current_chapter == ch['slug']:
            for level, hid, num, text in ch.get('outline', []):
                cls = 'toc-sub' if level == 'h2' else 'toc-subsub'
                numtxt = f'<span class="toc-num">{num}</span> ' if num else ''
                out.append(f'      <a class="{cls}" href="{L(page)}#{hid}">{numtxt}{html.escape(text)}</a>')
    out.append(f'''      <div class="toc-sep"></div>
      <a class="toc-chapter{active_fig}" href="{L('figuras.html')}">Figuras</a>
      <a class="toc-chapter{active_ref}" href="{L('capitulos/referencias.html')}">Referências</a>
      <a class="pdf-link" href="{L('assets/dissertacao.pdf')}">Baixar PDF</a>
    </nav>
  </div>
</aside>
<button class="menu-toggle" type="button" aria-label="Abrir sumário" aria-controls="sidebar">☰</button>
<div class="overlay" aria-hidden="true"></div>''')
    return '\n'.join(out)

def pager_html(rel):
    order = ['preliminares.html'] + [f'capitulos/{c["slug"]}.html' for c in CHAPTERS] + ['capitulos/referencias.html', 'figuras.html']
    if rel not in order:
        return ''
    i = order.index(rel)
    prev = order[i-1] if i > 0 else None
    nxt = order[i+1] if i+1 < len(order) else None
    labels = {
        'preliminares.html': 'Preliminares',
        'capitulos/referencias.html': 'Referências',
        'figuras.html': 'Figuras',
    }
    for c in CHAPTERS:
        labels[f'capitulos/{c["slug"]}.html'] = f'Capítulo {c["num"]} — {c["title"]}'
    parts = ['<nav class="pager" aria-label="Navegação entre páginas">']
    if prev:
        parts.append(f'<a class="prev" href="{link_from(rel, prev)}"><span class="label">Anterior</span>{html.escape(labels.get(prev, "Anterior"))}</a>')
    else:
        parts.append('<span></span>')
    if nxt:
        parts.append(f'<a class="next" href="{link_from(rel, nxt)}"><span class="label">Próximo</span>{html.escape(labels.get(nxt, "Próximo"))}</a>')
    else:
        parts.append('<span></span>')
    parts.append('</nav>')
    return '\n'.join(parts)

def render_page(rel, title, content_html, current_chapter=None, layout='sheet'):
    prefix = '../' if rel.startswith('capitulos/') else ''
    pager = pager_html(rel)
    body = content_html
    if layout == 'sheet':
        body = f'''<article class="sheet">
{content_html}
{pager}
<footer class="site-footer">
  <p>Plabiany Rodrigo Acosta · Dissertação de Mestrado · FACOM/UFMS · 2021</p>
  <p><a href="{link_from(rel, 'assets/dissertacao.pdf')}">Versão em PDF</a></p>
</footer>
</article>'''
    else:
        body = f'<div class="landing">{content_html}</div>'
    return f'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="Dissertação de mestrado de Plabiany Rodrigo Acosta: contador de objetos em vídeos usando redes neurais convolucionais.">
<link rel="stylesheet" href="{prefix}assets/css/site.css">
</head>
<body>
{sidebar_html(rel, current_chapter)}
<main class="page">
{body}
</main>
<script src="{prefix}assets/js/site.js"></script>
</body>
</html>
'''

def index_content():
    resumo = build_fragment(section_nodes(soup.find('h1', id='resumo')))
    abstract = build_fragment(section_nodes(soup.find('h1', id='abstract')))
    toc_items = []
    for ch in CHAPTERS:
        sub = []
        for level, hid, num, text in ch.get('outline', []):
            if level == 'h2':
                numtxt = f'<span class="toc-num">{num}</span> ' if num else ''
                sub.append(f'<li><a href="capitulos/{ch["slug"]}.html#{hid}">{numtxt}{html.escape(text)}</a></li>')
        subhtml = f'<ul>{"".join(sub)}</ul>' if sub else ''
        toc_items.append(f'<li><a href="capitulos/{ch["slug"]}.html"><span class="sum-num">{ch["num"]}.</span> {html.escape(ch["title"])}</a>{subhtml}</li>')
    return f'''<section class="hero">
  <div class="hero-content">
    <p class="kicker">Dissertação de Mestrado · FACOM/UFMS</p>
    <h1>Contador de objetos em vídeos usando redes neurais convolucionais</h1>
    <p class="hero-author">Plabiany Rodrigo Acosta</p>
    <p class="hero-meta">Orientador: Prof. Dr. Wesley Nunes Gonçalves<br>Universidade Federal de Mato Grosso do Sul · Campo Grande · 2021</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="capitulos/01-introducao.html">Ler a dissertação</a>
      <a class="btn btn-ghost" href="assets/dissertacao.pdf">Baixar PDF</a>
    </div>
  </div>
</section>
<div class="resumo-grid">
  <article class="card"><h2>Resumo</h2>{str(resumo)}</article>
  <article class="card"><h2>Abstract</h2>{str(abstract)}</article>
</div>
<section class="sumario">
  <h2>Sumário</h2>
  <ol class="sumario-list">
    <li><a href="preliminares.html">Preliminares</a></li>
    {''.join(toc_items)}
    <li><a href="capitulos/referencias.html">Referências</a></li>
    <li><a href="figuras.html">Figuras</a></li>
  </ol>
</section>
<section class="about">
  <h2>Sobre</h2>
  <div class="about-grid">
    <div><h3>Autor</h3><p>Plabiany Rodrigo Acosta</p></div>
    <div><h3>Orientação</h3><p>Prof. Dr. Wesley Nunes Gonçalves</p></div>
    <div><h3>Instituição</h3><p>Faculdade de Computação — FACOM<br>Universidade Federal de Mato Grosso do Sul</p></div>
    <div><h3>Ano</h3><p>2021</p></div>
  </div>
</section>'''

def main():
    prepare_images()
    pages = {}
    for ch in CHAPTERS:
        frag = build_chapter(ch)
        rel = f'capitulos/{ch["slug"]}.html'
        pages[rel] = dict(content=frag, title=f'Capítulo {ch["num"]} — {ch["title"]}', chapter=ch['slug'])
    pages['preliminares.html'] = dict(content=build_preliminares(), title='Preliminares', chapter=None)
    pages['capitulos/referencias.html'] = dict(content=build_referencias(), title='Referências', chapter=None)
    pages['figuras.html'] = dict(content=build_figuras(), title='Figuras', chapter=None)

    rewrite_links(pages)
    for rel, p in pages.items():
        prefix = '../' if rel.startswith('capitulos/') else ''
        rewrite_images(p['content'], prefix)
        outpath = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
        content_html = str(p['content'])
        html_doc = render_page(rel, p['title'], content_html, p['chapter'])
        open(outpath, 'w', encoding='utf-8').write(html_doc)
        print('escrito', rel, f'{len(html_doc)/1024:.1f} KB')

    index_html = render_page('index.html', 'Contador de objetos em vídeos usando redes neurais convolucionais', index_content(), None, layout='landing')
    open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(index_html)
    print('escrito index.html', f'{len(index_html)/1024:.1f} KB')

if __name__ == '__main__':
    main()
