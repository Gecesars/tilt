from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextBrowser,
    QVBoxLayout, QWidget,
)

from .engineering import C_WORKSHEET, Design, calculate, channel_frequency, parse_decimal, wavelength_m
from .reports import export_csv, export_json, fmt, report_html, snapshot
from .visuals import BLUE, TEAL
from .theme import STYLE, apply_palette
from . import __version__

ASSETS = Path(__file__).parent / 'assets'
CUSTOM = 'Personalizado / referência da planilha'

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
        self.setWindowTitle(f'EFTX ANTENNAS · Tilt elétrico · {__version__}')
        self.setWindowIcon(QIcon(str(ASSETS / 'eftx_logo.jpeg')))
        self.resize(1440, 940)
        self.setMinimumSize(1100, 760)
        apply_palette()
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
        from .diagrams import DiagramPage
        self.diagrams = DiagramPage()
        self.pages.addTab(self.diagrams, 'Diagramas')
        self._catalog_page()
        self._projects_page()
        self._method_page()
        self.statusBar().showMessage('Catálogo ADT-PY · 47 modelos · dados locais em SQLite')
        self.loading = False
        self.rebuild_models()
        self.update_spacing()
        self.run_calculation()
        self.state.setText('Exemplo inicial · substitua os dados pelos da sua instalação e clique em Calcular comprimentos.')
        self.refresh_projects()
        action = QAction('Calcular', self)
        action.setShortcut(QKeySequence('Ctrl+Return'))
        action.triggered.connect(self.run_calculation)
        self.addAction(action)
        save_action = QAction('Salvar revisão', self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_project)
        self.addAction(save_action)
        print_action = QAction('Imprimir', self)
        print_action.setShortcut(QKeySequence.StandardKey.Print)
        print_action.triggered.connect(self.prepare_print)
        self.addAction(print_action)

    def _header(self):
        frame = QFrame()
        frame.setObjectName('Header')
        row = QHBoxLayout(frame)
        row.setContentsMargins(18, 4, 22, 4)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(ASSETS / 'eftx_logo.jpeg')).scaled(130, 82, Qt.AspectRatioMode.KeepAspectRatio,
                                                                 Qt.TransformationMode.SmoothTransformation))
        logo.setFixedSize(134, 82)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(label('Tilt elétrico', 'AppTitle'))
        self.project_name = QLineEdit('Arranjo vertical — estudo de tilt')
        self.project_name.setMaxLength(160)
        self.project_name.setToolTip('Nome da revisão salva no banco local')
        titles.addWidget(self.project_name)
        row.addLayout(titles, 1)
        row.addSpacing(20)
        self.save_button = QPushButton('Salvar cálculo')
        self.save_button.clicked.connect(self.save_project)
        row.addWidget(self.save_button)
        self.export_button = QPushButton('Exportar…')
        self.export_button.clicked.connect(self.export)
        row.addWidget(self.export_button)
        self.print_button = QPushButton('Imprimir…')
        self.print_button.clicked.connect(self.prepare_print)
        row.addWidget(self.print_button)
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
        form.setVerticalSpacing(5)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addWidget(group)
        return form

    def _workbench(self):
        from .workbench import build_workbench
        build_workbench(self)

    def toggle_advanced(self, checked):
        self.advanced_panel.setVisible(checked)
        self.advanced_button.setText('−  Recolher ajustes avançados' if checked else '+  Mostrar ajustes avançados')

    def update_advanced_summary(self, *_):
        def value(key):
            return self.fields[key].text().replace('.', ',') or 'não informado'
        summary = (f"Corte: {value('cut_step_mm')} mm • trecho comum: {value('common_feeder_m')} m • "
                   f"outras perdas: {value('extra_loss_db')} dB")
        self.advanced_summary.setText(summary)
        self.advanced_summary.setToolTip(summary + f" • entrada: {value('input_power_w')} W")

    def toggle_technical(self, checked):
        self.technical_button.setText('−  Recolher detalhes técnicos' if checked else '+  Ver detalhes técnicos')
        for key in ('phase', 'power'):
            self.metric_cards[key].setVisible(checked)
        for index in range(1, self.result_tabs.count()):
            self.result_tabs.setTabVisible(index, checked)
        central = self.feed_layout.currentData() == 'center'
        self.result_tabs.setTabVisible(self.central_tab_index, central)
        self.result_tabs.tabBar().setVisible(checked or central)
        if not checked:
            self.result_tabs.setCurrentIndex(0)
        self.result_detail_stack.setCurrentIndex(0)
        self.array.simple = not checked
        self.array.setMinimumWidth(375 if checked else 260)
        self.array.setMinimumHeight(420 if checked else 340)
        self.array.update()
        self.secondary.setVisible(checked)
        self.update_warnings()

    def update_warnings(self):
        if self.result is None:
            self.warnings.hide()
            return
        warnings = self.result.warnings
        if not self.technical_button.isChecked():
            translations = {
                'O fator de arranjo admite lóbulos de grade. O nível no diagrama completo depende do padrão de cada antena.':
                    'O sinal também pode irradiar em outras direções. Veja os níveis estimados na aba Diagramas.',
                'Atenuação não informada: eficiência de alimentação e potência entregue indisponíveis.':
                    'Faltam dados de perda deste material. Não foi possível estimar a energia que chega às antenas.',
                'Ramal mínimo zero: verifique o percurso físico até cada elemento.':
                    'O trecho mais curto está em zero. Informe um comprimento que alcance a antena.',
                'O passo de corte altera a progressão de tilt em mais de 0,1° ou impede sua realização.':
                    'O arredondamento dos comprimentos altera a inclinação desejada. Revise o passo de corte nos ajustes avançados.',
                'Potências de catálogo são referências; condições térmicas e de ROE não foram fornecidas.':
                    'A capacidade de potência ainda precisa de conferência técnica para as condições da instalação.',
            }
            # The general catalog-rating limitation is always shown in the footer.
            warnings = [translations.get(warning, warning) for warning in warnings
                        if not warning.startswith('Potências de catálogo são referências;')]
        self.warnings.setText('\n'.join(warnings))
        self.warnings.setVisible(bool(warnings))

    def choose_example(self):
        menu = QMenu(self)
        for title, kind in [('Cabos — planilha fornecida', 'cable'), ('Linha rígida — planilha fornecida', 'rigid')]:
            action = menu.addAction(title)
            action.triggered.connect(lambda checked=False, chosen=kind: self.load_example(chosen))
        action = menu.addAction('FM — divisor central (planilha ODS)')
        action.triggered.connect(self.load_central_example)
        menu.exec(self.examples_button.mapToGlobal(self.examples_button.rect().bottomLeft()))

    def reveal_field(self, edit):
        if self.advanced_panel.isAncestorOf(edit):
            self.advanced_button.setChecked(True)
        self.input_scroll.widget().layout().activate()
        self.input_scroll.ensureWidgetVisible(edit)
        edit.setProperty('invalid', True)
        edit.style().unpolish(edit)
        edit.style().polish(edit)
        edit.setFocus()

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
        use = QPushButton('Usar este modelo no cálculo')
        use.setObjectName('Primary')
        use.clicked.connect(self.use_catalog_selection)
        layout.addWidget(use, alignment=Qt.AlignmentFlag.AlignLeft)
        self.catalog_search.textChanged.connect(self.refresh_catalog)
        self.catalog_table.itemSelectionChanged.connect(self.describe_catalog_selection)
        self.catalog_table.doubleClicked.connect(self.use_catalog_selection)
        self.refresh_catalog()
        self.pages.addTab(page, 'Catálogo')

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
        self.pages.addTab(page, 'Cálculos salvos')

    def _method_page(self):
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml('''<h1>Como usar</h1>
        <ol><li>Escolha <b>Cabo coaxial</b> ou <b>Linha rígida</b> e o modelo usado na instalação.</li>
        <li>Informe a frequência em MHz ou o canal de TV.</li>
        <li>Informe a quantidade de antenas, a distância entre seus centros, a inclinação desejada e o trecho mais curto.</li></ol>
        <p>Clique em <b>Calcular comprimentos</b>. A tabela mostra o comprimento para cada antena;
        E1 é a mais baixa. Salve o cálculo ou exporte o resultado para PDF, CSV ou JSON.</p>
        <p><b>Espaçamento automático:</b> a frequência preenche a distância com 1 λ no espaço livre (c/f).
        Editar a distância muda para manual; marque a opção novamente para acompanhar a frequência.
        Um espaçamento de 1 λ não garante ausência de outras direções de máximo.</p>
        <p><b>Diagramas:</b> ajuste início e fim do eixo horizontal entre −90° e +90°.
        Este eixo é elevação, com zero no horizonte e valores negativos para baixo.
        Mudar a faixa não altera os comprimentos.</p>
        <p><b>Imprimir (Ctrl+P):</b> salva um PDF em Documentos/EFTX Tilt/Relatorios e abre a prévia,
        com a impressora padrão selecionada. No diálogo de impressão você pode escolher outra impressora,
        páginas e cópias. Cancelar mantém o PDF e não envia o trabalho.</p>
        <p>Vírgula e ponto são aceitos para decimais. Valores iniciais são apenas um exemplo.
        Os ajustes avançados permitem informar perdas e medidas técnicas. Recolhê-los mantém os valores.
        A energia estimada depende das perdas informadas e não representa o rendimento total da antena.</p>
        <h1>Método e convenções</h1>
        <h2>01 · Tilt e diferença de percurso</h2><p>O eixo vertical cresce de E1 (inferior) para EN (superior).
        Tilt positivo aponta para baixo. O elemento superior recebe avanço de fase, usando um ramal mais curto.</p>
        <p><b>λ₀ = c / f<br>λg = VF × λ₀<br>Δφ = 360° × (d/λ₀) × sen(θ)<br>ΔL = VF × d × sen(θ)</b></p>
        <p>Para as mesmas geometria e VF, ΔL é independente da frequência. A fase e as perdas variam com a frequência.
        A aplicação usa comprimento total, sem reduzir módulo λg, preservando o atraso real.</p>
        <h2>02 · Comprimentos de fabricação</h2><p>Informe o ramal mais curto e confira que todos os caminhos podem ser montados.
        Nos novos projetos, a referência é malha a malha: entre extremidades da blindagem, medida ao longo do cabo;
        na linha rígida, extremidades do condutor externo. Não inclui pontas expostas nem conectores.
        Terminações são consideradas iguais em todos os ramais. Diferenças de fase nos conectores exigem compensação medida.
        A tabela mostra diferenças após arredondar, em relação ao ramal anterior e a E1. Negativo significa mais curto.
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
        <p>O resultado mostra a potência média máxima de referência na frequência informada, a potência de pico
        de catálogo e a comparação com a entrada dos ramais e da linha comum. Pico não substitui a potência média;
        sem fator de crista, a condição de pico não é verificada. O PDF e a revisão SQLite preservam limites,
        amostras usadas, margens de potência, referência de medida e todas as diferenças de comprimento.</p>
        <p>O modo personalizado aceita VF informado. Atenuação desconhecida mantém perdas e eficiência indisponíveis.
        O campo VF medido substitui explicitamente o VF do catálogo. Conectores e descontinuidades requerem medição de fase.</p>
        <p>A conversão de canal usa centro geométrico de canais TV de 6 MHz (2–69, incluindo canais históricos).
        O deslocamento +1/7 MHz é opcional. Esta tabela não verifica disponibilidade, destinação ou autorização de uso.</p>
        <h2>05 · Diagrama e limites</h2><p>O modelo inicial é uma aproximação por dipolos verticais de meia onda.
        Campo total = campo do elemento × fator de arranjo. O padrão do dipolo é
        cos[(π/2) sen(e)] / cos(e), com nulos físicos em ±90° de elevação.
        A aba técnica mantém o fator de arranjo isolado; com espaçamento de 1 λ, ele pode ter máximos nas extremidades.
        Selecionar elemento isotrópico mostra somente esse fator, preservando projetos antigos.
        O modelo não inclui terreno, torre, acoplamento ou descasamento. Não é ganho em dBi nem diagrama medido.
        O pico do conjunto pode diferir do tilt da progressão. Lóbulos de grade remanescentes não são removidos.</p>
        <h2>06 · Cabos com divisor no centro</h2><p>Selecione <b>Divisor no centro — comprimentos por λg</b>.
        λ₀ = c/f define o espaçamento entre antenas; λg = VF × λ₀ define o comprimento elétrico do cabo.
        A planilha FM usa 1,25 λg no par central, 2,25 λg no próximo e 3,25 λg no par externo de seis antenas.
        O aplicativo admite 2 a 64 elementos. Em quantidade ímpar, a base do elemento central é 0,25 λg.</p>
        <p>Desmarque Aplicar tilt elétrico para usar fases iguais. Com tilt, a correção é proporcional à altura
        em relação ao divisor. A folga inclui curvas e deslocamentos além da distância vertical.
        Se faltar alcance, o cálculo acrescenta ondas inteiras, mantendo a fase na frequência calculada.
        A reserva opcional acrescenta λg inteiros a todos os ramais. Confira o detalhamento na aba Divisor central.</p>
        <p>Saídas do divisor são consideradas em fase, com terminações iguais. A equivalência por λg inteiro
        vale na frequência de projeto, não em toda a banda. A parcela λg/4 segue a planilha e não é um cálculo
        de casamento de impedância. O exemplo FM usa 105,3 MHz e VF 0,87; não altera o catálogo de fabricantes.</p>
        <h2>Referências</h2><ul><li>Plan1 das duas planilhas fornecidas (D5, D7, D9, D11, D15 e D17).</li>
        <li>Catálogo ADT-PY / Rating / CableRating.xml.</li>
        <li><a href="https://www.analog.com/en/resources/analog-dialogue/articles/phased-array-antenna-patterns-part1.html">Analog Devices: fator de arranjo</a></li>
        <li><a href="https://www.analog.com/en/resources/analog-dialogue/articles/phased-array-antenna-patterns-part2.html">Analog Devices: lóbulos de grade e atraso</a></li></ul>''')
        self.pages.addTab(browser, 'Ajuda')

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
        self.print_button.setEnabled(False)
        self.diagrams.invalidate()
        self.result_tabs.setEnabled(False)
        self.answer.setText('Clique em Calcular comprimentos para ver a orientação com os novos dados.')
        self.rating_summary.setText('Potência do material: recalcule para atualizar a verificação.')
        for value in self.metrics.values():
            value.setText('—')
        self.warnings.hide()
        self.secondary.setText('Resultados anteriores desativados até novo cálculo.')

    def update_spacing(self, *_):
        if self.loading:
            return
        self.spacing_factor.setEnabled(self.auto_spacing.isChecked())
        try:
            frequency = parse_decimal(self.fields['frequency_mhz'].text(), 'Frequência')
            length = wavelength_m(frequency, self.speed.currentData())*1000
        except ValueError:
            self.lambda_info.setText('Informe uma frequência válida para calcular λ.')
            return
        self.lambda_info.setText(f'1 λ no espaço livre = {fmt(length, 3)} mm')
        if self.auto_spacing.isChecked():
            self._setting_spacing = True
            try:
                self.fields['spacing_mm'].setText(f'{length*self.spacing_factor.value():.9f}'.rstrip('0').rstrip('.').replace('.', ','))
            finally:
                self._setting_spacing = False
        self.invalidate()

    def spacing_edited(self):
        if not self.loading and not getattr(self, '_setting_spacing', False):
            self.auto_spacing.setChecked(False)

    def toggle_tilt(self, checked):
        self.fields['tilt_deg'].setEnabled(checked)
        if not checked:
            self.fields['tilt_deg'].setText('0')
        self.invalidate()

    def feed_layout_changed(self, *_):
        central = self.feed_layout.currentData() == 'center'
        self.feed_form.setRowVisible(self.fields['shortest_branch_m'].parentWidget(), not central)
        self.feed_form.setRowVisible(self.fields['route_extra_m'].parentWidget(), central)
        self.feed_form.setRowVisible(self.reserve_wavelengths, central)
        self.feed_form.setRowVisible(self.center_help, central)
        self.toggle_technical(self.technical_button.isChecked())
        self.invalidate()

    def frequency_changed(self, *_):
        derived = self.frequency_mode.currentIndex() == 1
        self.channel.setEnabled(derived)
        self.ofdm_offset.setEnabled(derived)
        self.fields['frequency_mhz'].setEnabled(not derived)
        self.frequency_form.setRowVisible(self.channel, derived)
        self.frequency_form.setRowVisible(self.fields['frequency_mhz'].parentWidget(), not derived)
        self.frequency_form.setRowVisible(self.frequency_readout, derived)
        if derived:
            value = channel_frequency(self.channel.value()) + (1/7 if self.ofdm_offset.isChecked() else 0)
            self.fields['frequency_mhz'].setText(f'{value:.9f}'.rstrip('0').rstrip('.'))
            self.frequency_readout.setText(f'Frequência calculada: {fmt(value, 4)} MHz')
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
            self.material_help.setText('Modelo personalizado: informe as características nos ajustes avançados.')
            if not self.loading:
                self.advanced_button.setChecked(True)
        else:
            material = 'cabo' if self.kind.currentData() == 'cable' else 'linha rígida'
            self.material_help.setText(f'Escolha o modelo do {material}. As características são preenchidas automaticamente.'
                                      if material == 'cabo' else 'Escolha o modelo da linha rígida. As características são preenchidas automaticamente.')
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
            self.reveal_field(edit)
            raise

    def read_design(self):
        central = self.feed_layout.currentData() == 'center'
        inactive = {'shortest_branch_m'} if central else {'route_extra_m'}
        if not self.apply_tilt.isChecked():
            inactive.add('tilt_deg')
        values = {key: 0.0 if key in inactive else self.number(key, key == 'attenuation_db_100m') for key in self.fields}
        if self.model.currentText() != CUSTOM:
            cable = self.db.cable(self.model.currentText())
            self.attenuation_chart.subtitle = 'Pontos do catálogo e interpolação log-log'
            if cable.kind != self.kind.currentData():
                raise ValueError('Selecione um modelo do tipo de linha informado.')
            values['attenuation_db_100m'], _ = cable.at(values['frequency_mhz'])
            if not self.override_vf.isChecked():
                values['velocity_factor'] = cable.velocity_factor
        values['spacing_m'] = values.pop('spacing_mm') / 1000
        return Design(**values, elements=self.elements.value(), speed_m_s=self.speed.currentData(),
                      element_pattern=self.element_pattern.currentData(), length_reference=self.length_reference.currentData(),
                      feed_layout=self.feed_layout.currentData(), reserve_wavelengths=self.reserve_wavelengths.value() if central else 0)

    def input_payload(self, design):
        return dict(schema_version=2, design=asdict(design), kind=self.kind.currentData(),
                    model=self.model.currentText(), override_vf=self.override_vf.isChecked(),
                    frequency_mode=self.frequency_mode.currentIndex(), channel=self.channel.value(),
                    ofdm_offset=self.ofdm_offset.isChecked(), spacing_auto=self.auto_spacing.isChecked(),
                    spacing_factor=self.spacing_factor.value())

    def run_calculation(self):
        try:
            design = self.read_design()
            result = calculate(design)
            from .specification import line_specification
            cable = self.db.cable(self.model.currentText()) if self.model.currentText() != CUSTOM else None
            result = replace(result, line_specification=line_specification(
                result, cable, self.model.currentText(), self.kind.currentData(), self.db.catalog_hash))
        except ValueError as exc:
            self.invalidate()
            # Domain validation can also identify an invalid value inside a closed panel.
            prefixes = {'Fator de velocidade:': 'velocity_factor', 'Atenuação:': 'attenuation_db_100m',
                        'Perdas adicionais:': 'extra_loss_db', 'Potência de entrada:': 'input_power_w',
                        'Passo de corte:': 'cut_step_mm', 'Espaçamento:': 'spacing_mm', 'Tilt:': 'tilt_deg',
                        'Folga de percurso:': 'route_extra_m'}
            for prefix, key in prefixes.items():
                if str(exc).startswith(prefix):
                    self.reveal_field(self.fields[key])
            if str(exc) == 'Comprimentos fora dos limites da bancada.':
                for key, maximum in [('shortest_branch_m', 10000), ('common_feeder_m', 100000)]:
                    if not 0 <= self.number(key) <= maximum:
                        self.reveal_field(self.fields[key])
                        exc = ValueError(f'{self.field_labels[key]}: use de 0 a {maximum} m.')
                        break
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
        self.state.setText(f'Calculado · {d.elements} antenas · {fmt(d.frequency_mhz, 4)} MHz · inclinação {fmt(d.tilt_deg, 2)}°')
        for key, value, digits in [('delta', abs(r.delta_length_m)*1000, 3), ('phase', r.phase_step_deg, 3),
                                  ('efficiency', None if r.feed_efficiency is None else r.feed_efficiency*100, 2),
                                  ('power', r.total_power_w, 1)]:
            self.metrics[key].setText(fmt(value, digits))
        self.save_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.print_button.setEnabled(True)
        self.result_tabs.setEnabled(True)
        self.array.set_result(r, self.kind.currentData())
        self.lengths.set_result(r, self.kind.currentData())
        self.delta_caption.setText('Correção de tilt por nível' if r.center_feed else 'Diferença entre trechos vizinhos')
        if r.center_feed:
            self.answer.setText('Divisor no centro: use o comprimento de cada antena na tabela. '
                                + ('Sem tilt, comprimentos diferentes mantêm a mesma fase na frequência calculada.' if d.tilt_deg == 0 else
                                   'O tilt é aplicado à fase; os comprimentos incluem ondas inteiras para alcançar cada antena.'))
            self.central_summary.setText(f'Divisor a {fmt(r.center_feed.divider_height_m, 3)} m acima de E1 · '
                                         f'λg = {fmt(r.guided_wavelength_m*1000, 3)} mm\n'
                                         f'Total de ramais: {fmt(sum(e.length_m for e in r.elements), 3)} m · '
                                         f'Folga mínima por percurso: {fmt(d.route_extra_m, 3)} m')
            fill_table(self.central_table, [[f'E{b.number}', fmt(b.offset_from_divider_m*1000), fmt(b.minimum_route_m*1000),
                                            fmt(b.base_wavelengths, 2), fmt(b.tilt_correction_m*1000), b.added_wavelengths,
                                            fmt(e.length_m*1000)] for b, e in zip(r.center_feed.branches, r.elements)])
        elif d.tilt_deg == 0:
            self.answer.setText('Sem inclinação: use o mesmo comprimento em todas as antenas. Confira os valores na tabela.')
        else:
            direction, length = ('baixo', 'menores') if d.tilt_deg > 0 else ('cima', 'maiores')
            self.answer.setText(f'Para inclinar {fmt(abs(d.tilt_deg), 2)}° para {direction}, os trechos ficam {length} '
                                'conforme se sobe na torre. Use os comprimentos da tabela, já ajustados ao passo de corte.')
        self.length_title.setText('Comprimento de cada cabo' if self.kind.currentData() == 'cable' else 'Comprimento de cada linha')
        shield = d.length_reference == 'shield_edges'
        reference = ('Malha a malha' if self.kind.currentData() == 'cable' else 'Condutor externo') if shield else 'Planos de referência'
        self.simple_table.setHorizontalHeaderLabels(['Antena', reference+'\n(mm)', 'Dif. anterior\n(mm)', 'Dif. E1\n(mm)'])
        self.measure_note.setText(reference + ': diferença negativa = mais curto. E1 é a antena inferior. '
                                 'Pontas expostas e conectores ficam fora da medida. Terminações devem ser iguais.' if shield else
                                 'Referência elétrica de revisão antiga. Selecione malha a malha nos ajustes para uma nova especificação de montagem.')
        fill_table(self.simple_table, [[f'E{e.number}', fmt(e.length_m*1000, 3), fmt(e.delta_previous_m*1000 if e.delta_previous_m is not None else None),
                                      fmt(e.delta_e1_m*1000)] for e in r.elements])
        spec = r.line_specification
        loads = f'Cada ramal recebe {fmt(spec.branch_input_w, 1)} W'
        if spec.common_input_w is not None:
            loads += f'; linha comum recebe {fmt(spec.common_input_w, 1)} W'
        self.rating_summary.setText(
            f'Potência média máxima: {fmt(spec.average_power_w, 1)} W por trecho a {fmt(d.frequency_mhz, 2)} MHz (catálogo).\n'
            f'{loads}. Verificação média: {spec.status}. Pico de catálogo: {fmt(spec.peak_power_w/1000, 1)} kW.'
            if spec.average_power_w is not None else 'Potência máxima: não informada para este modelo personalizado.')
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
            if spec.status == 'excede referência':
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
        self.diagrams.set_result(r)
        self.report_preview.setHtml(report_html(r, self.model.currentText(), self.project_name.text()))
        self.secondary.setText(f'λ₀ {fmt(r.wavelength_m*1000)} mm  ·  λg {fmt(r.guided_wavelength_m*1000)} mm  ·  '
                               f'Coerência no alvo {fmt(r.coherence_efficiency*100, 3)}%  ·  '
                               f'Tilt da progressão após corte {fmt(r.fitted_tilt_deg, 4)}°  ·  Perda {fmt(r.equivalent_loss_db)} dB')
        self.update_warnings()
        self.statusBar().showMessage('Cálculo concluído · Ctrl+S para salvar · Ctrl+P para imprimir · veja a aba Diagramas')

    def load_example(self, kind):
        self.loading = True
        self.feed_layout.setCurrentIndex(self.feed_layout.findData('progressive'))
        self.apply_tilt.setChecked(True)
        self.auto_spacing.setChecked(False)
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
        self.update_spacing()
        self.update_line_properties()
        self.pages.setCurrentIndex(0)
        self.run_calculation()
        self.state.setText('Exemplo da planilha carregado · confira os dados antes de usar na sua instalação.')

    def load_central_example(self):
        self.loading = True
        try:
            self.frequency_mode.setCurrentIndex(0)
            self.kind.setCurrentIndex(0)
            self.model.setCurrentText(CUSTOM)
            self.override_vf.setChecked(False)
            self.feed_layout.setCurrentIndex(self.feed_layout.findData('center'))
            self.elements.setValue(6)
            self.speed.setCurrentIndex(0)
            self.auto_spacing.setChecked(True)
            self.spacing_factor.setValue(1)
            self.apply_tilt.setChecked(False)
            self.reserve_wavelengths.setValue(0)
            for key, value in dict(frequency_mhz=105.3, velocity_factor=.87, tilt_deg=0,
                                   attenuation_db_100m='', route_extra_m=0, shortest_branch_m=0,
                                   common_feeder_m=0, extra_loss_db=0, input_power_w=1000, cut_step_mm=0).items():
                self.fields[key].setText(str(value))
            self.length_reference.setCurrentIndex(self.length_reference.findData('shield_edges'))
            self.project_name.setText('FM — divisor central — referência ODS')
        finally:
            self.loading = False
        self.update_spacing()
        self.update_line_properties()
        self.pages.setCurrentIndex(0)
        self.run_calculation()
        self.state.setText('Exemplo ODS: 105,3 MHz · VF 0,87 · 6 antenas · sem tilt · corte ideal.')

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
                    snapshot(self.result, self.model.currentText(), self.db.catalog_hash, self.diagrams.view_range))
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
            bounds = project['snapshot'].get('diagram', {}).get('elevation_range_deg', [-90, 90])
            if isinstance(bounds, list) and len(bounds) == 2:
                self.diagrams.set_range(*bounds)
        except (ValueError, KeyError, TypeError, sqlite3.Error):
            QMessageBox.warning(self, 'Revisão não carregada', 'Dados da revisão inválidos ou incompatíveis com esta versão.')

    def restore_payload(self, payload, title):
        if payload.get('schema_version') not in (1, 2):
            raise ValueError('Versão de projeto incompatível.')
        design = Design(**payload['design'])
        design.validate()
        if payload.get('kind') not in ('cable', 'rigid'):
            raise ValueError('Tipo de linha inválido.')
        if payload['model'] != CUSTOM:
            self.db.cable(payload['model'])
        self.loading = True
        try:
            factor = payload.get('spacing_factor', 1.0)
            if not isinstance(factor, (int, float)) or isinstance(factor, bool) or not .01 <= factor <= 20:
                raise ValueError('Múltiplo de λ inválido.')
            self.spacing_factor.setValue(factor)
            self.auto_spacing.setChecked(bool(payload.get('spacing_auto', False)))
            self.feed_layout.setCurrentIndex(self.feed_layout.findData(design.feed_layout))
            self.reserve_wavelengths.setValue(design.reserve_wavelengths)
            self.apply_tilt.setChecked(design.tilt_deg != 0)
            self.kind.setCurrentIndex(0 if payload['kind'] == 'cable' else 1)
            self.model.setCurrentText(payload['model'])
            self.override_vf.setChecked(payload['override_vf'])
            self.frequency_mode.setCurrentIndex(payload['frequency_mode'])
            self.channel.setValue(payload['channel'])
            self.ofdm_offset.setChecked(payload.get('ofdm_offset', False))
            self.elements.setValue(design.elements)
            self.element_pattern.setCurrentIndex(self.element_pattern.findData(design.element_pattern))
            self.length_reference.setCurrentIndex(self.length_reference.findData(design.length_reference))
            for key, value in asdict(design).items():
                if key == 'spacing_m':
                    self.fields['spacing_mm'].setText(str(value*1000))
                elif key in self.fields:
                    self.fields[key].setText('' if value is None else str(value))
            self.speed.setCurrentIndex(0 if design.speed_m_s == C_WORKSHEET else 1)
            self.project_name.setText(title)
        finally:
            self.loading = False
        self.update_spacing()
        # Catalog changes are intentionally applied only on an explicit calculation.
        self.invalidate()
        self.update_advanced_summary()
        if payload['model'] == CUSTOM or payload['override_vf']:
            self.advanced_button.setChecked(True)
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
                                  **snapshot(self.result, self.model.currentText(), self.db.catalog_hash, self.diagrams.view_range)})
            else:
                self.write_pdf(path)
        except (OSError, ValueError):
            QMessageBox.warning(self, 'Exportação não concluída', 'Não foi possível gravar o arquivo. Verifique a pasta e se ele está aberto em outro programa.')
            return
        self.statusBar().showMessage(f'Exportado: {path.name}')

    def write_pdf(self, path):
        from .printing import write_report_pdf
        return write_report_pdf(path, self.result, self.model.currentText(), self.project_name.text(),
                                self.kind.currentData(), self.db.catalog_hash, self.calculated_payload,
                                self.diagrams.view_range)

    def prepare_print(self):
        if self.result is None:
            self.statusBar().showMessage('Calcule os comprimentos antes de imprimir.')
            return False
        from PySide6.QtCore import QStandardPaths
        from .printing import PrintPreview
        folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)) / 'EFTX Tilt' / 'Relatorios'
        try:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / ('Tilt_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.pdf')
            self.write_pdf(path)
            preview = PrintPreview(path, self)
        except (OSError, ValueError):
            QMessageBox.warning(self, 'Impressão não preparada',
                                'Não foi possível gerar ou abrir o PDF. Verifique a pasta Documentos e as permissões de escrita.')
            return False
        self.statusBar().showMessage(f'PDF salvo: {path}')
        preview.exec()
        preview.deleteLater()
        return True
