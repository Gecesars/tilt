"""Exercise the actual Qt windows and capture reproducible visual evidence."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from tilt.storage import Database
from tilt.window import MainWindow

app = QApplication([])
app.setStyle('Fusion')
# Qt's offscreen Windows plugin does not enumerate system fonts.
if not QFontDatabase.families():
    for font in ('segoeui.ttf', 'segoeuib.ttf', 'segoeuii.ttf'):
        QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / font))
db = Database(':memory:')
window = MainWindow(db)
window.resize(1540, 1000)
window.show()
app.processEvents()
out = Path(__file__).resolve().parents[1] / '.artifacts'
out.mkdir(exist_ok=True)


def capture(name):
    app.processEvents()
    assert window.grab().save(str(out / (name+'.png')))


capture('bancada_cabos')
window.write_pdf(out/'relatorio_cabos.pdf')
window.pages.setCurrentWidget(window.diagrams)
capture('dipolo_faixa_completa')
window.diagrams.tabs.setCurrentIndex(2)
capture('fator_arranjo_comparacao')
window.diagrams.tabs.setCurrentIndex(0)
window.pages.setCurrentIndex(0)
window.resize(1366, 768)
capture('simples_1366')
window.resize(1540, 1000)
window.technical_button.setChecked(True)
capture('detalhes_tecnicos')
window.result_tabs.setCurrentIndex(1)
capture('comprimentos')
window.result_tabs.setCurrentIndex(2)
capture('perdas')
window.pages.setCurrentIndex(2)
capture('catalogo')
window.pages.setCurrentIndex(0)
window.result_tabs.setCurrentIndex(0)
window.technical_button.setChecked(False)
window.kind_buttons.button(1).click()
window.fields['frequency_mhz'].setText('107,7')
window.fields['spacing_mm'].setText('1385,793872')
window.fields['tilt_deg'].setText('5')
assert window.run_calculation()
capture('bancada_rigida')
window.write_pdf(out/'relatorio_rigida.pdf')
window.resize(1100, 760)
capture('bancada_compacta')
window.resize(1540, 1000)
window.advanced_button.setChecked(True)
window.input_scroll.ensureWidgetVisible(window.fields['velocity_factor'])
capture('ajustes_avancados')
window.model.showPopup()
app.processEvents()
assert window.model.view().window().grab().save(str(out/'lista_modelos.png'))
window.model.hidePopup()
window.pages.setCurrentWidget(window.diagrams)
window.diagrams.set_range(-15, 5)
capture('diagramas_verticais')
window.diagrams.tabs.setCurrentIndex(1)
capture('diagramas_lineares')
from tilt.printing import PrintPreview
preview = PrintPreview(out/'relatorio_rigida.pdf', window)
preview.show()
app.processEvents()
assert preview.grab().save(str(out/'previa_impressao.png'))
preview.close()
window.elements.setValue(64)
assert window.run_calculation()
window.write_pdf(out/'stress64.pdf')
window.close()
db.close()
print('Capturas: cabos, rígida, comprimentos, perdas, catálogo e diagramas. PDFs: cabo, rígida e 64 elementos.')
