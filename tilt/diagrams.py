"""Independent vertical diagram page with view-only angular controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget

from .engineering import ELEMENT_PATTERNS, parse_decimal, vertical_patterns
from .reports import fmt
from .visuals import BLUE, TEAL, SeriesChart


def pattern_series(data, linear=False):
    def values(db):
        return [10**(v/20) for v in db] if linear else db
    return [(name, data.angles, values(db), color) for name, db, color in (
        ('Após o corte', data.actual_db, BLUE),
        ('Comprimentos ideais', data.ideal_db, TEAL),
        ('Sem tilt', data.untilted_db, '#657b96'),
    )]


class DiagramPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self.view_range = (-90.0, 90.0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        title = QLabel('Diagramas verticais')
        title.setObjectName('AppTitle')
        layout.addWidget(title)
        note = QLabel('Eixo X = elevação: 0° é o horizonte; valores negativos apontam para baixo. Tilt positivo aparece à esquerda de 0°.')
        note.setWordWrap(True)
        layout.addWidget(note)
        controls = QHBoxLayout()
        self.start = QLineEdit('-90')
        self.stop = QLineEdit('90')
        for caption, field in [('Início (°)', self.start), ('Fim (°)', self.stop)]:
            label = QLabel(caption)
            label.setBuddy(field)
            controls.addWidget(label)
            field.setMaximumWidth(110)
            field.setAccessibleName(caption)
            controls.addWidget(field)
            field.returnPressed.connect(self.apply_range)
        self.apply_button = QPushButton('Aplicar faixa')
        self.apply_button.setObjectName('Primary')
        self.apply_button.clicked.connect(self.apply_range)
        controls.addWidget(self.apply_button)
        full = QPushButton('Faixa completa')
        full.clicked.connect(lambda: self.set_range(-90, 90))
        controls.addWidget(full)
        focus = QPushButton('Focar no tilt')
        focus.clicked.connect(self.focus_tilt)
        controls.addWidget(focus)
        controls.addStretch()
        layout.addLayout(controls)
        self.error = QLabel()
        self.error.setObjectName('Error')
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        self.summary = QLabel('Calcule os comprimentos para visualizar os diagramas.')
        self.summary.setWordWrap(True)
        self.summary.setObjectName('State')
        layout.addWidget(self.summary)
        self.tabs = QTabWidget()
        self.db_chart = SeriesChart('Diagrama vertical completo', 'Elemento × fator de arranjo')
        self.linear_chart = SeriesChart('Campo relativo', 'Mesma referência de amplitude em todas as curvas')
        self.factor_chart = SeriesChart('Fator de arranjo isolado', 'Não inclui a resposta angular da antena')
        for chart in (self.db_chart, self.linear_chart, self.factor_chart):
            chart.dashed_series = {'Comprimentos ideais', 'Sem tilt'}
        self.tabs.addTab(self.db_chart, 'Em decibéis (dB)')
        self.tabs.addTab(self.linear_chart, 'Campo relativo (0 a 1)')
        self.tabs.addTab(self.factor_chart, 'Fator de arranjo (técnico)')
        layout.addWidget(self.tabs, 1)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.setObjectName('Notice')
        self.notice.hide()
        layout.addWidget(self.notice)
        self.footer = footer = QLabel(''
                        'Referência: soma coerente das amplitudes de cada curva; o zoom não altera a normalização. '
                        'A curva sem tilt mantém as amplitudes e zera as fases. Piso visual: −60 dB.')
        footer.setWordWrap(True)
        footer.setObjectName('Subtitle')
        layout.addWidget(footer)

    def invalidate(self):
        self.result = None
        self.db_chart.set_data([])
        self.linear_chart.set_data([])
        self.factor_chart.set_data([])
        self.summary.setText('Entradas alteradas. Volte a Calcular e atualize os comprimentos.')
        self.notice.hide()

    def set_result(self, result):
        self.result = result
        self.render()

    def apply_range(self):
        try:
            start = parse_decimal(self.start.text(), 'Início do eixo X')
            stop = parse_decimal(self.stop.text(), 'Fim do eixo X')
            if not -90 <= start < stop <= 90:
                raise ValueError('Informe início menor que fim, entre −90° e +90°.')
        except ValueError as exc:
            self.error.setText(str(exc))
            self.error.show()
            return False
        self.view_range = (start, stop)
        self.error.hide()
        self.render()
        return True

    def set_range(self, start, stop):
        self.start.setText(fmt(start, 3))
        self.stop.setText(fmt(stop, 3))
        self.apply_range()

    def focus_tilt(self):
        if self.result is not None:
            center = -self.result.design.tilt_deg
            self.set_range(max(-90, center-10), min(90, center+10))

    def render(self):
        if self.result is None:
            return
        r = self.result
        data = vertical_patterns(r, *self.view_range)
        self.db_chart.title = ('Diagrama vertical completo' if r.design.element_pattern != 'isotropic' else 'Fator de arranjo — elemento isotrópico')
        self.footer.setText(ELEMENT_PATTERNS[r.design.element_pattern] + '. Diagrama analítico; sem torre, solo ou acoplamento. '
                            '0 dB = soma coerente das amplitudes com máximo do elemento; zoom não renormaliza. '
                            'Piso visual −60 dB. A direção do pico resultante pode diferir do tilt da progressão.')
        for chart, linear in [(self.db_chart, False), (self.linear_chart, True)]:
            chart.set_data(pattern_series(data, linear), 'Elevação (°)',
                           'Campo relativo' if linear else 'Campo relativo (dB)', self.view_range,
                           (0, 1.05) if linear else (-60, 0), -r.design.tilt_deg)
        factor = vertical_patterns(r, *self.view_range, factor_only=True)
        self.factor_chart.set_data(pattern_series(factor), 'Elevação (°)', 'Campo relativo (dB)',
                                   self.view_range, (-60, 0), -r.design.tilt_deg)
        self.summary.setText(f'Inclinação solicitada: {fmt(r.design.tilt_deg)}° • '
                             f'Progressão após corte: {fmt(r.fitted_tilt_deg, 4)}° • '
                             f'Espaçamento: {fmt(r.design.spacing_m/r.wavelength_m, 4)} λ • '
                             f'Coerência no alvo: {fmt(r.coherence_efficiency*100, 3)}%')
        notes = []
        if r.grating_angles_deg:
            notes.append('O fator de arranjo admite lóbulos de grade; o diagrama completo inclui a atenuação angular da antena.')
        if not self.view_range[0] <= -r.design.tilt_deg <= self.view_range[1]:
            notes.append('A direção de tilt solicitada está fora da faixa exibida.')
        if data.sampling_limited:
            notes.append('Resolução limitada para este arranjo. Reduza a faixa angular para inspecionar picos e nulos estreitos.')
        self.notice.setText('\n'.join(notes))
        self.notice.setVisible(bool(notes))
