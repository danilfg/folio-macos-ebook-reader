from .ui_shared import *


class WindowLibraryMixin:
    def refresh_library(self, *_):
        self.books.clear()
        current_path = self.meta['path'] if self.meta else None
        current_item = None
        for row in self.library.all(self.filter.text()):
            ext = 'FB2.ZIP' if row['path'].lower().endswith('.fb2.zip') else Path(row['path']).suffix[1:].upper()
            progress = f"  ·  {row['page'] + 1} / {row['total']}" if row['total'] else ''
            item = QListWidgetItem(f"{row['title']}\n{ext}{progress}")
            item.setData(Qt.ItemDataRole.UserRole, row['path'])
            item.setToolTip(row['path'] + '\nDouble-click to open')
            self.books.addItem(item)
            if row['path'] == current_path:
                current_item = item
        if current_item:
            self.books.setCurrentItem(current_item)

    def choose_open(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Open books', str(Path.home()), BOOK_FILTER)
        self.add_paths(paths)

    def add_paths(self, paths):
        valid = [str(Path(p).resolve()) for p in paths if Path(p).is_file() and supported(p)]
        for path in valid:
            self.library.add(path)
        self.refresh_library()
        if valid:
            self.open_path(valid[0])
        elif paths:
            self.error('None of the selected files use a supported book format.')

    def update_sidebar_preview(self):
        if not getattr(self, 'library_preview_card', None):
            return
        if not self.meta:
            self.library_preview_title.setText('')
            self.library_preview_meta.setText('')
            self.library_preview_image.setText('Open a book to see a preview')
            self.library_preview_image.setPixmap(QPixmap())
            return
        suffix = 'FB2.ZIP' if self.meta['path'].lower().endswith('.fb2.zip') else Path(self.meta['path']).suffix[1:].upper()
        self.library_preview_title.setText(self.meta['title'])
        self.library_preview_meta.setText(f"{suffix} · {self.meta['count']} pages")
        self.library_preview_image.setPixmap(QPixmap())
        self.library_preview_image.setText('Loading preview…')
        generation = self.generation

        def done(response, generation=generation):
            if generation != self.generation:
                return
            if 'error' in response:
                self.library_preview_image.setText('Preview unavailable')
                return
            image = QImage.fromData(base64.b64decode(response['result']['image']))
            pix = QPixmap.fromImage(image)
            pix = pix.scaled(220, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.library_preview_image.setText('')
            self.library_preview_image.setPixmap(pix)

        self.engine.request('render', done, page=0, width=260)

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Add a folder with books')
        if not folder:
            return
        progress = QProgressDialog('Scanning the folder for books…', 'Stop', 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        count = 0
        for root, dirs, files in os.walk(folder, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            QApplication.processEvents()
            if progress.wasCanceled():
                break
            for name in files:
                path = Path(root) / name
                if supported(path):
                    self.library.add(path)
                    count += 1
        progress.close()
        self.refresh_library()
        self.statusBar().showMessage(f'Added {count} book(s). Double-click a book to open it.')

    def clear_pages(self):
        while self.pages_layout.count():
            item = self.pages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.page_labels = []
        self.page_label = None
        self.pending_pages.clear()
        self.rendered_signature.clear()
        self.render_busy = False

    def build_page_placeholders(self):
        self.clear_pages()
        for index in range(self.meta['count']):
            label = PageLabel(index)
            self.page_labels.append(label)
            self.pages_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.refresh_page_geometry()

    def open_path(self, path, password=''):
        if self.opening or self.working:
            self.statusBar().showMessage('Wait for the current operation to finish.')
            return
        self.opening = True
        self.generation += 1
        generation = self.generation
        self.statusBar().showMessage('Opening ' + Path(path).name + '…')

        def done(response):
            self.opening = False
            if generation != self.generation:
                return
            if 'error' in response:
                if response.get('kind') == 'PermissionError':
                    password_value, ok = QInputDialog.getText(self, 'Protected PDF', 'Password:', QLineEdit.EchoMode.Password)
                    if ok:
                        self.open_path(path, password_value)
                else:
                    self.error(response['error'])
                return

            self.meta = response['result']
            self.current_password = password
            self.last_query = ''
            self.search.clear()
            self.library.add(self.meta['path'], self.meta['title'], self.meta['count'])
            row = self.library.get(self.meta['path'])
            self.page = min(row['page'], self.meta['count'] - 1)
            self.page_spin.blockSignals(True)
            self.page_spin.setRange(1, self.meta['count'])
            self.page_spin.setValue(self.page + 1)
            self.page_spin.blockSignals(False)
            self.page_total.setText(f" / {self.meta['count']}  ")
            self.setWindowTitle(self.meta['title'] + ' — Folio')

            self.toc.clear()
            parents = {}
            for level, title, pagenum in self.meta['toc']:
                if pagenum < 1:
                    continue
                parent = parents.get(level - 1, self.toc)
                item = QTreeWidgetItem(parent, [title])
                item.setData(0, Qt.ItemDataRole.UserRole, pagenum - 1)
                parents[level] = item
                parents = {k: v for k, v in parents.items() if k <= level}
            self.toc.expandToDepth(0)
            if not self.meta['toc']:
                item = QTreeWidgetItem(self.toc, ['No table of contents is available in this file'])
                item.setFlags(Qt.ItemFlag.NoItemFlags)

            self.refresh_marks()
            self.update_sidebar_preview()
            self.build_page_placeholders()
            self.stack.setCurrentIndex(1)
            self.zoom_footer.show()
            QTimer.singleShot(0, lambda: self.go(self.page, force=True))

        self.engine.request('open', done, path=path, password=password)
