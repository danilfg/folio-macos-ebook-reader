from .ui_shared import *


class WindowUiMixin:
    def action(self, name, slot, shortcut=None, icon=None, tooltip=None):
        a = QAction(line_icon(icon) if icon else QIcon(), name, self)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(shortcut)
        a.setToolTip(tooltip or name)
        self.addAction(a)
        return a

    def add_toolbar_action(self, bar, name, slot, shortcut=None, icon=None, tooltip=None):
        act = self.action(name, slot, shortcut, icon, tooltip)
        bar.addAction(act)
        return act

    def build_ui(self):
        bar = self.addToolBar('Reader')
        bar.setMovable(False)
        bar.setObjectName('MainToolbar')
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        bar.setIconSize(QPixmap(22, 22).size())

        file_menu = self.menuBar().addMenu('File')
        open_action = self.action('Open…', self.choose_open, QKeySequence.StandardKey.Open, 'open', 'Open book…')
        file_menu.addAction(open_action)
        bar.addAction(open_action)
        folder_action = self.action('Add folder…', self.import_folder, 'Ctrl+Shift+O')
        file_menu.addAction(folder_action)

        export_menu = file_menu.addMenu('Export as…')
        export_pdf_action = self.action('PDF document…', self.export_pdf, 'Ctrl+Shift+S')
        export_menu.addAction(export_pdf_action)

        print_action = self.action('Print…', self.print_book, QKeySequence.StandardKey.Print, 'print', 'Print with preview…')
        file_menu.addAction(print_action)
        bar.addAction(print_action)
        file_menu.addSeparator()
        file_menu.addAction(self.action('Close Window', self.close, QKeySequence.StandardKey.Close))

        bar.addSeparator()
        self.prev_action = self.add_toolbar_action(bar, 'Previous page', lambda: self.go(self.page - 1), 'Left', 'prev', 'Previous page')
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setFixedWidth(66)
        self.page_spin.setKeyboardTracking(False)
        self.page_spin.valueChanged.connect(lambda x: self.go(x - 1))
        self.page_spin.setToolTip('Current page')
        bar.addWidget(self.page_spin)
        self.page_total = QLabel(' / —  ')
        bar.addWidget(self.page_total)
        self.next_action = self.add_toolbar_action(bar, 'Next page', lambda: self.go(self.page + 1), 'Right', 'next', 'Next page')

        bar.addSeparator()
        self.zoom = QComboBox()
        self.zoom.addItems(['Fit Width', 'Fit Page', '50%', '67%', '75%', '90%', '100%', '110%', '125%', '150%', '175%', '200%', '250%', '300%'])
        self.zoom.setCurrentText('Fit Width')
        self.zoom.setToolTip('Zoom')
        self.zoom.currentIndexChanged.connect(self.refresh_page_geometry)
        bar.addWidget(self.zoom)

        self.add_toolbar_action(bar, 'Bookmark', self.bookmark, 'Ctrl+D', 'bookmark', 'Add or remove bookmark')
        bar.addSeparator()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bar.addWidget(spacer)

        self.export_button = QToolButton()
        self.export_button.setIcon(line_icon('export'))
        self.export_button.setToolTip('Export as…')
        self.export_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.export_button.setAutoRaise(False)
        export_popup = QMenu(self.export_button)
        export_popup.addAction(export_pdf_action)
        self.export_button.setMenu(export_popup)
        bar.addWidget(self.export_button)

        self.add_toolbar_action(bar, 'Toggle theme', self.toggle_theme, 'Ctrl+Shift+L', 'theme', 'Toggle light / dark theme')

        view_menu = self.menuBar().addMenu('View')
        view_menu.addAction(self.action('Sidebar', lambda: self.sidebar.setVisible(not self.sidebar.isVisible()), 'Ctrl+B'))
        view_menu.addAction(self.action('Full Screen', self.fullscreen, 'Ctrl+Shift+F'))
        view_menu.addAction(self.action('Page Text', self.show_text, 'Ctrl+Shift+C'))
        view_menu.addSeparator()
        view_menu.addAction(self.action('Zoom In', lambda: self.zoom_step(1), 'Ctrl++'))
        view_menu.addAction(self.action('Zoom Out', lambda: self.zoom_step(-1), 'Ctrl+-'))
        view_menu.addAction(self.action('Actual Size', lambda: self.set_zoom('100%'), 'Ctrl+0'))
        view_menu.addAction(self.action('Fit Width', lambda: self.set_zoom('Fit Width')))
        view_menu.addAction(self.action('Fit Page', lambda: self.set_zoom('Fit Page')))

        help_menu = self.menuBar().addMenu('Help')
        help_menu.addAction(self.action('About Folio', self.about))

        self.splitter = QSplitter()
        self.sidebar = QWidget()
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(18, 18, 12, 14)
        brand = QLabel('FOLIO')
        brand.setObjectName('brand')
        side.addWidget(brand)
        subtitle = QLabel('Your library. On your Mac.')
        subtitle.setObjectName('muted')
        side.addWidget(subtitle)
        side.addSpacing(10)

        self.tabs = QTabWidget()
        lib = QWidget()
        lib_layout = QVBoxLayout(lib)
        lib_layout.setContentsMargins(0, 10, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText('Search your library')
        self.filter.textChanged.connect(self.refresh_library)
        lib_layout.addWidget(self.filter)
        self.books = QListWidget()
        self.books.setWordWrap(True)
        self.books.itemDoubleClicked.connect(lambda item: self.open_path(item.data(Qt.ItemDataRole.UserRole)))
        self.books.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.books.customContextMenuRequested.connect(self.book_menu)
        lib_layout.addWidget(self.books)
        add = QPushButton(line_icon('open'), ' Add books')
        add.setToolTip('Add one or more books to the library')
        add.clicked.connect(self.choose_open)
        lib_layout.addWidget(add)
        self.tabs.addTab(lib, 'Books')

        self.toc = QTreeWidget()
        self.toc.setHeaderHidden(True)
        self.toc.itemClicked.connect(lambda item, col: self.go(item.data(0, Qt.ItemDataRole.UserRole)))
        self.tabs.addTab(self.toc, 'Contents')
        self.marks = QListWidget()
        self.marks.itemClicked.connect(lambda item: self.go(item.data(Qt.ItemDataRole.UserRole)))
        self.tabs.addTab(self.marks, 'Bookmarks')
        side.addWidget(self.tabs)
        self.splitter.addWidget(self.sidebar)

        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.search_bar = QWidget()
        search_layout = QHBoxLayout(self.search_bar)
        search_layout.setContentsMargins(12, 8, 12, 8)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Find text in this book · Enter finds the next matching page')
        self.search.returnPressed.connect(self.find)
        search_layout.addWidget(self.search)
        find_button = QToolButton()
        find_button.setIcon(line_icon('search'))
        find_button.setToolTip('Find next')
        find_button.clicked.connect(self.find)
        search_layout.addWidget(find_button)
        hide_button = QToolButton()
        hide_button.setIcon(line_icon('close'))
        hide_button.setToolTip('Close search')
        hide_button.clicked.connect(self.hide_search)
        search_layout.addWidget(hide_button)
        self.search_bar.hide()
        layout.addWidget(self.search_bar)
        self.action('Find in Book', self.focus_search, QKeySequence.StandardKey.Find)

        self.stack = QStackedWidget()
        welcome = QWidget()
        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge = QLabel('ONE LIBRARY · MANY FORMATS')
        badge.setObjectName('eyebrow')
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(badge)
        headline = QLabel('Just open a book.')
        headline.setObjectName('headline')
        headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(headline)
        description = QLabel('PDF, DjVu, EPUB, FB2, MOBI, XPS, CBZ and images.\nRead locally with continuous scrolling.')
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setObjectName('description')
        welcome_layout.addWidget(description)
        welcome_layout.addSpacing(22)
        open_button = QPushButton(line_icon('open'), ' Open book')
        open_button.setObjectName('primary')
        open_button.setToolTip('Open a local book or document')
        open_button.clicked.connect(self.choose_open)
        welcome_layout.addWidget(open_button, alignment=Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addSpacing(16)
        foot = QLabel('Reading position is saved automatically · Files stay on your Mac')
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        foot.setObjectName('muted')
        welcome_layout.addWidget(foot)
        self.stack.addWidget(welcome)

        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName('pageArea')
        self.pages_container = QWidget()
        self.pages_container.setObjectName('pagesContainer')
        self.pages_layout = QVBoxLayout(self.pages_container)
        self.pages_layout.setContentsMargins(24, 24, 24, 24)
        self.pages_layout.setSpacing(18)
        self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.pages_container)
        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.stack.addWidget(self.scroll)
        layout.addWidget(self.stack, 1)

        self.zoom_footer = QWidget()
        self.zoom_footer.setObjectName('zoomFooter')
        zlayout = QHBoxLayout(self.zoom_footer)
        zlayout.setContentsMargins(10, 5, 12, 5)
        zlayout.addStretch(1)
        zoom_out = QToolButton()
        zoom_out.setIcon(line_icon('zoom_out'))
        zoom_out.setToolTip('Zoom out')
        zoom_out.clicked.connect(lambda: self.zoom_step(-1))
        zlayout.addWidget(zoom_out)
        self.zoom_footer_label = QLabel('Fit Width')
        self.zoom_footer_label.setMinimumWidth(72)
        self.zoom_footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zlayout.addWidget(self.zoom_footer_label)
        zoom_in = QToolButton()
        zoom_in.setIcon(line_icon('zoom_in'))
        zoom_in.setToolTip('Zoom in')
        zoom_in.clicked.connect(lambda: self.zoom_step(1))
        zlayout.addWidget(zoom_in)
        layout.addWidget(self.zoom_footer)
        self.zoom_footer.hide()

        self.splitter.addWidget(right)
        self.splitter.setSizes([290, 990])
        self.splitter.splitterMoved.connect(lambda *_: self.resize_timer.start(150))
        self.setCentralWidget(self.splitter)
        self.statusBar().showMessage('Open a book · ⌘O')

    def apply_style(self):
        bg, panel, ink, muted, border, canvas, page = (
            ('#191d24', '#222831', '#e7e9ef', '#a2adbd', '#384150', '#11161b', '#f8f8f6') if self.dark else
            ('#f8f6f1', '#ffffff', '#24332d', '#7b837e', '#e1e4dc', '#e4e7e2', '#ffffff')
        )
        self.setStyleSheet(f'''
        QMainWindow,QWidget {{ background:{bg}; color:{ink}; font-family:"Helvetica Neue","Arial"; font-size:13px; }}
        QToolBar {{ border:0; border-bottom:1px solid {border}; padding:7px 9px; spacing:5px; }}
        QToolButton {{ border:1px solid {border}; border-radius:7px; padding:5px; background:{panel}; min-width:26px; min-height:26px; }}
        QToolButton:hover,QPushButton:hover {{ border-color:#4d8b70; background:{panel}; }}
        QPushButton {{ border:1px solid {border}; border-radius:7px; padding:8px 12px; background:{panel}; }}
        QLineEdit,QSpinBox,QComboBox {{ padding:6px 8px; border:1px solid {border}; border-radius:7px; background:{panel}; }}
        QListWidget,QTreeWidget {{ border:0; background:transparent; outline:0; }}
        QListWidget::item {{ padding:11px 8px; border-bottom:1px solid {border}; }}
        QListWidget::item:selected,QTreeWidget::item:selected {{ background:#dcece2; color:#24332d; border-radius:6px; }}
        QTabWidget::pane {{ border:0; }}
        QTabBar::tab {{ padding:8px 5px; color:{muted}; }}
        QTabBar::tab:selected {{ color:{ink}; border-bottom:2px solid #428166; }}
        QScrollArea#pageArea,QWidget#pagesContainer {{ background:{canvas}; border:0; }}
        QLabel#bookPage {{ background:{page}; color:#9aa39e; border:1px solid #cfd5d0; }}
        QLabel#brand {{ font-size:23px; font-weight:700; letter-spacing:4px; }}
        QLabel#muted {{ color:{muted}; font-size:11px; }}
        QLabel#eyebrow {{ color:#579178; font-size:11px; font-weight:600; letter-spacing:2px; }}
        QLabel#headline {{ font-size:34px; font-weight:600; padding:18px 0 8px; }}
        QLabel#description {{ color:{muted}; font-size:15px; padding:4px; }}
        QPushButton#primary {{ background:#2d694f; color:white; border:0; padding:12px 26px; font-weight:600; }}
        QWidget#zoomFooter {{ border-top:1px solid {border}; background:{bg}; }}
        QWidget#printCanvas {{ background:#dfe2df; }}
        QWidget#printSettings {{ background:{panel}; border-right:1px solid {border}; }}
        QLabel#printTitle {{ font-size:28px; font-weight:600; padding-bottom:12px; }}
        QLabel#printPage {{ background:#ffffff; color:#777; border:1px solid #c9ceca; }}
        QStatusBar {{ border-top:1px solid {border}; color:{muted}; padding:3px; }}
        ''')
