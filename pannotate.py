import argparse
import json
import popplerqt4
import PyQt4
import sys
import urllib
import os

from collections import namedtuple, defaultdict

from lxml import etree as ET
from lxml.builder import E

import bibtexparser

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

    return parser

def main():

    opt = make_parser().parse_args()

    if len(opt.inputs) == 1:
        annote = defaultdict(lambda: "???")
        annote['annotations'] = get_annotes(opt.inputs[0])
        annotes = [annote]
    else:
        bibfile, pdfdir = opt.inputs
        annotes = annotes_dicts(bibfile, pdfdir)

    if opt.json:
        json.dump(annotes, sys.stdout, indent=4)
    else:
        for annote in annotes:
            print(annote_str(annote))

def annotes_dicts(bibfile, pdfdir):

    with open(bibfile) as bibtex_file:
        bibtex_str = bibtex_file.read()
    bib_database = bibtexparser.loads(bibtex_str)

    annotes_list = []

    for entry in bib_database.entries:
        if 'file' in entry:
            filepath = os.path.join(pdfdir, entry['file'][1:-4])
            sys.stderr.write("%s\n" % filepath)
            annotes = get_annotes(filepath)
            if annotes:
                info = {'file': filepath}
                annotes_list.append(info)
                for k in 'author', 'year', 'title', 'journal', 'ID':
                    info[k] = _to_utf(entry.get(k, '???'))
                info['annotations'] = [{k:_to_utf(v) for k,v in j._asdict().items()} for j in annotes]

    return annotes_list

def annote_str(annote):

    ans = [u"{author}, {year}, {journal}, {ID}\n{title}".format(**annote)]
    for annotation in annote['annotations']:
        ans.append("p%s, %s" % (annotation['page'], annotation['text']))
        if annotation['note']:
            ans.append('=>  %s' % annotation['note'])
    return '\n'.join(ans)

def get_annotes(filepath):

    document = popplerqt4.Poppler.Document.load(filepath)
    if not document:
        return

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
            if not isinstance(annotation, popplerqt4.Poppler.HighlightAnnotation):
                continue
            pagenum = page_n+1
            date = annotation.modificationDate().toString()
            note = annotation.contents()
            txt = []
            for quad in annotation.highlightQuads():
                bdy = PyQt4.QtCore.QRectF()
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

