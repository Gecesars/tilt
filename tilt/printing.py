"""Detailed PDF and native print preview of the exact saved PDF pages."""
from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QImage, QPageLayout, QPageSize, QPainter, QTextDocument
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter, QPrinterInfo, QPrintPreviewWidget
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout

from . import __version__
from .diagrams import pattern_series
from .engineering import ENGINE_VERSION, ELEMENT_PATTERNS, vertical_patterns
from .reports import fmt, report_html
from .visuals import ArrayIllustration, LengthIllustration, FabricationIllustration, SeriesChart

ASSETS = Path(__file__).parent / 'assets'


def configure_page(printer):
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Unit.Millimeter)


def add_figure(document, name, widget, width, height):
    """Fixed geometry and 2x pixels, independent of the visible desktop window."""
    widget.resize(width, height)
    image = QImage(width*2, height*2, QImage.Format.Format_ARGB32)
    image.setDevicePixelRatio(2)
    image.fill(Qt.GlobalColor.white)
    widget.render(image)
    document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), image)


def report_document(result, model, title, kind, catalog_hash, context=None, view_range=(-90.0, 90.0)):
    context = context or {}
    document = QTextDocument()
    document.setDefaultFont(QFont('Segoe UI', 10))
    document.addResource(QTextDocument.ResourceType.ImageResource, QUrl('eftx-logo'),
                         QImage(str(ASSETS/'eftx_logo.jpeg')))
    html = report_html(result, model, title)
    generated = datetime.now().astimezone().strftime('%d/%m/%Y %H:%M:%S %z')
    mode = 'Automático: 1 λ no espaço livre' if context.get('spacing_auto') else 'Distância informada pelo usuário'
    frequency = (f"Canal TV {context.get('channel')}" if context.get('frequency_mode') == 1 else 'Frequência em MHz')
    if context.get('frequency_mode') == 1 and context.get('ofdm_offset'):
        frequency += ' + 1/7 MHz'
    material = 'Cabo coaxial' if kind == 'cable' else 'Linha rígida'
    header = (f'<img src="eftx-logo" width="135" height="89">'
              f'<p class="note">Emitido em {generated} | Aplicativo {__version__} | Motor RF {ENGINE_VERSION}<br>'
              f'{material} | Entrada: {escape(frequency)}<br>{escape(mode)}</p>')
    html = html.replace('<body>', '<body>'+header)
    html = html.replace('<h2>Material e capacidade de potência</h2>',
                        '<h2 style="page-break-before:always">Material e capacidade de potência</h2>')
    html = html.replace('<h2>Comprimentos entre planos de referência</h2>',
                        '<h2 style="page-break-before:always">Comprimentos entre planos de referência</h2>')
    # Separate technical memory from long manufacturing tables, including N=64.
    html = html.replace('<h2>Memória de cálculo</h2>',
                        '<h2 style="page-break-before:always">Memória de cálculo e verificações</h2>')
    figures = []
    automatic_focus = view_range == (-90.0, 90.0)
    detail_range = (max(-90, -result.design.tilt_deg-10), min(90, -result.design.tilt_deg+10)) if automatic_focus else view_range
    detail_caption = 'Ampliação do tilt (automática)' if automatic_focus else 'Faixa vertical selecionada'
    for index, (caption, bounds) in enumerate([('Faixa vertical completa', (-90.0, 90.0)),
                                               (detail_caption, detail_range)]):
        data = vertical_patterns(result, *bounds)
        chart = SeriesChart(caption, f'Elevação de {fmt(bounds[0], 2)}° a {fmt(bounds[1], 2)}°')
        chart.dashed_series = {'Comprimentos ideais', 'Sem tilt'}
        chart.set_data(pattern_series(data), 'Elevação (°) - negativo = abaixo do horizonte',
                       'Campo relativo (dB)', bounds, (-60, 0), -result.design.tilt_deg)
        name = f'vertical-{index}'
        add_figure(document, name, chart, 680, 390)
        figures.append(f'<p><img src="{name}" width="550" height="315"></p>')
        if data.sampling_limited:
            figures.append('<p>Resolução limitada: reduza a faixa para examinar picos e nulos estreitos.</p>')
    diagram_html = ('<h2 style="page-break-before:always">Diagramas verticais</h2>'
                    f'<p><b>{escape(ELEMENT_PATTERNS[result.design.element_pattern])}</b>.<br>'
                    'Comparação: após o corte, comprimentos ideais e fases zeradas (sem tilt). '
                    'A linha vertical marca a inclinação solicitada.<br>'
                    f'{detail_caption}: {fmt(detail_range[0])}° a {fmt(detail_range[1])}°.</p>' + ''.join(figures) +
                    '<p class="note">Referência: soma coerente das amplitudes de cada curva. '
                    'O recorte angular não renormaliza as curvas. Piso de exibição: -60 dB. '
                    'Não representa ganho em dBi nem diagrama medido de uma antena.</p>')
    array = ArrayIllustration()
    array.set_result(result, kind)
    add_figure(document, 'array', array, 680, 480)
    lengths = LengthIllustration()
    lengths.set_result(result, kind)
    add_figure(document, 'lengths', lengths, 680, 290)
    assembly_html = ('<h2 style="page-break-before:always">Esquema de alimentação e montagem</h2>'
                     '<p>Ilustração sem escala. E1 é a antena inferior. Use a tabela completa de comprimentos.</p>'
                     '<p><img src="array" width="550" height="388"></p>'
                     '<p><img src="lengths" width="550" height="235"></p>'
                     '<p class="note">Confira o percurso físico, os planos dos conectores e a fase em bancada.</p>'
                     f'<p class="note">Catálogo SHA-256:<br>{escape(catalog_hash)}</p>')
    fabrication_html = ''
    for offset in range(0, len(result.elements), 8):
        elements = result.elements[offset:offset+8]
        drawing = FabricationIllustration(result, kind, elements)
        height = 85+80*len(elements)
        name = f'fabrication-{offset}'
        add_figure(document, name, drawing, 680, height)
        fabrication_html += (f'<h2 style="page-break-before:always">Detalhes de cada trecho · E{elements[0].number} a E{elements[-1].number}</h2>'
                             '<p>Extremidades tracejadas delimitam a medida. A sobra do condutor central é apenas ilustrativa; '
                             'o preparo de cada conector deve seguir seu desenho de montagem. Diferença negativa = mais curto.</p>'
                             f'<p><img src="{name}" width="550" height="{height*550//680}"></p>')
    document.setHtml(html.replace('</body>', diagram_html+assembly_html+fabrication_html+'</body>'))
    return document


def write_report_pdf(path, result, model, title, kind, catalog_hash, context=None, view_range=(-90.0, 90.0)):
    if result is None:
        raise ValueError('Calcule os comprimentos antes de gerar o relatório.')
    path = Path(path)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(path))
    printer.setDocName(title)
    printer.setCreator(f'EFTX Tilt {__version__}')
    configure_page(printer)
    # QTextDocument.print_ adds its own 20 mm margins and page numbers. Starting
    # at the paper origin avoids adding the printer's margins a second time.
    printer.setFullPage(True)
    document = report_document(result, model, title, kind, catalog_hash, context, view_range)
    document.print_(printer)
    if not path.is_file() or path.stat().st_size < 100 or printer.printerState() == QPrinter.PrinterState.Error:
        raise OSError('Não foi possível gravar o PDF.')
    return path


def load_pdf(path, parent=None):
    document = QPdfDocument(parent)
    if document.load(str(path)) != QPdfDocument.Error.None_ or document.pageCount() == 0:
        raise ValueError('Não foi possível abrir o PDF gerado para impressão.')
    return document


def paint_pdf(document, printer):
    """Paint saved pages, preserving aspect ratio and selected page range/order.

    Only a preview or an explicitly accepted native print dialog calls this.
    Render one page at a time, bounded to 200 dpi to keep memory predictable.
    """
    first = max(1, printer.fromPage() or 1)
    last = min(document.pageCount(), printer.toPage() or document.pageCount())
    if first > last:
        raise ValueError('Intervalo de páginas inválido.')
    pages = list(range(first-1, last))
    if printer.pageOrder() == QPrinter.PageOrder.LastPageFirst:
        pages.reverse()
    if not printer.supportsMultipleCopies() and printer.copyCount() > 1:
        copies = printer.copyCount()
        pages = pages*copies if printer.collateCopies() else [p for p in pages for _ in range(copies)]
    printer.setFullPage(True)
    painter = QPainter()
    if not painter.begin(printer):
        raise OSError('A impressora não iniciou o trabalho.')
    try:
        for number, index in enumerate(pages):
            if number and not printer.newPage():
                raise OSError('A impressora não aceitou a próxima página.')
            points = document.pagePointSize(index)
            dpi = min(200, printer.resolution())
            image = document.render(index, QSize(max(1, round(points.width()*dpi/72)),
                                                  max(1, round(points.height()*dpi/72))))
            if image.isNull():
                raise OSError('Não foi possível renderizar uma página do PDF.')
            page = QRectF(printer.pageRect(QPrinter.Unit.DevicePixel))
            factor = min(page.width()/image.width(), page.height()/image.height())
            width, height = image.width()*factor, image.height()*factor
            target = QRectF(page.x()+(page.width()-width)/2, page.y()+(page.height()-height)/2, width, height)
            painter.drawImage(target, image)
    finally:
        ended = painter.end()
    if not ended or printer.printerState() == QPrinter.PrinterState.Error:
        raise OSError('A impressora informou uma falha no trabalho.')


class PrintPreview(QDialog):
    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.setWindowTitle('EFTX - PDF e prévia de impressão')
        available = self.screen().availableGeometry()
        self.resize(min(1050, available.width()-50), min(820, available.height()-70))
        self.document = load_pdf(self.pdf_path, self)
        self.finished.connect(self.document.close)
        default = QPrinterInfo.defaultPrinter()
        self.printer = (QPrinter(default, QPrinter.PrinterMode.HighResolution) if not default.isNull()
                        else QPrinter(QPrinter.PrinterMode.HighResolution))
        if default.isNull():
            self.printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        configure_page(self.printer)
        self.printer.setDocName(self.pdf_path.stem)
        layout = QVBoxLayout(self)
        info = QLabel(f'PDF salvo: {self.pdf_path}\nImpressora padrão: '
                      + (default.printerName() if not default.isNull() else 'nenhuma configurada'))
        info.setTextFormat(Qt.TextFormat.PlainText)
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(info)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setObjectName('Error')
        self.error.hide()
        layout.addWidget(self.error)
        controls = QHBoxLayout()
        controls.addWidget(QLabel('Página'))
        self.page = QSpinBox()
        self.page.setRange(1, self.document.pageCount())
        controls.addWidget(self.page)
        controls.addWidget(QLabel(f'de {self.document.pageCount()}'))
        fit = QPushButton('Ajustar página')
        fit.clicked.connect(lambda: self.preview.fitInView())
        controls.addWidget(fit)
        width = QPushButton('Largura da página')
        width.clicked.connect(lambda: self.preview.fitToWidth())
        controls.addWidget(width)
        controls.addStretch()
        open_pdf = QPushButton('Abrir PDF')
        open_pdf.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.pdf_path))))
        controls.addWidget(open_pdf)
        self.print_button = QPushButton('Imprimir…')
        self.print_button.setObjectName('Primary')
        self.print_button.setEnabled(bool(QPrinterInfo.availablePrinterNames()))
        self.print_button.clicked.connect(self.submit_print)
        controls.addWidget(self.print_button)
        close = QPushButton('Fechar')
        close.clicked.connect(self.reject)
        controls.addWidget(close)
        layout.addLayout(controls)
        self.preview = QPrintPreviewWidget(self.printer, self)
        self.preview.paintRequested.connect(self.paint_preview)
        self.page.valueChanged.connect(self.preview.setCurrentPage)
        self.preview.previewChanged.connect(self.sync_page)
        layout.addWidget(self.preview, 1)
        layout.addWidget(QLabel('Confira o PDF. O trabalho só será enviado ao confirmar no diálogo de impressão.'))

    def sync_page(self):
        self.page.blockSignals(True)
        self.page.setValue(max(1, self.preview.currentPage()))
        self.page.blockSignals(False)

    def paint_preview(self, printer):
        try:
            paint_pdf(self.document, printer)
        except (OSError, ValueError) as exc:
            self.error.setText(str(exc))
            self.error.show()

    def submit_print(self):
        dialog = QPrintDialog(self.printer, self)
        dialog.setWindowTitle('Imprimir relatório EFTX')
        dialog.setMinMax(1, self.document.pageCount())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        try:
            paint_pdf(self.document, self.printer)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Impressão não concluída', str(exc))
            return False
        self.accept()
        return True
