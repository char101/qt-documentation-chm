import sys

import re
import shutil
import subprocess
from os.path import abspath

import chm
from lxml import etree, html
from path import path as Path

SOURCE = Path('complete\\source').abspath()
OUTPUT = Path('complete\\output').abspath()
CHM = chm.DocChm('Qt-5.7.0', default_topic='qtdoc/index.html', title='Qt 5.7.0')

def can_skip_section(section):
    for sec in section.findall('section'):
        if sec.get('title') not in (
            'List of all members',
            'Obsolete members'
        ):
            return False
    return True

def parse_file_toc(file, parent):
    if not file.exists():
        return
    with open(file, encoding='utf-8') as f:
        tree = html.parse(f)

    for toc in tree.xpath('//div[@class="toc"]'):
        prev_level = None
        prev_item = None
        stack = [parent]
        for li in toc.findall('ul/li'):
            level = int(li.get('class')[-1])
            # some HTML have 2 as the first level
            if prev_level is None:
                prev_level = level
            a = li.find('a')
            title = html.tostring(a, encoding='unicode', method='text').strip()
            href = a.get('href')
            if href[0] == '#':
                href = file.basename() + href
            href = OUTPUT.relpathto(file.dirname() / href)
            if level > prev_level:
                stack.append(prev_item)
            elif level < prev_level:
                for i in range(level, prev_level):
                    stack.pop()
            item = stack[-1].append(title, href)

            prev_level = level
            prev_item = item

    if file.basename() == 'qtexamplesandtutorials.html':
        for multicolumn in tree.xpath('//div[@class="multi-column"]'):
            for doccolumn in multicolumn.findall('div[@class="doc-column"]'):
                title = html.tostring(doccolumn.find('p'), encoding='unicode', method='text').strip()
                doccolumn_toc = parent.append(title, OUTPUT.relpathto(file))
                for li in doccolumn.findall('ul/li'):
                    a = li.find('a')
                    href = a.get('href')
                    if href.startswith('http://doc.qt.io'):
                        continue
                    title = html.tostring(a, encoding='unicode', method='text').strip()
                    doccolumn_toc.append(title, OUTPUT.relpathto(file.dirname() / href))

def process_section(elem, parent, module):
    for section in elem.findall('section'):
        title = section.get('title')
        href = module.basename() / section.get('ref')
        child_toc = parent.append(title, href)
        if not can_skip_section(section):
            process_section(section, child_toc, module)
        elif '#' not in href:
            parse_file_toc(OUTPUT / href, child_toc)

def process_qhp(file, module):
    with open(file, encoding='utf-8'):
        tree = etree.parse(file)
    toc = tree.xpath('//toc')
    if len(toc):
        process_section(toc[0], CHM.toc, module)
    keywords = tree.xpath('//keywords')
    index = CHM.index
    if len(keywords):
        for keyword in keywords[0].findall('keyword'):
            name = keyword.get('name')

            # too many topics
            if name.startswith('operator') and ' ' not in name:
                continue

            href = module.basename() / keyword.get('ref')
            title = keyword.get('ref')
            index.append(name, href, title)

def process_resource(dir, output_dir):
    if dir.basename() == 'style':
        return
    target = output_dir / dir.basename()
    if not target.exists():
        print('Copying', dir)
        shutil.copytree(dir, target)
    for file in target.files():
        CHM.append(OUTPUT.relpathto(file))

style_re = re.compile(r'<link.*?</script>', re.S)

def process_html(file, output_dir):
    target = output_dir / file.basename()
    if not target.exists():
        print('Processing', file)
        with open(file, encoding='utf-8') as r, open(target, 'w', encoding='utf-8') as w:
            w.write(style_re.sub('<link rel="stylesheet" type="text/css" href="../style.css" />', r.read(), 1))
    CHM.append(OUTPUT.relpathto(target))

def process_module(module):
    print(module)
    output_dir = OUTPUT / module.basename()
    output_dir.mkdir_p()

    qhp = None
    for file in module.files():
        if file.ext == '.html':
            process_html(file, output_dir)
        elif file.ext == '.qhp':
            qhp = file

    if qhp:
        process_qhp(qhp, module)

    for dir in module.dirs():
        process_resource(dir, output_dir)

def main():
    # put qtdoc first
    process_module(SOURCE / 'qtdoc')

    for module in SOURCE.dirs():
        if module.basename() != 'qtdoc':
            process_module(module)

if __name__ == '__main__':
    OUTPUT.mkdir_p()
    main()
    ostyle = OUTPUT / 'style.css'
    if not ostyle.exists():
        subprocess.call(['cmd.exe', 'mklink', ostyle, abspath('style.css')])
    CHM.append('style.css')
    with OUTPUT:
        CHM.save()
