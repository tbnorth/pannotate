import popplerqt4
import PyQt4
import sys
import urllib
import os

from collections import namedtuple

import bibtexparser

Annote = namedtuple("Annote", "page date text note")

def main():

    if not sys.argv[1].endswith('.bib'):
        annotes = get_annotes(sys.argv[1])
        for annote in annotes:
            print("p%s, %s" % (annote.page, annote.text))
        if annote.note:
            print('=>  %s' % annote.note)
        return

    bibfile, pdfdir = sys.argv[1:]

    with open(bibfile) as bibtex_file:
        bibtex_str = bibtex_file.read()

    bib_database = bibtexparser.loads(bibtex_str)
    keys = set()
    for entry in bib_database.entries:
        keys.update(entry.keys())
        if 'file' in entry:
            annotes = get_annotes(os.path.join(pdfdir, entry['file'][1:-4]))
            if annotes:
                print(u"{author}, {year}, {journal}, {ID}".format(
                    **{k:entry.get(k, '???') for k in ('author', 'year', 'journal', 'ID')}))
                print(entry['title'])
                for annote in annotes:
                    print("p%s, %s" % (annote.page, annote.text))
                    if annote.note:
                        print('=>  %s' % annote.note)

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

