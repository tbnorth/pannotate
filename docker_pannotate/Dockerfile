# Docker environment for running pannotate.py which
# needs popplerqt5 etc.

FROM ubuntu:18.04

RUN apt-get update

RUN apt-get install -y python3-bibtexparser

RUN apt-get install -y wget

# for some weird reason it failed (twice) to fetch this file, so
RUN wget http://archive.ubuntu.com/ubuntu/pool/main/q/qtsvg-opensource-src/libqt5svg5_5.9.5-0ubuntu1_amd64.deb
# wget it then install its depends, then install it...
RUN apt-get install -y libqt5core5a libqt5gui5 libqt5widgets5 \
  qtbase-abi-5-9-5

RUN dpkg --install libqt5svg5_5.9.5-0ubuntu1_amd64.deb

RUN apt-get install -y python3-poppler-qt5

RUN apt-get install -y python3-lxml

# docker run --rm -it -v 'C:\Users\tbrown02\OneDrive Path\repo\tnbbib\:/bib' panno
# cd bib
# python3 pannotate.py --filter keyword NNNM --html --cite-as 1 tnb.bib pdfs/ >d.html
