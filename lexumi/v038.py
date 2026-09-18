from PySide6.QtWidgets import QMessageBox


class WindowV038Mixin:
    """v0.3.8: branded macOS installer DMG release metadata."""

    def about(self):
        QMessageBox.about(
            self,
            'About Lexumi',
            'Lexumi 0.3.8\nOffline ebook & document reader for macOS Apple Silicon.\n\n'
            'PDF · DjVu · EPUB · FB2 / FB2.ZIP · MOBI / PRC\nTXT · XPS / OXPS · CBZ / CBR · images\n\n'
            'Continuous scrolling, embedded ebook covers, two-page spreads, text search, bookmarks, print preview, and PDF export.\n'
            'OCR and DRM are not supported.\n\nPySide6 / Qt, PyMuPDF, DjVuLibre, libarchive.\nAGPL-3.0-or-later.'
        )
