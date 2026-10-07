"""Native, scalable engineering illustrations tied to the calculated design."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

INK = '#172d48'
MUTED = '#40536e'
BLUE = '#2946c7'
TEAL = '#008caa'
GRID = '#e3eaf2'


def text(p, x, y, w, h, value, size=10, color=INK, bold=False, align=Qt.AlignmentFlag.AlignLeft):
    p.setPen(QColor(color))
    p.setFont(QFont('Segoe UI', size, QFont.Weight.DemiBold if bold else QFont.Weight.Normal))
    p.drawText(QRectF(x, y, w, h), align | Qt.AlignmentFlag.AlignVCenter, value)


def line(p, x1, y1, x2, y2, color=GRID, width=1, dashed=False):
    pen = QPen(QColor(color), width)
    if dashed:
        pen.setStyle(Qt.PenStyle.DashLine)
    p.setPen(pen)
    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def arrow(p, x1, y1, x2, y2, color=BLUE, width=2):
    line(p, x1, y1, x2, y2, color, width)
    direction = math.atan2(y2-y1, x2-x1)
    for turn in (-0.45, 0.45):
        line(p, x2, y2, x2-9*math.cos(direction+turn), y2-9*math.sin(direction+turn), color, width)


class SeriesChart(QWidget):
    def __init__(self, title='', subtitle='', parent=None):
        super().__init__(parent)
        self.title, self.subtitle = title, subtitle
        self.series = []
        self.dashed_series = set()
        self.x_bounds = None
        self.y_bounds = None
        self.x_label, self.y_label = '', ''
        self.marker_x = None
        self.hover = None
        self.setMouseTracking(True)
        self.setMinimumSize(310, 270)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, series, x_label='', y_label='', x_bounds=None, y_bounds=None, marker_x=None):
        self.series = series
        self.x_label, self.y_label = x_label, y_label
        self.x_bounds, self.y_bounds, self.marker_x = x_bounds, y_bounds, marker_x
        self.update()

    def mouseMoveEvent(self, event):
        self.hover = event.position()
        self.update()

    def leaveEvent(self, event):
        self.hover = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('white'))
        w, h = self.width(), self.height()
        text(p, 20, 12, w-40, 25, self.title, 11, bold=True)
        text(p, 20, 38, w-40, 22, self.subtitle, 9, MUTED)
        if not self.series:
            text(p, 20, h/2, w-40, 30, 'Calcule para visualizar.', 10, MUTED,
                 align=Qt.AlignmentFlag.AlignCenter)
            return
        xs = [v for s in self.series for v in s[1]]
        ys = [v for s in self.series for v in s[2]]
        xmin, xmax = self.x_bounds or (min(xs), max(xs))
        ymin, ymax = self.y_bounds or (min(ys), max(ys))
        if xmax <= xmin:
            xmax = xmin + 1
        if ymax <= ymin:
            ymax = ymin + 1
        box = QRectF(58, 88, w-82, h-185)
        def point(x, y):
            return QPointF(box.left()+(x-xmin)/(xmax-xmin)*box.width(),
                           box.bottom()-(y-ymin)/(ymax-ymin)*box.height())
        for i in range(7):
            f = i/6
            x, y = box.left()+f*box.width(), box.bottom()-f*box.height()
            line(p, x, box.top(), x, box.bottom())
            line(p, box.left(), y, box.right(), y)
            text(p, x-28, box.bottom()+5, 56, 20, f'{xmin+f*(xmax-xmin):g}', 8, MUTED,
                 align=Qt.AlignmentFlag.AlignCenter)
            text(p, 0, y-11, 50, 22, f'{ymin+f*(ymax-ymin):.1f}', 8, MUTED,
                 align=Qt.AlignmentFlag.AlignRight)
        text(p, box.left(), 64, box.width(), 18, self.y_label, 8, MUTED)
        text(p, box.left(), h-31, box.width(), 20, self.x_label, 9, MUTED,
             align=Qt.AlignmentFlag.AlignCenter)
        p.save()
        p.setClipRect(box.adjusted(-1, -1, 1, 1))
        for label, sx, sy, color in reversed(self.series):
            path = QPainterPath()
            for i, (x, y) in enumerate(zip(sx, sy)):
                q = point(x, y)
                if i == 0:
                    path.moveTo(q)
                else:
                    path.lineTo(q)
            pen = QPen(QColor(color), 2)
            if label in self.dashed_series:
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawPath(path)
        if self.marker_x is not None and xmin <= self.marker_x <= xmax:
            x = point(self.marker_x, ymin).x()
            line(p, x, box.top(), x, box.bottom(), '#cc8617', 1.5, True)
        p.restore()
        offset = 22
        for label, _, _, color in self.series:
            line(p, offset, h-48, offset+17, h-48, color, 3, label in self.dashed_series)
            text(p, offset+23, h-59, 170, 22, label, 8, MUTED)
            offset += 170
        if self.hover is not None and box.contains(self.hover):
            at = xmin+(self.hover.x()-box.left())/box.width()*(xmax-xmin)
            sx, sy = self.series[0][1:3]
            index = min(range(len(sx)), key=lambda i: abs(sx[i]-at))
            q = point(sx[index], sy[index])
            line(p, q.x(), box.top(), q.x(), box.bottom(), '#94a3b8', 1, True)
            p.setBrush(QColor(BLUE))
            p.drawEllipse(q, 4, 4)
            rx = min(max(box.left(), q.x()-60), box.right()-145)
            p.fillRect(QRectF(rx, box.top()+5, 145, 26), QColor('#edf3ff'))
            text(p, rx+6, box.top()+5, 136, 26, f'{sx[index]:.2f}  →  {sy[index]:.2f}', 9, BLUE)
        p.end()


class ArrayIllustration(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self.kind = 'cable'
        self.simple = False
        self.setMinimumSize(375, 420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_result(self, result, kind):
        self.result, self.kind = result, kind
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('#fbfdff'))
        w, h = self.width(), self.height()
        title = 'Cabos até as antenas' if self.kind == 'cable' else 'Linhas até as antenas'
        text(p, 20, 12, w-40, 25, title, 11, bold=True)
        text(p, 20, 38, w-40, 22, 'Vista lateral · E1 inferior · esquema sem escala', 9, MUTED)
        if not self.result:
            return
        r, d = self.result, self.result.design
        top, bottom = 91, h-150 if self.simple else h-180
        tower_x = min(190, w*0.38)
        panel_x = tower_x+24
        # Lattice mast: contextual geometry, never used in the RF calculation.
        line(p, tower_x-15, top-12, tower_x-15, bottom+30, '#adbed2', 3)
        line(p, tower_x+15, top-12, tower_x+15, bottom+30, '#adbed2', 3)
        for y in range(int(top-10), int(bottom+25), 24):
            line(p, tower_x-15, y, tower_x+15, y+24, '#c5d1df', 1)
            line(p, tower_x+15, y, tower_x-15, y+24, '#c5d1df', 1)
        indices = list(range(d.elements)) if d.elements <= 8 else sorted({round(i*(d.elements-1)/7) for i in range(8)})
        for display_i, i in enumerate(indices):
            e = r.elements[i]
            y = bottom - (bottom-top)*i/(d.elements-1)
            color = QColor.fromHsv(225-int(35*i/(d.elements-1)), 190, 190).name()
            route_x = 40+display_i*9
            path = QPainterPath(QPointF(44, bottom+45))
            if self.kind == 'cable':
                path.cubicTo(QPointF(route_x-10, y), QPointF(route_x+10, y), QPointF(panel_x, y))
            else:
                path.lineTo(route_x, bottom+45)
                path.lineTo(route_x, y)
                path.lineTo(panel_x, y)
            p.setPen(QPen(QColor(color), 2.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setBrush(QColor('#e6edff'))
            p.setPen(QPen(QColor(color), 1.5))
            p.drawRoundedRect(QRectF(panel_x, y-15, 38, 30), 4, 4)
            for shift in (8, 15, 22, 29):
                line(p, panel_x+shift, y-8, panel_x+shift, y+8, color, 1.5)
            text(p, panel_x+49, y-22, w-panel_x-58, 23,
                 f'E{e.number}' if self.simple else f'E{e.number}   {e.length_m*1000:.1f} mm', 11 if self.simple else 10, color, True)
            if self.simple:
                position = 'Mais baixa' if i == 0 else 'Mais alta' if i == d.elements-1 else ''
                text(p, panel_x+49, y, w-panel_x-58, 19, position, 9, MUTED)
            else:
                text(p, panel_x+49, y, w-panel_x-58, 19, f'φ {e.relative_phase_deg:+.2f}°', 9, MUTED)
        p.setBrush(QColor('#142f53'))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(24, bottom+35, 87, 34), 5, 5)
        text(p, 28, bottom+35, 79, 34, f'Divisor 1:{d.elements}', 9, 'white', True,
             Qt.AlignmentFlag.AlignCenter)
        text(p, 127, bottom+37, w-140, 31,
             'Do transmissor às antenas' if self.simple else f'd = {d.spacing_m*1000:.1f} mm   ·   θ = {d.tilt_deg:+.2f}°', 9, BLUE)
        if d.elements > 8:
            text(p, 20, 65, w-40, 18, f'8 das {d.elements} antenas; todas estão na tabela.', 8, MUTED)
        if self.simple:
            line(p, 20, h-60, w-20, h-60)
            text(p, 20, h-55, w-40, 42, 'Cada conexão E1, E2… corresponde\na uma linha da tabela.', 10, MUTED)
            p.end()
            return
        line(p, 20, h-95, w-20, h-95)
        # Longitudinal section: cable dielectric versus rigid air-line.
        y = h-61
        p.setBrush(QColor('#35516d' if self.kind == 'cable' else '#879aac'))
        p.drawRoundedRect(QRectF(25, y-10, 142, 30), 5, 5)
        p.setBrush(QColor('#dcf3fb' if self.kind == 'cable' else '#ffffff'))
        p.drawRect(QRectF(31, y-5, 130, 20))
        p.setBrush(QColor('#bf7b34'))
        p.drawRect(QRectF(22, y+2, 147, 6))
        text(p, 181, h-85, w-194, 25, 'Dielétrico sólido / espumado' if self.kind == 'cable' else 'Condutor interno · dielétrico de ar', 9, MUTED)
        text(p, 181, h-59, w-194, 25, f'VF {d.velocity_factor:.4f}   ·   λg {r.guided_wavelength_m*1000:.2f} mm', 9, BLUE, True)
        text(p, 25, h-34, 142, 22, 'Corte longitudinal esquemático', 7, MUTED)
        p.end()


class LengthIllustration(QWidget):
    """Manufacturing view of differential branch lengths and RF reference planes."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result, self.kind = None, 'cable'
        self.setMinimumSize(310, 260)

    def set_result(self, result, kind):
        self.result, self.kind = result, kind
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('white'))
        w, h = self.width(), self.height()
        text(p, 20, 13, w-40, 25, 'Comprimentos e planos de referência', 11, bold=True)
        text(p, 20, 40, w-40, 25, 'Conectores e transições exigem compensação de fase em bancada.', 9, MUTED)
        if not self.result:
            return
        r = self.result
        rows = [r.elements[-1], r.elements[0]]
        maxlen = max(e.length_m for e in rows) or 1
        start, available = 92, w-152
        for i, e in enumerate(rows):
            y = 105+i*78
            end = start + max(30, available*e.length_m/maxlen)
            text(p, 20, y-18, 63, 34, f'E{e.number}', 11, BLUE, True)
            gradient = QLinearGradient(0, y-9, 0, y+9)
            gradient.setColorAt(0, QColor('#98aec8'))
            gradient.setColorAt(0.5, QColor('#2946c7' if self.kind == 'cable' else '#c3ced8'))
            gradient.setColorAt(1, QColor('#546a87'))
            p.setBrush(gradient)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(start, y-9, end-start, 18), 4, 4)
            for xx in (start, end):
                p.setBrush(QColor('#c6984d'))
                p.drawRect(QRectF(xx-4, y-13, 8, 26))
                line(p, xx, y-28, xx, y+30, '#64768c', 1, True)
            text(p, start, y+16, available, 24, f'{e.length_m*1000:.3f} mm   ·   fase {e.relative_phase_deg:+.3f}°', 9, MUTED)
        text(p, 20, h-50, w-40, 30,
             f'ΔL por nível: {r.delta_length_m*1000:+.4f} mm   |   corte: {r.design.cut_step_mm:g} mm', 10, BLUE, True)
        p.end()
