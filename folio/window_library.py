from .ui_shared import *


class WindowLibraryMixin:
    def update_book_row_styles(self):
        current = self.books.currentItem()
        for i in range(self.books.count()):
            item = self.books.item(i)
            widget = self.books.itemWidget(item)
            if isinstance(widget, BookListItemWidget):
                widget.set_selected(item is current, self.dark)

    def refresh_library(self, *_):
        self.books.clear()
        current_path = self.meta['path'] if self.meta else None
        current_item = None
        for row in self.library.all(self.filter.text()):
            ext = 'FB2.ZIP' if row['path'].lower().endswith('.fb2.zip') else Path(row['path']).suffix[1:].upper()
            progress = f'Page {row["page"] + 1} / {row["total"]}' if row['total'] else 'Not opened yet'
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, row['path'])
            item.setToolTip(row['path'] + '\nClick to open')
            item.setSizeHint(QSize(0, 96))
            self.books.addItem(item)
            widget = BookListItemWidget(row['title'], f'{ext}  ·  {progress}', ext, self.dark)
            preview = self.book_previews.get(row['path'])
            widget.set_preview(preview, ext)
            widget.removeRequested.connect(lambda p=row['path']: self.remove_book(p))
            self.books.setItemWidget(item, widget)
            if row['path'] == current_path:
                current_item = item
        if current_item:
            self.books.setCurrentItem(current_item)
        self.update_book_row_styles()

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
        if not self.meta:
            return
        path = self.meta['path']
        generation = self.generation

        def done(response, generation=generation, path=path):
            if generation != self.generation:
                return
            if 'error' in response:
                return
            image = QImage.fromData(base64.b64decode(response['result']['image']))
            pix = QPixmap.fromImage(image)
            self.book_previews[path] = pix
            self.refresh_library()

        self.engine.request('render', done, page=0, width=72)

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
        self.statusBar().showMessage(f'Added {count} book(s). Click a book to open it.')

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
            self.build_page_placeholders()
            self.stack.setCurrentIndex(1)
            self.zoom_footer.show()
            self.refresh_library()
            self.update_sidebar_preview()
            QTimer.singleShot(0, lambda: self.go(self.page, force=True))

        self.engine.request('open', done, path=path, password=password)
