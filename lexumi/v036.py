from __future__ import annotations

from PySide6.QtWidgets import QMessageBox


class WindowV036Mixin:
    """v0.3.6: reliable EPUB cover selection with first-page fallback."""

    def about(self):
        QMessageBox.about(
            self,
            'About Lexumi',
            'Lexumi 0.3.6\nOffline ebook & document reader for macOS Apple Silicon.\n\n'
            'PDF · DjVu · EPUB · FB2 / FB2.ZIP · MOBI / PRC\nTXT · XPS / OXPS · CBZ / CBR · images\n\n'
            'Continuous scrolling, ebook covers with first-page fallback, text search, bookmarks, print preview, and PDF export.\n'
            'OCR and DRM are not supported.\n\nPySide6 / Qt, PyMuPDF, DjVuLibre, libarchive.\nAGPL-3.0-or-later.'
        )
