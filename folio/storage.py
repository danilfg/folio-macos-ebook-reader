"""SQLite library: references only; never moves or deletes book files."""
import os
from pathlib import Path
import sqlite3
import sys
import time


def data_dir():
    override = os.environ.get('FOLIO_DATA_DIR')
    path = Path(override) if override else (
        Path.home() / 'Library/Application Support/Folio' if sys.platform == 'darwin'
        else Path.home() / '.local/share/Folio')
    path.mkdir(parents=True, exist_ok=True)
    return path


class Library:
    def __init__(self, path=None):
        self.db = sqlite3.connect(path or data_dir() / 'library.sqlite3')
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS books (
            path TEXT PRIMARY KEY, title TEXT NOT NULL, page INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0, opened REAL NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS bookmarks (
            path TEXT NOT NULL, page INTEGER NOT NULL, label TEXT NOT NULL,
            PRIMARY KEY(path,page));
        ''')

    def add(self, path, title=None, total=0):
        path = str(Path(path).resolve())
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO books(path,title,total) VALUES (?,?,?)',
                            (path, title or Path(path).stem, total))
            if title:
                self.db.execute('UPDATE books SET title=?,total=? WHERE path=?', (title,total,path))

    def opened(self, path, page):
        with self.db:
            self.db.execute('UPDATE books SET page=?,opened=? WHERE path=?', (page,time.time(),path))

    def get(self, path):
        return self.db.execute('SELECT * FROM books WHERE path=?', (path,)).fetchone()

    def all(self, query=''):
        rows = self.db.execute('SELECT * FROM books ORDER BY opened DESC,title COLLATE NOCASE').fetchall()
        return [r for r in rows if query.casefold() in r['title'].casefold() or query.casefold() in Path(r['path']).name.casefold()]

    def remove(self, path):
        with self.db:
            self.db.execute('DELETE FROM books WHERE path=?', (path,))
            self.db.execute('DELETE FROM bookmarks WHERE path=?', (path,))

    def bookmarks(self, path):
        return self.db.execute('SELECT * FROM bookmarks WHERE path=? ORDER BY page', (path,)).fetchall()

    def toggle_bookmark(self, path, page):
        with self.db:
            exists = self.db.execute('SELECT 1 FROM bookmarks WHERE path=? AND page=?', (path,page)).fetchone()
            if exists:
                self.db.execute('DELETE FROM bookmarks WHERE path=? AND page=?', (path,page))
            else:
                self.db.execute('INSERT INTO bookmarks VALUES (?,?,?)', (path,page,f'Page {page+1}'))

    def close(self):
        self.db.close()
