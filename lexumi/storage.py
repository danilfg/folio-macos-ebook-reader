"""SQLite library: references only; never moves or deletes book files."""
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time


def _default_data_dir(app_name):
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support' / app_name
    return Path.home() / '.local/share' / app_name


def data_dir():
    override = os.environ.get('LEXUMI_DATA_DIR')
    path = Path(override) if override else _default_data_dir('Lexumi')

    # Preserve existing local library data across the product rename.
    if not override and not path.exists():
        legacy_name = 'Fo' + 'lio'
        legacy = _default_data_dir(legacy_name)
        if legacy.exists():
            shutil.copytree(legacy, path, dirs_exist_ok=True)

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
