"""Generate original, redistributable fixtures (CC0)."""
from pathlib import Path
import subprocess
import tempfile
import zipfile
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT/'samples'


def make():
    SAMPLES.mkdir(exist_ok=True)
    html = '''<html><head><meta charset="utf-8"><style>
    body {font-family:serif; color:#24332d; padding:36px; font-size:15px;}
    h1 {font-size:36px; color:#2d694f;} h2 {font-size:26px;}
    .muted {color:#7b837e;} .break {page-break-before:always;}
    </style></head><body>
    <p class="muted">LEXUMI / ПЕРВАЯ КНИГА</p>
    <h1>Всё начинается<br/>с одной страницы.</h1>
    <p>Эта небольшая книга поможет проверить Lexumi: открытие,
    поиск по тексту, закладки и печать.</p>
    <h2>Книги — рядом</h2>
    <p>Добавьте свои PDF, DjVu, EPUB или FB2. Lexumi запоминает,
    где вы остановились, и хранит закладки локально.</p>
    <p>Исходные файлы остаются в выбранной вами папке.</p>
    <p class="muted">Перейдите на вторую страницу клавишей →.</p>
    <h2 class="break">Маленькая проверка</h2>
    <p>Контрольная фраза: зелёная закладка.</p>
    <p>Нажмите ⌘F и найдите слово «закладка». Затем добавьте
    эту страницу в закладки и снова откройте книгу.</p>
    <p>Для проверки печати выберите только эту страницу.</p>
    <p class="muted">Демонстрационный текст создан для Lexumi. CC0.</p>
    </body></html>'''
    doc = fitz.open(stream=html.encode(),filetype='html')
    doc.layout(width=595,height=842,fontsize=13)
    pdf = fitz.open(stream=doc.convert_to_pdf(),filetype='pdf')
    pdf.set_metadata({'title':'Добро пожаловать в Lexumi','author':'Lexumi'})
    pdf.set_toc([[1,'Добро пожаловать',1],[1,'Проверка чтения',2]])
    pdf.save(SAMPLES/'Welcome.pdf')
    for index,p in enumerate(pdf):
        p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(SAMPLES/f'page-{index+1}.png')
    with zipfile.ZipFile(SAMPLES/'Welcome.cbz','w') as z:
        for p in sorted(SAMPLES.glob('page-*.png')):
            z.write(p,p.name)
    pdf.close(); doc.close()
    fb2 = '''<?xml version="1.0" encoding="utf-8"?>
    <FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
    <description><title-info><genre>reference</genre><author><first-name>Lexumi</first-name><last-name>Demo</last-name></author>
    <book-title>Проверка FB2</book-title><lang>ru</lang></title-info></description>
    <body><title><p>Книга в Lexumi</p></title><section><title><p>Первая глава</p></title>
    <p>Привет, читатель. Зелёная закладка помогает вернуться к книге.</p>
    <p>Это демонстрационная книга FB2 для проверки русского текста.</p></section></body></FictionBook>'''
    (SAMPLES/'Welcome.fb2').write_text(fb2,encoding='utf-8')
    with zipfile.ZipFile(SAMPLES/'Welcome.fb2.zip','w') as z:
        z.writestr('Welcome.fb2',fb2)
    (SAMPLES/'Welcome.txt').write_text('Lexumi\n\nПривет, читатель!\nЗелёная закладка.\nЭто TXT в UTF-8.\n',encoding='utf-8')
    with zipfile.ZipFile(SAMPLES/'Welcome.epub','w') as z:
        z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
        z.writestr('META-INF/container.xml','''<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>''')
        z.writestr('OEBPS/book.opf','''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Книга EPUB в Lexumi</dc:title><dc:language>ru</dc:language><dc:identifier id="id">lexumi-demo</dc:identifier></metadata><manifest><item id="c1" href="chapter.xhtml" media-type="application/xhtml+xml"/><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest><spine toc="ncx"><itemref idref="c1"/></spine></package>''')
        z.writestr('OEBPS/chapter.xhtml','''<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Lexumi</title></head><body><h1>Lexumi — проверка EPUB</h1><p>Привет, читатель. Зелёная закладка.</p><p>Книги разных форматов в одном приложении.</p></body></html>''')
        z.writestr('OEBPS/toc.ncx','''<?xml version="1.0" encoding="utf-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="lexumi-demo"/></head><docTitle><text>Lexumi</text></docTitle><navMap><navPoint id="c1" playOrder="1"><navLabel><text>Первая глава</text></navLabel><content src="chapter.xhtml"/></navPoint></navMap></ncx>''')
    print('Samples:',SAMPLES)


if __name__ == '__main__':
    make()
