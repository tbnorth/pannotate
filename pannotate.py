"""
--filter keyword NNNM
i.e. it's `keyword`, not `keywords` etc.

"""

import argparse
import json
import os
import re
import sys
import time
import urllib

from collections import namedtuple, defaultdict

import bibtexparser
from bibtexparser.bparser import BibTexParser
import popplerqt5
import PyQt5

from lxml import etree as ET
from lxml.builder import E

try:
    unicode
except:
    unicode = str

Annote = namedtuple("Annote", "page date text note")

def _to_utf(s):
    if isinstance(s, (int, float)):
        return str(s)
    try:
        return unicode(s.toUtf8(), 'utf-8')  # .toUtf8 returns QByteArray
    except AttributeError:
        return s  # was unicode already?

def make_parser():

    parser = argparse.ArgumentParser(
        description="""Read annotations from PDFs""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('inputs', type=str, nargs='+',
        help="<pdf-file> or <bib-file> <pdf-folder>"
    )

    parser.add_argument('--json', action='store_true',
        help='Return JSON output')
    parser.add_argument('--html', action='store_true',
        help='Return HTML output')
    parser.add_argument('--cite-as',
        help='E.g. "--cite-as=\\\\no-site{%%s}" to get a list of '
        'citation commands (useful with --filter).')
    parser.add_argument('--filter', action='append', nargs=2,
        metavar=('KEY', 'PATTERN'), default=[],
        help='field KEY must match regex PATTERN. Repeatable.')

    return parser

def main():

    opt = make_parser().parse_args()

    if len(opt.inputs) == 1:
        annote = {}
        annote['annotations'] = get_annotes(opt.inputs[0])
        annotes = [annote]
    else:
        bibfile, pdfdir = opt.inputs
        annotes = annotes_dicts(bibfile, pdfdir, opt.filter,
            include_all=bool(opt.cite_as))

    if opt.json:
        json.dump(annotes, sys.stdout, indent=4)
    elif opt.html:
        html_dump(annotes, sys.stdout)
    elif opt.cite_as:
        print('\n'.join([opt.cite_as % i['ID'] for i in annotes]))
    else:
        for annote in annotes:
            print(annote_str(annote))

def annotes_dicts(bibfile, pdfdir, filters, include_all=False):

    with open(bibfile, encoding="utf-8") as bibtex_file:
        bibtex_str = bibtex_file.read()
    parser = BibTexParser()
    parser.ignore_nonstandard_types = False
    bib_database = bibtexparser.loads(bibtex_str, parser)

    annotes_list = []

    for entry in bib_database.entries:
        match = True
        for key, pattern in filters:
            if key not in entry or not re.search(pattern, entry[key]):
                match = False
                break
        filepath = ''
        if match and (entry.get('file') or entry.get('review') or include_all):
            if entry.get('file'):
                filepath = os.path.join(pdfdir, entry['file'][1:-4])
                sys.stderr.write("%s\n" % filepath)
                annotes = get_annotes(filepath)
            else:
                annotes = []
            if annotes or entry.get('review') is not None or include_all:
                info = {'file': filepath}
                annotes_list.append(info)
                for k in 'author', 'year', 'title', 'journal', 'review', 'ID', 'doi':
                    info[k] = _to_utf(entry.get(k, None))
                info['annotations'] = [{k:_to_utf(v) for k,v in j._asdict().items()} for j in annotes]

    annotes_list.sort(key=lambda x: x['ID'])
    return annotes_list

def html_dump(annotes, out):

    timestamp = time.asctime()

    body = E.body(E.h1("Notes %s" % timestamp))
    html = E.html(E.head(
    E.title("Notes %s" % timestamp),
    E.style("""
    :root {
      --c_bg: #fff;
      --c_fg: #000;
      --c_bibkey: green;
      --c_note: #800;

      --c_bg: #002b36;
      --c_fg: #657b83;
      --c_bibkey: #859900;
      --c_note: #b58900;
      --c_doi: #586e75;
    }
    * { font-family: sans-serif; }
    body { background: var(--c_bg); color: var(--c_fg); }
    a { text-decoration: none; }
    a:hover { text-decoration: underline; text-decoration-color: var(--c_fg); }
    h2 { margin-bottom: 0; }
    .title a { color: var(--c_fg); }
    .doi { font-size: 50%; }
    .doi a { color: var(--c_doi); }
    .bibkey { font-size: 75%; color: var(--c_bibkey); }
    .author { font-weight: bold; }
    .journal { font-style: italic; }
    .note { color: var(--c_note); }
    .page { display: inline-block; width: 2em; font-family: "Courier New", monospace; 
            text-align: center; vertical-align: top; }
    .text a { color: var(--c_fg); }
    .text { display: inline-block; width: 90%; }
    .filelink { font-family: monospace; font-size: 60%; padding-right: 1ex }
    .filepath { width: 0 }
    """),
    E.script("""
    function copyPath(file) {
      var copyText = document.getElementById('copy-text');
      copyText.value = file;
      copyText.select();
      document.execCommand("copy");
      // alert("Copied the text: " + copyText.value);
    }
    """)
    ), body)

    for annote in annotes:
        annote = defaultdict(lambda: '?', annote)
        h2 = E.h2(
            E.a(E.span(annote['ID'], id=annote['ID'], class_='bibkey'), href="#"+annote['ID']), ' ',
            E.span('F', class_='filelink', onclick='copyPath("%s")'%annote['file'], title='Copy path to file'),
            E.span(E.a(annote['title'] or '???', href=annote['file'], target=annote['file']), class_='title'), ' ',
        )
        if annote.get('doi'):
            h2.append(E.span(E.a(annote['doi'], href='https://dx.doi.org/'+annote['doi'], target=annote['file']), class_='doi'))
        body.append(h2)
        body.append(E.div(annote['author'] or '???', class_='author'))
        if annote.get('journal'):
            body.append(E.div(annote['journal'], class_='journal'))
        if annote.get('review'):
            body.append(E.div(annote['review'], class_='note'))
        for annotation in annote['annotations']:
            body.append(E.div(
                E.span(E.span(str(annotation['page'])), class_='page'), ' ',
                E.span(E.a(annotation['text'],
                    href="%s#page=%s" % (annote['file'], annotation['page']), target='_blank'), class_='text'),
                class_='annotation',
            ))
            if annotation.get('note'):
                body.append(E.div(annotation['note'], class_='note'))

    body.append(E.div(E.input(id='copy-text', value="(pdf file copy / paste)")))

    html_str = ET.tostring(html)
    html_str = html_str.decode('utf-8').replace('class_', 'class')
    html_str = html_str.replace('{{', '').replace('}}', '')
    out.write(html_str)

def annote_str(annote):
    annote = defaultdict(lambda: "?", annote)
    ans = [u"{0[author]}, {0[year]}, {0[journal]}, {0[ID]}\n{0[title]}".format(annote)]
    for annotation in annote['annotations']:
        ans.append("p%s, %s" % (annotation.page, annotation.text))
        if annotation.note:
            ans.append('=>  %s' % annotation.note)
    return '\n'.join(ans)

def get_annotes(filepath):

    document = popplerqt5.Poppler.Document.load(filepath)
    if not document:
        return []

    # print dir(document)
    # print document.date()
    # print [unicode(i) for i in document.infoKeys()]

    annotes = []

    for page_n in range(document.numPages()):
        page = document.page(page_n)
        pwidth = page.pageSize().width()
        pheight = page.pageSize().height()
        # pwidth = pheight = 1
        for annotation in page.annotations():
            if not isinstance(annotation, popplerqt5.Poppler.HighlightAnnotation):
                continue
            pagenum = page_n+1
            date = annotation.modificationDate().toString()
            note = annotation.contents()
            txt = []
            for quad in annotation.highlightQuads():
                bdy = PyQt5.QtCore.QRectF()
                bdy.setCoords(
                    quad.points[0].x() * pwidth,
                    quad.points[0].y() * pheight,
                    quad.points[2].x() * pwidth,
                    quad.points[2].y() * pheight
                )
                txt.append(unicode(page.text(bdy)))
            txt = ' '.join(txt)
            annotes.append(Annote(page=pagenum, text=txt, note=note, date=date))

    return annotes

if __name__ == "__main__":
    main()

