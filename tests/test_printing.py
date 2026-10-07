from pathlib import Path

import pytest
from PySide6.QtCore import QStandardPaths, QSize
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from PySide6.QtWidgets import QDialog

from tilt import printing


def pdf_text(document):
    return '\n'.join(document.getAllText(i).text() for i in range(document.pageCount()))


def test_detailed_pdf_has_inputs_results_figures_selected_range_and_traceability(window, tmp_path):
    window.project_name.setText('Teste <&> RF')
    window.diagrams.set_range(-12, 8)
    path = window.write_pdf(tmp_path/'report.pdf')
    doc = printing.load_pdf(path)
    try:
        assert doc.pageCount() == 7
        text = pdf_text(doc)
        for phrase in ['Teste <&> RF', '623,000', '481,541', 'E1', 'E4', 'Memória de cálculo',
                       'Diagramas verticais', '-12,000° a 8,000°', 'Esquema de alimentação', window.db.catalog_hash,
                       'Malha a malha', 'Potência média máxima', 'Potência de pico', 'Dif. anterior', 'Dif. E1',
                       'Dipolo vertical de meia onda', 'Detalhes de cada trecho']:
            assert phrase in text
        for value in ['1519,819', '38000,000', '3044,400', '-14,800', '-44,400']:
            assert value in text  # Default 623 MHz LCF12-50 rating and actual rounded fabrication.
        assert doc.pagePointSize(0).width() == pytest.approx(595, abs=1)
        assert not doc.render(3, QSize(600, 850)).isNull()
    finally:
        doc.close()


def test_long_pdf_contains_every_element_and_unknown_efficiency(window, tmp_path):
    from tilt.window import CUSTOM
    window.model.setCurrentText(CUSTOM)
    window.elements.setValue(64)
    assert window.run_calculation()
    path = window.write_pdf(tmp_path/'64_elements.pdf')
    doc = printing.load_pdf(path)
    try:
        text = pdf_text(doc)
        assert 15 <= doc.pageCount() <= 22  # Eight fabrication drawings, plus long tables and calculation.
        for n in range(1, 65):
            assert f'E{n}' in text
        assert 'n/d' in text
        assert 'Atenuação não informada' in text
    finally:
        doc.close()


def test_printing_uses_saved_pdf_page_range_and_reverse_order(window, tmp_path):
    path = window.write_pdf(tmp_path/'original.pdf')
    doc = printing.load_pdf(path)
    rendered = []
    class TrackedDocument:
        pageCount = doc.pageCount
        pagePointSize = doc.pagePointSize
        def render(self, page, size):
            rendered.append(page)
            return doc.render(page, size)
    output = tmp_path/'print_to_file.pdf'
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(output))
    printer.setResolution(96)
    printing.configure_page(printer)
    printer.setFromTo(2, 3)
    printer.setPageOrder(QPrinter.PageOrder.LastPageFirst)
    printing.paint_pdf(TrackedDocument(), printer)
    assert rendered == [2, 1]
    printed = printing.load_pdf(output)
    assert printed.pageCount() == 2
    printed.close()
    doc.close()


def test_cancel_native_print_dialog_never_submits_pages(window, tmp_path, monkeypatch):
    path = window.write_pdf(tmp_path/'preview.pdf')
    preview = printing.PrintPreview(path, window)
    class CancelDialog:
        def __init__(self, *args): pass
        def setWindowTitle(self, *args): pass
        def setMinMax(self, *args): pass
        def exec(self): return QDialog.DialogCode.Rejected
        def deleteLater(self): pass
    monkeypatch.setattr(printing, 'QPrintDialog', CancelDialog)
    calls = []
    monkeypatch.setattr(printing, 'paint_pdf', lambda *args: calls.append(args))
    assert not preview.submit_print()
    assert not calls
    default = QPrinterInfo.defaultPrinter()
    if not default.isNull():
        assert preview.printer.printerName() == default.printerName()
    preview.document.close()
    preview.close()


def test_preview_without_printer_retains_pdf_and_disables_submission(window, tmp_path, monkeypatch):
    path = window.write_pdf(tmp_path/'no_printer.pdf')
    monkeypatch.setattr(QPrinterInfo, 'defaultPrinter', lambda: QPrinterInfo())
    monkeypatch.setattr(QPrinterInfo, 'availablePrinterNames', lambda: [])
    preview = printing.PrintPreview(path, window)
    assert not preview.print_button.isEnabled()
    assert preview.document.pageCount() == 7
    assert path.is_file()
    preview.document.close()
    preview.close()


def test_prepare_print_saves_pdf_before_preview_and_blocks_stale_results(window, tmp_path, monkeypatch):
    captured = []
    class PreviewStub:
        def __init__(self, path, parent):
            assert path.is_file()
            captured.append(path)
        def exec(self): return QDialog.DialogCode.Rejected
        def deleteLater(self): pass
    monkeypatch.setattr(printing, 'PrintPreview', PreviewStub)
    monkeypatch.setattr(QStandardPaths, 'writableLocation', lambda _: str(tmp_path))
    assert window.prepare_print()
    assert captured[0].parent == tmp_path/'EFTX Tilt'/'Relatorios'
    window.fields['tilt_deg'].setText('3')
    assert not window.prepare_print()
    assert not window.print_button.isEnabled()
    assert len(captured) == 1


def test_prepare_print_handles_file_failure_without_opening_preview(window, tmp_path, monkeypatch):
    def failed(*args): raise OSError('disk failure')
    monkeypatch.setattr(window, 'write_pdf', failed)
    monkeypatch.setattr(QStandardPaths, 'writableLocation', lambda _: str(tmp_path))
    warnings = []
    monkeypatch.setattr('tilt.window.QMessageBox.warning', lambda *args: warnings.append(args))
    assert not window.prepare_print()
    assert len(warnings) == 1


def test_confirmed_print_uses_selected_pdf_output_without_physical_printer(window, tmp_path, monkeypatch):
    path = window.write_pdf(tmp_path/'source.pdf')
    output = tmp_path/'confirmed.pdf'
    preview = printing.PrintPreview(path, window)
    class AcceptedDialog:
        def __init__(self, printer, parent): self.printer = printer
        def setWindowTitle(self, *args): pass
        def setMinMax(self, *args): pass
        def exec(self):
            self.printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            self.printer.setOutputFileName(str(output))
            self.printer.setResolution(96)
            self.printer.setFromTo(1, 1)
            self.printer.setCopyCount(2)
            return QDialog.DialogCode.Accepted
    monkeypatch.setattr(printing, 'QPrintDialog', AcceptedDialog)
    assert preview.submit_print()
    printed = printing.load_pdf(output)
    assert printed.pageCount() == 2
    printed.close()
    preview.close()
