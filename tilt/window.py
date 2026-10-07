from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
import sqlite3

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QIcon, QPixmap, QTextDocument, QDesktopServices, QAction, QKeySequence
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QTextBrowser,
    QVBoxLayout, QWidget,
)

from .engineering import C_SI, C_WORKSHEET, Design, array_pattern, calculate, channel_frequency, parse_decimal
from .reports import export_csv, export_json, fmt, report_html, snapshot
from .visuals import ArrayIllustration, LengthIllustration, SeriesChart, BLUE, TEAL

ASSETS = Path(__file__).parent / 'assets'
CUSTOM = 'Personalizado / referência da planilha'

STYLE = '''
QMainWindow, QDialog {background:#edf2f8;}
QWidget {font-family:"Segoe UI";font-size:10pt;color:#172d48;}
QFrame#Header {background:white;border-bottom:1px solid #d4deeb;}
QLabel#AppTitle {font-size:23pt;font-weight:650;color:#092c74;}
QLabel#Subtitle {color:#64768c;font-size:10pt;}
QLabel#State {background:#e9effa;color:#24419b;border-radius:5px;padding:8px;font-weight:600;}
QLabel#Error {background:#fff0ef;color:#a02d22;border:1px solid #f0c5be;padding:10px;border-radius:5px;}
QLabel#Notice {background:#fff7e8;color:#895716;border:1px solid #eed7ac;padding:9px;border-radius:5px;}
QGroupBox {background:white;border:1px solid #d6e0ec;border-radius:7px;margin-top:13px;padding:14px 10px 9px 10px;font-weight:600;}
QGroupBox::title {subcontrol-origin:margin;left:12px;padding:0 4px;color:#264a83;}
QLineEdit,QComboBox,QSpinBox {background:white;border:1px solid #c5d2e1;border-radius:5px;min-height:29px;padding:2px 8px;selection-background-color:#2946c7;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus {border:1px solid #2946c7;}
QLineEdit[invalid="true"] {border:2px solid #ca4434;background:#fff5f3;}
QLineEdit:disabled,QComboBox:disabled {background:#f0f4f8;color:#64768c;}
QPushButton {background:white;border:1px solid #bdccdc;border-radius:5px;padding:8px 13px;font-weight:600;min-height:19px;}
QPushButton:hover {background:#eaf0ff;border-color:#2946c7;}
QPushButton:pressed {background:#dce5ff;}
QPushButton:disabled {color:#93a0b0;background:#f0f3f7;border-color:#dce3ec;}
QPushButton#Primary {background:#143b9b;color:white;border:1px solid #143b9b;}
QPushButton#Primary:hover {background:#254eb5;}
QPushButton#Primary:disabled {background:#a8b6d4;border-color:#a8b6d4;}
QTabWidget::pane {border:1px solid #d6e0ec;background:white;border-radius:4px;}
QTabBar::tab {padding:11px 17px;background:#eaf0f7;color:#62748a;border-bottom:2px solid transparent;}
QTabBar::tab:selected {background:white;color:#123d96;border-bottom:2px solid #c5202c;font-weight:600;}
QTableWidget {background:white;alternate-background-color:#f5f8fc;gridline-color:#e5ebf2;border:0;selection-background-color:#d9e6ff;selection-color:#173b75;}
QHeaderView::section {background:#eaf0f8;color:#24456f;border:0;border-bottom:1px solid #cbd8e9;padding:9px;font-weight:600;}
QFrame#Metric {background:white;border:1px solid #d6e0ec;border-radius:6px;}
QLabel#MetricValue {color:#0b3386;font-size:21pt;font-weight:650;}
QLabel#MetricName {color:#64768c;font-size:9pt;}
QScrollArea {border:0;background:transparent;}
QScrollBar:vertical {background:#edf2f8;width:10px;}
QScrollBar::handle:vertical {background:#b8c7da;border-radius:4px;min-height:30px;}
QTextBrowser {border:0;background:white;padding:14px;}
QStatusBar {background:#142d50;color:white;}
QStatusBar QLabel {color:white;}
'''


def label(value, name=None, wrap=False):
    item = QLabel(value)
    if name:
        item.setObjectName(name)
    item.setWordWrap(wrap)
    return item


def table(headers):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setAlternatingRowColors(True)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.verticalHeader().setVisible(False)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    widget.horizontalHeader().setStretchLastSection(True)
    widget.setSortingEnabled(False)
    return widget


def fill_table(widget, rows):
    widget.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            item = QTableWidgetItem(str(value))
            if j:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            widget.setItem(i, j, item)


class MainWindow(QMainWindow):
    def __init__(self, database):
        super().__init__()
        self.db = database
        self.result = None
        self.calculated_payload = None
        self.loading = True
        self.fields = {}
        self.field_labels = {}
        self.setWindowTitle('EFTX ANTENNAS · Tilt elétrico')
        self.setWindowIcon(QIcon(str(ASSETS / 'eftx_logo.jpeg')))
        self.resize(1540, 1000)
        self.setMinimumSize(1100, 760)
        self.setStyleSheet(STYLE)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(root)
        layout.addWidget(self._header())
        self.pages = QTabWidget()
        self.pages.setDocumentMode(True)
        layout.addWidget(self.pages, 1)
        self._workbench()
        self._catalog_page()
        self._projects_page()
        self._method_page()
        self.statusBar().showMessage('Catálogo ADT-PY · 47 modelos · dados locais em SQLite')
        self.loading = False
        self.rebuild_models()
        self.run_calculation()
        self.refresh_projects()
        action = QAction('Calcular', self)
        action.setShortcut(QKeySequence('Ctrl+Return'))
        action.triggered.connect(self.run_calculation)
        self.addAction(action)
        save_action = QAction('Salvar revisão', self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_project)
        self.addAction(save_action)

    def _header(self):
        frame = QFrame()
        frame.setObjectName('Header')
        row = QHBoxLayout(frame)
        row.setContentsMargins(18, 4, 22, 4)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(ASSETS / 'eftx_logo.jpeg')).scaled(180, 114, Qt.AspectRatioMode.KeepAspectRatio,
                                                                 Qt.TransformationMode.SmoothTransformation))
        logo.setFixedSize(184, 114)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(label('Tilt elétrico', 'AppTitle'))
        titles.addWidget(label('Dimensionamento entre elementos · cabos coaxiais e linhas rígidas', 'Subtitle'))
        self.project_name = QLineEdit('Arranjo vertical — estudo de tilt')
        self.project_name.setMaxLength(160)
        self.project_name.setToolTip('Nome da revisão salva no banco local')
        titles.addWidget(self.project_name)
        row.addLayout(titles, 1)
        row.addSpacing(20)
        self.save_button = QPushButton('Salvar revisão')
        self.save_button.clicked.connect(self.save_project)
        row.addWidget(self.save_button)
        self.export_button = QPushButton('Exportar…')
        self.export_button.clicked.connect(self.export)
        row.addWidget(self.export_button)
        return frame

    def _field(self, form, key, title, value, unit='', hint=''):
        edit = QLineEdit(str(value))
        edit.setMinimumWidth(65)
        edit.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        edit.setObjectName(key)
        edit.setToolTip(hint or title)
        edit.textChanged.connect(self.invalidate)
        edit.textChanged.connect(self._clear_error)
        self.fields[key], self.field_labels[key] = edit, title
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        row.addWidget(edit, 1)
        if unit:
            suffix = label(unit)
            suffix.setMinimumWidth(48)
            row.addWidget(suffix)
        form.addRow(title, holder)
        return edit

    def _group(self, title, layout):
        group = QGroupBox(title)
        form = QFormLayout(group)
        form.setHorizontalSpacing(9)
        form.setVerticalSpacing(7)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addWidget(group)
        return form

    def _workbench(self):
        page = QWidget()
        outer = QHBoxLayout(page)
        outer.setContentsMargins(12, 12, 12, 12)
        splitter = QSplitter()
        outer.addWidget(splitter)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        left = QWidget()
        left.setMinimumWidth(330)
        left.setMaximumWidth(450)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(scroll, 1)
        controls = QWidget()
        inputs = QVBoxLayout(controls)
        inputs.setContentsMargins(0, 0, 8, 0)
        inputs.setSpacing(9)
        scroll.setWidget(controls)
        splitter.addWidget(left)
        form = self._group('01   Frequência de operação', inputs)
        self.frequency_mode = QComboBox()
        self.frequency_mode.addItems(['Frequência informada', 'Canal de TV (centro de 6 MHz)'])
        self.frequency_mode.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        form.addRow('Entrada', self.frequency_mode)
        self.channel = QSpinBox()
        self.channel.setRange(2, 69)
        self.channel.setValue(39)
        self.channel.setEnabled(False)
        form.addRow('Canal', self.channel)
        self._field(form, 'frequency_mhz', 'Frequência', 623, 'MHz')
        self.ofdm_offset = QCheckBox('Aplicar deslocamento +1/7 MHz')
        self.ofdm_offset.setEnabled(False)
        form.addRow(self.ofdm_offset)
        self.frequency_mode.currentIndexChanged.connect(self.frequency_changed)
        self.channel.valueChanged.connect(self.frequency_changed)
        self.ofdm_offset.toggled.connect(self.frequency_changed)
        self.fields['frequency_mhz'].textChanged.connect(self.update_line_properties)
        form = self._group('02   Linha de alimentação', inputs)
        self.kind = QComboBox()
        self.kind.addItem('Cabo coaxial', 'cable')
        self.kind.addItem('Linha rígida', 'rigid')
        form.addRow('Construção', self.kind)
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.model.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.model.setMinimumContentsLength(15)
        form.addRow('Modelo', self.model)
        self.override_vf = QCheckBox('Usar VF medido / informado')
        form.addRow(self.override_vf)
        self._field(form, 'velocity_factor', 'Fator de velocidade', 0.88, 'v/c')
        self._field(form, 'attenuation_db_100m', 'Atenuação', '', 'dB/100 m', 'Deixe vazio no modo personalizado se a atenuação for desconhecida.')
        self.line_info = label('', 'Subtitle', True)
        form.addRow(self.line_info)
        self.kind.currentIndexChanged.connect(self.rebuild_models)
        self.model.currentTextChanged.connect(self.update_line_properties)
        self.override_vf.toggled.connect(self.update_line_properties)
        form = self._group('03   Arranjo vertical', inputs)
        self.elements = QSpinBox()
        self.elements.setRange(2, 64)
        self.elements.setValue(4)
        self.elements.valueChanged.connect(self.invalidate)
        form.addRow('Elementos', self.elements)
        self._field(form, 'spacing_mm', 'Espaçamento', 480, 'mm', 'Distância entre centros de fase de elementos adjacentes.')
        self._field(form, 'tilt_deg', 'Tilt desejado', 2, '°')
        form.addRow(label('Positivo: para baixo · negativo: para cima', 'Subtitle'))
        self._field(form, 'shortest_branch_m', 'Ramal mais curto', 3, 'm', 'Comprimento entre planos de referência. Verifique o percurso físico de todos os ramais.')
        self._field(form, 'cut_step_mm', 'Passo de corte', 0.1, 'mm', '0 = comprimento ideal; valor positivo = arredondamento ao passo de fabricação.')
        form = self._group('04   Perdas e potência', inputs)
        self._field(form, 'common_feeder_m', 'Linha comum', 0, 'm', 'Mesmo modelo do ramal, antes do divisor.')
        self._field(form, 'extra_loss_db', 'Perdas adicionais', 0, 'dB', 'Perda total adicional por caminho: conectores e perda de inserção do divisor, excluindo a divisão ideal 1/N.')
        self._field(form, 'input_power_w', 'Potência de entrada', 1000, 'W')
        self.speed = QComboBox()
        self.speed.addItem('Planilhas · c = 300.000.000 m/s', C_WORKSHEET)
        self.speed.addItem('SI · c = 299.792.458 m/s', C_SI)
        self.speed.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.speed.currentIndexChanged.connect(self.invalidate)
        form.addRow('Constante c', self.speed)
        self.error = label('', 'Error', True)
        self.error.hide()
        left_layout.addWidget(self.error)
        self.calculate_button = QPushButton('Calcular arranjo   Ctrl+Enter')
        self.calculate_button.setObjectName('Primary')
        self.calculate_button.clicked.connect(self.run_calculation)
        left_layout.addWidget(self.calculate_button)
        examples = QHBoxLayout()
        for title, mode in [('Exemplo: cabo', 'cable'), ('Exemplo: rígida', 'rigid')]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, m=mode: self.load_example(m))
            examples.addWidget(button)
        left_layout.addLayout(examples)
        inputs.addStretch()
        right = QWidget()
        content = QVBoxLayout(right)
        content.setContentsMargins(7, 0, 0, 0)
        content.setSpacing(10)
        self.state = label('Informe as entradas e calcule.', 'State')
        content.addWidget(self.state)
        metrics = QGridLayout()
        self.metrics = {}
        for i, (key, name, unit) in enumerate([
            ('delta', 'Diferença de comprimento / nível', 'mm'), ('phase', 'Avanço de fase / nível', 'graus'),
            ('efficiency', 'Eficiência de alimentação', '%'), ('power', 'Potência entregue ao arranjo', 'W')]):
            card = QFrame()
            card.setObjectName('Metric')
            column = QVBoxLayout(card)
            column.setContentsMargins(14, 11, 14, 11)
            column.addWidget(label(name, 'MetricName', True))
            value = label('—', 'MetricValue')
            column.addWidget(value)
            column.addWidget(label(unit, 'Subtitle'))
            metrics.addWidget(card, 0, i)
            self.metrics[key] = value
        content.addLayout(metrics)
        self.result_tabs = QTabWidget()
        visuals = QSplitter()
        self.array = ArrayIllustration()
        self.pattern = SeriesChart('Fator de arranjo vertical', 'Elementos isotrópicos · campo normalizado')
        visuals.addWidget(self.array)
        visuals.addWidget(self.pattern)
        visuals.setSizes([480, 470])
        self.result_tabs.addTab(visuals, 'Arranjo e diagrama')
        cut_page = QWidget()
        cut_layout = QVBoxLayout(cut_page)
        self.lengths = LengthIllustration()
        self.lengths.setMaximumHeight(280)
        cut_layout.addWidget(self.lengths)
        self.element_table = table(['Elemento', 'z (m)', 'Ideal (mm)', 'Corte (mm)', 'Fase (°)', 'Erro (°)', 'Perda (dB)', 'Potência (W)'])
        cut_layout.addWidget(self.element_table, 1)
        self.result_tabs.addTab(cut_page, 'Comprimentos por elemento')
        losses_page = QSplitter(Qt.Orientation.Vertical)
        self.attenuation_chart = SeriesChart('Atenuação da linha', 'Pontos do catálogo e interpolação log-log')
        self.power_chart = SeriesChart('Distribuição de potência', 'Divisão ideal igual; perdas por caminho')
        losses_page.addWidget(self.attenuation_chart)
        losses_page.addWidget(self.power_chart)
        losses_scroll = QScrollArea()
        losses_scroll.setWidgetResizable(True)
        losses_scroll.setWidget(losses_page)
        self.result_tabs.addTab(losses_scroll, 'Perdas e potência')
        self.report_preview = QTextBrowser()
        self.result_tabs.addTab(self.report_preview, 'Memória do cálculo')
        content.addWidget(self.result_tabs, 1)
        self.secondary = label('', 'Subtitle', True)
        content.addWidget(self.secondary)
        self.warnings = label('', 'Notice', True)
        content.insertWidget(2, self.warnings)
        self.limits = label('Modelo: alimentação paralela com divisão igual. Eficiência da alimentação exclui radiação, ROE e acoplamento. Comprimentos entre planos de referência.', 'Subtitle', True)
        content.addWidget(self.limits)
        result_scroll = QScrollArea()
        result_scroll.setWidgetResizable(True)
        result_scroll.setWidget(right)
        splitter.addWidget(result_scroll)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([375, 1100])
        self.pages.addTab(page, 'Bancada de cálculo')

    def _catalog_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addWidget(label('Catálogo de linhas de transmissão', 'AppTitle'))
        layout.addWidget(label('47 modelos importados do ADT-PY · 1.669 amostras · sem extrapolação de frequência', 'Subtitle'))
        self.catalog_search = QLineEdit()
        self.catalog_search.setPlaceholderText('Filtrar por modelo, impedância ou tipo…')
        layout.addWidget(self.catalog_search)
        self.catalog_table = table(['Modelo', 'Tipo', 'VF', 'Ω', 'Mín. MHz', 'Máx. MHz', 'Pico kW', 'Tensão pico V', 'Amostras'])
        layout.addWidget(self.catalog_table, 1)
        self.catalog_detail = label('Selecione um modelo para ver suas características na frequência de trabalho.', 'Subtitle', True)
        layout.addWidget(self.catalog_detail)
        use = QPushButton('Usar modelo selecionado na bancada')
        use.setObjectName('Primary')
        use.clicked.connect(self.use_catalog_selection)
        layout.addWidget(use, alignment=Qt.AlignmentFlag.AlignLeft)
        self.catalog_search.textChanged.connect(self.refresh_catalog)
        self.catalog_table.itemSelectionChanged.connect(self.describe_catalog_selection)
        self.catalog_table.doubleClicked.connect(self.use_catalog_selection)
        self.refresh_catalog()
        self.pages.addTab(page, 'Catálogo de cabos e linhas')

    def _projects_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addWidget(label('Projetos e revisões', 'AppTitle'))
        layout.addWidget(label('Cada salvamento cria uma revisão independente com entradas e resultados. Dados armazenados neste computador.', 'Subtitle', True))
        self.project_table = table(['Revisão', 'Projeto', 'Salvo em (horário local)'])
        layout.addWidget(self.project_table)
        buttons = QHBoxLayout()
        load = QPushButton('Abrir revisão selecionada')
        load.setObjectName('Primary')
        load.clicked.connect(self.open_project)
        buttons.addWidget(load)
        refresh = QPushButton('Atualizar lista')
        refresh.clicked.connect(self.refresh_projects)
        buttons.addWidget(refresh)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.project_table.doubleClicked.connect(self.open_project)
        self.pages.addTab(page, 'Projetos salvos')

    def _method_page(self):
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml('''<h1>Método e convenções</h1>
        <h2>01 · Tilt e diferença de percurso</h2><p>O eixo vertical cresce de E1 (inferior) para EN (superior).
        Tilt positivo aponta para baixo. O elemento superior recebe avanço de fase, usando um ramal mais curto.</p>
        <p><b>λ₀ = c / f<br>λg = VF × λ₀<br>Δφ = 360° × (d/λ₀) × sen(θ)<br>ΔL = VF × d × sen(θ)</b></p>
        <p>Para as mesmas geometria e VF, ΔL é independente da frequência. A fase e as perdas variam com a frequência.
        A aplicação usa comprimento total, sem reduzir módulo λg, preservando o atraso real.</p>
        <h2>02 · Comprimentos de fabricação</h2><p>Informe o ramal mais curto e confira que todos os caminhos podem ser montados.
        Os comprimentos ideais são deslocados por uma constante comum para manter o mínimo informado.
        O passo de corte arredonda cada comprimento individualmente. Fases e erros usam os comprimentos arredondados.</p>
        <p>Linhas rígidas usam o mesmo princípio de percurso elétrico. O valor é a diferença de comprimento elétrico convertida
        em comprimento físico; não é automaticamente o curso de um mecanismo telescópico. A célula K16 da planilha rígida
        divide ΔL por 4 sem identificar a geometria. Por isso, esse fator mecânico não é aplicado.</p>
        <h2>03 · Eficiência e potência</h2><p>Pin é a potência antes da linha comum e do divisor. Cada ramo recebe Pin/N antes das perdas.
        A perda de divisão ideal não é dissipada; não some 10 log₁₀(N) às perdas adicionais.
        Aᵢ = α(Lcomum + Lᵢ)/100 + Aextra. Pᵢ = Pin/N × 10^(−Aᵢ/10).</p>
        <p><b>Eficiência de alimentação = ΣPᵢ / Pin.</b> A coerência no alvo mede a combinação de amplitudes e erros de fase,
        normalizada pelo arranjo ideal com a mesma potência entregue. Nenhuma dessas métricas é o rendimento de radiação da antena.</p>
        <h2>04 · Catálogo e frequência</h2><p>VF, impedância, perdas e potências vêm do CableRating.xml do ADT-PY.
        Atenuação e potência média são interpoladas em escala log-log apenas entre amostras do próprio modelo.
        Valores fora da faixa são bloqueados. As potências nominais do catálogo não incluem validação térmica,
        de altitude, temperatura, conectores, ROE ou ciclo de trabalho.</p>
        <p>O modo personalizado aceita VF informado. Atenuação desconhecida mantém perdas e eficiência indisponíveis.
        O campo VF medido substitui explicitamente o VF do catálogo. Conectores e descontinuidades requerem medição de fase.</p>
        <p>A conversão de canal usa centro geométrico de canais TV de 6 MHz (2–69, incluindo canais históricos).
        O deslocamento +1/7 MHz é opcional. Esta tabela não verifica disponibilidade, destinação ou autorização de uso.</p>
        <h2>05 · Diagrama e limites</h2><p>O gráfico representa somente o fator de arranjo de elementos idênticos isotrópicos,
        sem padrão individual, terreno, estrutura da torre, acoplamento ou descasamento. Não é ganho em dBi.
        Lóbulos de grade são sinalizados quando existem outras soluções visíveis da progressão ideal.</p>
        <h2>Referências</h2><ul><li>Plan1 das duas planilhas fornecidas (D5, D7, D9, D11, D15 e D17).</li>
        <li>Catálogo ADT-PY / Rating / CableRating.xml.</li>
        <li><a href="https://www.analog.com/en/resources/analog-dialogue/articles/phased-array-antenna-patterns-part1.html">Analog Devices: fator de arranjo</a></li>
        <li><a href="https://www.analog.com/en/resources/analog-dialogue/articles/phased-array-antenna-patterns-part2.html">Analog Devices: lóbulos de grade e atraso</a></li></ul>''')
        self.pages.addTab(browser, 'Método e referências')

    def _clear_error(self):
        field = self.sender()
        if isinstance(field, QLineEdit) and field.property('invalid'):
            field.setProperty('invalid', False)
            field.style().unpolish(field)
            field.style().polish(field)

    def invalidate(self, *_):
        if self.loading:
            return
        self.result = None
        self.calculated_payload = None
        self.state.setText('Entradas alteradas · calcule novamente para atualizar e exportar.')
        self.save_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.result_tabs.setEnabled(False)
        for value in self.metrics.values():
            value.setText('—')
        self.warnings.hide()
        self.secondary.setText('Resultados anteriores desativados até novo cálculo.')

    def frequency_changed(self, *_):
        derived = self.frequency_mode.currentIndex() == 1
        self.channel.setEnabled(derived)
        self.ofdm_offset.setEnabled(derived)
        self.fields['frequency_mhz'].setEnabled(not derived)
        if derived:
            value = channel_frequency(self.channel.value()) + (1/7 if self.ofdm_offset.isChecked() else 0)
            self.fields['frequency_mhz'].setText(f'{value:.9f}'.rstrip('0').rstrip('.'))
        self.update_line_properties()

    def rebuild_models(self, *_):
        self.model.blockSignals(True)
        self.model.clear()
        self.model.addItems([c.name for c in self.db.cables(self.kind.currentData())])
        self.model.addItem(CUSTOM)
        preferred = 'LCF12-50' if self.kind.currentData() == 'cable' else '3 1/8" 50 Ohm Rigid Line'
        self.model.setCurrentText(preferred)
        self.model.blockSignals(False)
        self.override_vf.setChecked(False)
        self.update_line_properties()

    def update_line_properties(self, *_):
        custom = self.model.currentText() == CUSTOM
        if custom and getattr(self, '_last_model', None) != CUSTOM and not self.loading:
            self.fields['attenuation_db_100m'].clear()
            self.fields['velocity_factor'].setText('0.88' if self.kind.currentData() == 'cable' else '0.995')
        self._last_model = self.model.currentText()
        self.fields['velocity_factor'].setEnabled(custom or self.override_vf.isChecked())
        self.fields['attenuation_db_100m'].setEnabled(custom)
        self.override_vf.setEnabled(not custom)
        if custom:
            self.line_info.setText('Dados informados pelo usuário. Atenuação vazia = eficiência indisponível.')
        else:
            try:
                cable = self.db.cable(self.model.currentText())
                if not self.override_vf.isChecked():
                    self.fields['velocity_factor'].setText(str(cable.velocity_factor))
                f = parse_decimal(self.fields['frequency_mhz'].text(), 'Frequência')
                attenuation, power = cable.at(f)
                self.fields['attenuation_db_100m'].setText(f'{attenuation:.9g}')
                lo, hi = cable.frequency_range
                self.line_info.setText(f'{cable.impedance_ohm:g} Ω · {lo:g}–{hi:g} MHz\nPotência média de catálogo: {fmt(power, 2)} kW')
            except ValueError as exc:
                self.fields['attenuation_db_100m'].clear()
                self.line_info.setText(str(exc))
        self.invalidate()

    def number(self, key, optional=False):
        edit = self.fields[key]
        if optional and not edit.text().strip():
            return None
        try:
            return parse_decimal(edit.text(), self.field_labels[key])
        except ValueError:
            edit.setProperty('invalid', True)
            edit.style().unpolish(edit)
            edit.style().polish(edit)
            edit.setFocus()
            raise

    def read_design(self):
        values = {key: self.number(key, key == 'attenuation_db_100m') for key in self.fields}
        if self.model.currentText() != CUSTOM:
            cable = self.db.cable(self.model.currentText())
            self.attenuation_chart.subtitle = 'Pontos do catálogo e interpolação log-log'
            if cable.kind != self.kind.currentData():
                raise ValueError('Selecione um modelo do tipo de linha informado.')
            values['attenuation_db_100m'], _ = cable.at(values['frequency_mhz'])
            if not self.override_vf.isChecked():
                values['velocity_factor'] = cable.velocity_factor
        values['spacing_m'] = values.pop('spacing_mm') / 1000
        return Design(**values, elements=self.elements.value(), speed_m_s=self.speed.currentData())

    def input_payload(self, design):
        return dict(schema_version=1, design=asdict(design), kind=self.kind.currentData(),
                    model=self.model.currentText(), override_vf=self.override_vf.isChecked(),
                    frequency_mode=self.frequency_mode.currentIndex(), channel=self.channel.value(),
                    ofdm_offset=self.ofdm_offset.isChecked())

    def run_calculation(self):
        try:
            design = self.read_design()
            result = calculate(design)
        except ValueError as exc:
            self.invalidate()
            self.error.setText(str(exc))
            self.error.show()
            self.state.setText('Cálculo não executado · corrija a entrada indicada.')
            return False
        self.error.hide()
        self.result = result
        self.calculated_payload = self.input_payload(design)
        self.render_result()
        return True

    def render_result(self):
        r, d = self.result, self.result.design
        self.state.setText(f'Calculado · {d.elements} elementos · {fmt(d.frequency_mhz, 4)} MHz · tilt {fmt(d.tilt_deg, 2)}°')
        for key, value, digits in [('delta', r.delta_length_m*1000, 3), ('phase', r.phase_step_deg, 3),
                                  ('efficiency', None if r.feed_efficiency is None else r.feed_efficiency*100, 2),
                                  ('power', r.total_power_w, 1)]:
            self.metrics[key].setText(fmt(value, digits))
        self.save_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.result_tabs.setEnabled(True)
        self.array.set_result(r, self.kind.currentData())
        self.lengths.set_result(r, self.kind.currentData())
        angles, pattern = array_pattern(r)
        _, zero = array_pattern(r, untilted=True)
        self.pattern.set_data([('Com tilt', angles, pattern, BLUE), ('Sem tilt', angles, zero, '#96b3ca')],
                              'Elevação (°) · negativo = abaixo do horizonte', 'Campo normalizado (dB)',
                              (-90, 90), (-40, 0), -d.tilt_deg)
        fill_table(self.element_table, [[f'E{e.number}', fmt(e.height_m), fmt(e.ideal_length_m*1000),
                    fmt(e.length_m*1000), fmt(e.relative_phase_deg), fmt(e.phase_error_deg),
                    fmt(e.loss_db), fmt(e.power_w)] for e in r.elements])
        warnings = list(r.warnings)
        if self.model.currentText() != CUSTOM:
            cable = self.db.cable(self.model.currentText())
            curve_f = []
            for a, b in zip(cable.samples, cable.samples[1:]):
                curve_f.extend(a[0]*(b[0]/a[0])**(j/8) for j in range(8))
            curve_f.append(cable.samples[-1][0])
            self.attenuation_chart.set_data([('Interpolação do catálogo', curve_f, [cable.at(f)[0] for f in curve_f], BLUE)],
                                           'Frequência (MHz)', 'Atenuação (dB/100 m)', marker_x=d.frequency_mhz)
            _, rating_kw = cable.at(d.frequency_mhz)
            branch_input = d.input_power_w/d.elements * 10**(-(d.attenuation_db_100m*d.common_feeder_m/100)/10)
            if branch_input > rating_kw*1000 or (d.common_feeder_m > 0 and d.input_power_w > rating_kw*1000):
                warnings.append('Potência acima da referência média do catálogo em ao menos um trecho. Revise o dimensionamento térmico.')
            warnings.append('Potências de catálogo são referências; condições térmicas e de ROE não foram fornecidas.')
        else:
            self.attenuation_chart.set_data([])
            self.attenuation_chart.subtitle = 'Modelo personalizado: sem curva de frequência disponível'
        if r.total_power_w is not None:
            n = [e.number for e in r.elements]
            self.power_chart.set_data([('Entregue', n, [e.power_w for e in r.elements], TEAL),
                                       ('Antes das perdas', n, [d.input_power_w/d.elements]*d.elements, '#96b3ca')],
                                      'Elemento · E1 inferior', 'Potência (W)', (1, d.elements), (0, d.input_power_w/d.elements*1.08))
        else:
            self.power_chart.set_data([])
        if self.frequency_mode.currentIndex() == 1 and (self.channel.value() > 51 or self.channel.value() == 37):
            warnings.append('Canal histórico ou de destinação específica. A conversão não verifica autorização de uso.')
        r = replace(r, warnings=tuple(warnings))
        self.result = r
        self.report_preview.setHtml(report_html(r, self.model.currentText(), self.project_name.text()))
        self.secondary.setText(f'λ₀ {fmt(r.wavelength_m*1000)} mm  ·  λg {fmt(r.guided_wavelength_m*1000)} mm  ·  '
                               f'Coerência no alvo {fmt(r.coherence_efficiency*100, 3)}%  ·  '
                               f'Tilt da progressão após corte {fmt(r.fitted_tilt_deg, 4)}°  ·  Perda {fmt(r.equivalent_loss_db)} dB')
        self.warnings.setText('\n'.join(warnings))
        self.warnings.setVisible(bool(warnings))
        self.statusBar().showMessage('Cálculo concluído · Ctrl+S salva uma nova revisão · gráficos disponíveis para inspeção com o mouse')

    def load_example(self, kind):
        self.loading = True
        self.frequency_mode.setCurrentIndex(0)
        self.kind.setCurrentIndex(0 if kind == 'cable' else 1)
        self.model.setCurrentText(CUSTOM)
        self.override_vf.setChecked(False)
        self.elements.setValue(2)
        values = dict(frequency_mhz=623 if kind == 'cable' else 107.7,
                      spacing_mm=1960 if kind == 'cable' else 2771.5877437325903,
                      tilt_deg=2 if kind == 'cable' else 5,
                      velocity_factor=0.88 if kind == 'cable' else 0.995,
                      shortest_branch_m=0.9698053480875263 if kind == 'cable' else 1,
                      attenuation_db_100m='', common_feeder_m=0, extra_loss_db=0,
                      input_power_w=1000, cut_step_mm=0)
        for key, value in values.items():
            self.fields[key].setText(str(value))
        self.speed.setCurrentIndex(0)
        self.project_name.setText('Referência da planilha — ' + ('cabo' if kind == 'cable' else 'linha rígida'))
        self.loading = False
        self.update_line_properties()
        self.pages.setCurrentIndex(0)
        self.run_calculation()

    def refresh_catalog(self):
        query = self.catalog_search.text().strip().casefold()
        rows = [[c.name, 'Rígida' if c.kind == 'rigid' else 'Cabo', fmt(c.velocity_factor, 3),
                 f'{c.impedance_ohm:g}', *[f'{v:g}' for v in c.frequency_range],
                 f'{c.peak_power_kw:g}', f'{c.peak_voltage_v:g}', len(c.samples)] for c in self.db.cables()]
        fill_table(self.catalog_table, [r for r in rows if query in ' '.join(map(str, r)).casefold()])

    def describe_catalog_selection(self):
        row = self.catalog_table.currentRow()
        if row < 0 or self.catalog_table.item(row, 0) is None:
            return
        cable = self.db.cable(self.catalog_table.item(row, 0).text())
        try:
            f = self.number('frequency_mhz')
            attenuation, power = cable.at(f)
            self.catalog_detail.setText(f'{cable.name} a {fmt(f)} MHz: {fmt(attenuation, 4)} dB/100 m · '
                                        f'potência média {fmt(power, 3)} kW · interpolação log-log entre pontos do modelo.')
        except ValueError as exc:
            self.catalog_detail.setText(str(exc))

    def use_catalog_selection(self, *_):
        row = self.catalog_table.currentRow()
        if row < 0:
            return
        cable = self.db.cable(self.catalog_table.item(row, 0).text())
        self.kind.setCurrentIndex(0 if cable.kind == 'cable' else 1)
        self.model.setCurrentText(cable.name)
        self.pages.setCurrentIndex(0)

    def save_project(self):
        if self.result is None:
            self.statusBar().showMessage('Calcule o arranjo antes de salvar.')
            return
        try:
            project_id = self.db.save_project(self.project_name.text(), self.calculated_payload,
                snapshot(self.result, self.model.currentText(), self.db.catalog_hash))
        except (ValueError, sqlite3.Error) as exc:
            self.error.setText(str(exc) if isinstance(exc, ValueError) else 'Não foi possível salvar no banco. Verifique espaço e permissão de escrita.')
            self.error.show()
            return
        self.refresh_projects()
        self.statusBar().showMessage(f'Revisão #{project_id} salva no SQLite com entradas e resultados.')

    def refresh_projects(self):
        fill_table(self.project_table, [[r['id'], r['title'], datetime.fromisoformat(r['created_at']).astimezone().strftime('%d/%m/%Y %H:%M:%S')]
                                        for r in self.db.projects()])

    def open_project(self, *_):
        row = self.project_table.currentRow()
        if row < 0:
            return
        try:
            project = self.db.project(int(self.project_table.item(row, 0).text()))
            self.restore_payload(project['payload'], project['title'])
        except (ValueError, KeyError, TypeError, sqlite3.Error):
            QMessageBox.warning(self, 'Revisão não carregada', 'Dados da revisão inválidos ou incompatíveis com esta versão.')

    def restore_payload(self, payload, title):
        if payload.get('schema_version') != 1:
            raise ValueError('Versão de projeto incompatível.')
        design = Design(**payload['design'])
        design.validate()
        if payload.get('kind') not in ('cable', 'rigid'):
            raise ValueError('Tipo de linha inválido.')
        if payload['model'] != CUSTOM:
            self.db.cable(payload['model'])
        self.loading = True
        try:
            self.kind.setCurrentIndex(0 if payload['kind'] == 'cable' else 1)
            self.model.setCurrentText(payload['model'])
            self.override_vf.setChecked(payload['override_vf'])
            self.frequency_mode.setCurrentIndex(payload['frequency_mode'])
            self.channel.setValue(payload['channel'])
            self.ofdm_offset.setChecked(payload.get('ofdm_offset', False))
            self.elements.setValue(design.elements)
            for key, value in asdict(design).items():
                if key == 'spacing_m':
                    self.fields['spacing_mm'].setText(str(value*1000))
                elif key in self.fields:
                    self.fields[key].setText('' if value is None else str(value))
            self.speed.setCurrentIndex(0 if design.speed_m_s == C_WORKSHEET else 1)
            self.project_name.setText(title)
        finally:
            self.loading = False
        # Catalog changes are intentionally applied only on an explicit calculation.
        self.invalidate()
        self.pages.setCurrentIndex(0)
        self.state.setText('Revisão carregada · confira as entradas e recalcule com o catálogo atual.')

    def export(self):
        if self.result is None:
            return
        selected, filetype = QFileDialog.getSaveFileName(self, 'Exportar cálculo EFTX', 'tilt_eletrico',
            'Relatório PDF (*.pdf);;Tabela CSV (*.csv);;Memória JSON (*.json)')
        if not selected:
            return
        suffix = '.pdf' if 'PDF' in filetype else '.csv' if 'CSV' in filetype else '.json'
        path = Path(selected)
        if path.suffix.lower() != suffix:
            path = Path(str(path) + suffix)
        try:
            if suffix == '.csv':
                export_csv(path, self.result, self.model.currentText())
            elif suffix == '.json':
                export_json(path, {'title': self.project_name.text(), 'inputs': self.calculated_payload,
                                  **snapshot(self.result, self.model.currentText(), self.db.catalog_hash)})
            else:
                self.write_pdf(path)
        except (OSError, ValueError):
            QMessageBox.warning(self, 'Exportação não concluída', 'Não foi possível gravar o arquivo. Verifique a pasta e se ele está aberto em outro programa.')
            return
        self.statusBar().showMessage(f'Exportado: {path.name}')

    def write_pdf(self, path):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(path))
        printer.setDocName(self.project_name.text())
        printer.setCreator('EFTX Tilt 1.0.0')
        from PySide6.QtGui import QPageLayout, QPageSize
        from PySide6.QtCore import QMarginsF
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QMarginsF(15, 14, 15, 14), QPageLayout.Unit.Millimeter)
        doc = QTextDocument()
        logo_url = QUrl('eftx-logo')
        doc.addResource(QTextDocument.ResourceType.ImageResource, logo_url, QPixmap(str(ASSETS / 'eftx_logo.jpeg')))
        html = report_html(self.result, self.model.currentText(), self.project_name.text())
        html = html.replace('<body>', '<body><img src="eftx-logo" width="150" height="99">')
        # Fixed report geometry: resizing the application must not clip exported figures.
        report_array = ArrayIllustration()
        report_array.resize(640, 500)
        report_array.set_result(self.result, self.kind.currentData())
        report_chart = SeriesChart('Fator de arranjo vertical', 'Elementos isotrópicos · campo normalizado')
        report_chart.resize(640, 480)
        angles, values = array_pattern(self.result)
        _, zero = array_pattern(self.result, untilted=True)
        report_chart.set_data([('Com tilt', angles, values, BLUE), ('Sem tilt', angles, zero, '#96b3ca')],
                             'Elevação (°) · negativo = abaixo do horizonte', 'Campo normalizado (dB)',
                             (-90, 90), (-40, 0), -self.result.design.tilt_deg)
        for name, widget in [('arranjo', report_array), ('diagrama', report_chart)]:
            doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), widget.grab())
        html = html.replace('<h2>Comprimentos entre planos de referência</h2>',
                            '<h2 style="page-break-before:always">Comprimentos entre planos de referência</h2>')
        html = html.replace('</body>', '<div style="page-break-before:always"><h2>Ilustrações do cálculo</h2>'
            '<p>Esquema sem escala. Fator de arranjo de elementos isotrópicos.</p>'
            '<p><img src="arranjo" width="550"></p><p><img src="diagrama" width="550"></p></div>'
            f'<p>Catálogo SHA-256: {self.db.catalog_hash}</p></body>')
        doc.setHtml(html)
        doc.print_(printer)
        if not Path(path).exists() or Path(path).stat().st_size < 100:
            raise OSError('PDF não gravado.')
