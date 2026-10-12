"""Desenho técnico vetorial do alimentador; cotas vêm exclusivamente do Result.

Esta página não altera o motor RF. Caminhos entre divisor e antenas são
esquemáticos: o comprimento de corte é autoritativo, a geometria das curvas não.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QBrush, QFont, QPainter, QPainterPath, QPen
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtWidgets import (
    QFileDialog, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from .engineering import Result

INK = "#19304a"
BLUE = "#2946c7"
TEAL = "#007f95"
MUTED = "#52657c"
LIGHT = "#d9e4ed"
COPPER = "#b47736"


def _pen(color: str, width: float = 1.2, dashed: bool = False) -> QPen:
    pen = QPen(QColor(color), width)
    if dashed:
        pen.setStyle(Qt.PenStyle.DashLine)
    return pen


def _label(scene: QGraphicsScene, x: float, y: float, value: str,
           *, color: str = INK, size: int = 10, bold: bool = False) -> None:
    item = scene.addSimpleText(value)
    item.setFont(QFont("Segoe UI", size, QFont.Weight.DemiBold if bold else QFont.Weight.Normal))
    item.setBrush(QBrush(QColor(color)))
    item.setPos(x, y)


def _line(scene: QGraphicsScene, x1: float, y1: float, x2: float, y2: float,
          *, color: str = LIGHT, width: float = 1.2, dashed: bool = False) -> None:
    scene.addLine(x1, y1, x2, y2, _pen(color, width, dashed))


def _dimension(scene: QGraphicsScene, x: float, y1: float, y2: float,
               caption: str) -> None:
    # Vertical dimension with witness lines and 45-degree end marks.
    for y in (y1, y2):
        _line(scene, x - 7, y - 7, x + 7, y + 7, color=BLUE)
    _line(scene, x, y1, x, y2, color=BLUE)
    _label(scene, x + 8, (y1 + y2) / 2 - 10, caption, color=BLUE, size=9)


def _text_scene(title: str, subtitle: str) -> QGraphicsScene:
    scene = QGraphicsScene()
    scene.setBackgroundBrush(QBrush(QColor("#fbfdff")))
    _label(scene, 26, 12, title, size=16, bold=True)
    _label(scene, 26, 43, subtitle, color=MUTED, size=10)
    return scene


def make_mount_scene(result: Result, kind: str) -> QGraphicsScene:
    """Vista de elevação com espaçamentos cotados; roteamento ilustrativo."""
    if kind not in {"cable", "rigid"}:
        raise ValueError("Tipo de material inválido.")
    d = result.design
    scene = _text_scene(
        "EFTX · Vista lateral cotada",
        "Elevação proporcional ao espaçamento entre centros; conexões esquemáticas.",
    )
    n = len(result.elements)
    step = 69.0
    bottom = 120.0 + (n - 1) * step
    divider_y = (120.0 + bottom) / 2 if result.center_feed else bottom + 104
    tower_left, tower_right, port_x = 570.0, 606.0, 650.0

    _line(scene, tower_left, 97, tower_left, bottom + 49, color="#92a5b9", width=3)
    _line(scene, tower_right, 97, tower_right, bottom + 49, color="#92a5b9", width=3)
    for index in range(n):
        y = bottom - index * step
        _line(scene, tower_left, y, tower_right, y, color="#a0b2c4")
        _line(scene, tower_left, y, tower_right, y + step / 2 if index else y,
              color="#c4d1dd")
        _line(scene, 780, y, 795, y, color=BLUE)
        scene.addRect(650, y - 13, 100, 26, _pen(BLUE, 1.5),
                      QBrush(QColor("#eaf1fd")))
        _label(scene, 676, y - 12, f"E{index + 1}", color=BLUE, bold=True)
        _label(scene, 805, y - 18,
               f"E{index + 1}  ·  {result.elements[index].length_m * 1000:.3f} mm",
               size=10)
        if index:
            _line(scene, 880, y, 880, y + step, color=LIGHT, dashed=True)
            _dimension(scene, 970, y, y + step, f"{d.spacing_m * 1000:.2f} mm")
    for i, element in enumerate(result.elements):
        y = bottom - i * step
        # The link is *not* the physical cutting route; it is a functional map.
        left_x = 365.0 + 5 * (i % 7)
        path = QPainterPath()
        path.moveTo(488, divider_y)
        if kind == "cable":
            path.cubicTo(left_x, divider_y, left_x, y, 650, y)
        else:
            path.lineTo(left_x, divider_y)
            path.lineTo(left_x, y)
            path.lineTo(650, y)
        scene.addPath(path, _pen(TEAL if kind == "cable" else COPPER, 1.8))
    scene.addRect(438, divider_y - 25, 100, 50, _pen(INK, 1.6),
                  QBrush(QColor(INK)))
    _label(scene, 449, divider_y - 17, f"Divisor 1:{n}", color="#ffffff", bold=True)
    _label(scene, 28, divider_y - 20, "Centro do arranjo" if result.center_feed
           else "Posição ilustrativa", size=10, color=MUTED)
    _line(scene, 220, divider_y, 438, divider_y, color=COPPER, width=2.5)
    _label(scene, 26, divider_y + 10,
           "Linha comum (comprimento de entrada separado)", color=MUTED, size=9)

    top = bottom - (n - 1) * step
    _line(scene, 1100, top, 1100, bottom, color=BLUE)
    _dimension(scene, 1100, top, bottom,
               f"Altura total: {(n - 1) * d.spacing_m * 1000:.2f} mm")
    if result.center_feed:
        _label(scene, 26, 81,
               f"Divisor central: {result.center_feed.divider_height_m * 1000:.2f} mm acima de E1",
               color=BLUE, bold=True)
    else:
        _label(scene, 26, 81, "Modo ramal mínimo: localização física do divisor não informada.",
               color=BLUE, bold=True)
    _label(scene, 26, max(bottom, divider_y) + 83,
           "ATENÇÃO: caminhos, curvas, torre e conectores não estão dimensionados.",
           color="#9c4e25", size=11, bold=True)
    _label(scene, 26, max(bottom, divider_y) + 107,
           "Validar suportes, raio de curvatura, conexões e folgas em campo antes de fabricar.",
           color=MUTED)
    scene.setSceneRect(0, 0, 1350, max(bottom, divider_y) + 155)
    return scene


def make_cut_scene(result: Result, kind: str) -> QGraphicsScene:
    """Plano de corte: todas as barras usam a mesma escala linear em mm."""
    if kind not in {"cable", "rigid"}:
        raise ValueError("Tipo de material inválido.")
    d = result.design
    name = "cabos coaxiais" if kind == "cable" else "linhas rígidas"
    scene = _text_scene(
        f"EFTX · Plano de corte — {name}",
        "Barras em escala linear relativa; cotas numéricas em mm determinam a fabricação.",
    )
    _label(scene, 27, 73,
           "Malha a malha / condutor externo" if d.length_reference == "shield_edges"
           else "Referência elétrica legada: verificar planos físicos antes do corte.",
           color=BLUE, bold=True)
    longest = max(e.length_m for e in result.elements)
    x0, width = 160.0, 920.0
    for i, element in enumerate(result.elements):
        y = 132 + i * 65
        length_px = (element.length_m / longest) * width if longest else 0.0
        _label(scene, 26, y - 10, f"E{element.number}", color=BLUE, size=11, bold=True)
        _line(scene, x0, y, x0 + length_px, y, color=TEAL if kind == "cable"
              else COPPER, width=14)
        _line(scene, x0, y - 21, x0, y + 21, color=INK)
        _line(scene, x0 + length_px, y - 21, x0 + length_px, y + 21, color=INK)
        _line(scene, x0, y + 24, x0 + length_px, y + 24, color=BLUE)
        _label(scene, 1098, y - 13, f"{element.length_m * 1000:.3f} mm", bold=True)
        _label(scene, 1098, y + 8, f"fase {element.relative_phase_deg:+.3f}°", color=MUTED, size=9)
    footer = 132 + len(result.elements) * 65 + 22
    _label(scene, 26, footer,
           f"f = {d.frequency_mhz:g} MHz  ·  VF = {d.velocity_factor:g}  ·  "
           f"passo de corte = {d.cut_step_mm:g} mm", color=BLUE, bold=True)
    _label(scene, 26, footer + 26,
           "Conectores, derivações e curvas não estão incluídos nas cotas de corte. "
           "Validar com instrumentos de RF.", color="#9c4e25")
    scene.setSceneRect(0, 0, 1450, footer + 83)
    return scene


class DrawingView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMinimumHeight(380)

    def show_scene(self, scene: QGraphicsScene) -> None:
        self.setScene(scene)
        self.fit()

    def fit(self) -> None:
        if self.scene() and not self.scene().sceneRect().isEmpty():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class DraftingPage(QWidget):
    """Página destacada de desenho técnico. Exportação offline sem telemetria."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result: Result | None = None
        self.kind = "cable"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        title = QLabel("Desenho técnico de montagem e corte")
        title.setObjectName("AppTitle")
        layout.addWidget(title)
        note = QLabel(
            "Cotas calculadas em milímetros. Vista da montagem proporcional à distância "
            "entre antenas; comprimento dos ramais em escala relativa. "
            "Traçados de conexão são ilustrativos."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        bar = QHBoxLayout()
        self.fit_button = QPushButton("Ajustar à tela")
        self.zoom_in = QPushButton("Ampliar +")
        self.zoom_out = QPushButton("Reduzir −")
        self.svg_button = QPushButton("Exportar desenho SVG…")
        self.svg_button.setObjectName("Primary")
        for button in (self.fit_button, self.zoom_in, self.zoom_out):
            bar.addWidget(button)
        bar.addStretch(1)
        bar.addWidget(self.svg_button)
        layout.addLayout(bar)
        self.tabs = QTabWidget()
        self.mount_view = DrawingView()
        self.cut_view = DrawingView()
        self.tabs.addTab(self.mount_view, "Vista da montagem")
        self.tabs.addTab(self.cut_view, "Plano de corte")
        layout.addWidget(self.tabs, 1)
        self.info = QLabel("Calcule um projeto para gerar o desenho.")
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        self.fit_button.clicked.connect(self.fit_current)
        self.zoom_in.clicked.connect(lambda: self.zoom_current(1.25))
        self.zoom_out.clicked.connect(lambda: self.zoom_current(0.8))
        self.svg_button.clicked.connect(self.export_svg)
        self.tabs.currentChanged.connect(lambda _index: self.fit_current())
        self.invalidate()

    def current_view(self) -> DrawingView:
        return (self.mount_view, self.cut_view)[self.tabs.currentIndex()]

    def fit_current(self) -> None:
        self.current_view().fit()

    def zoom_current(self, ratio: float) -> None:
        view = self.current_view()
        if view.scene():
            view.scale(ratio, ratio)

    def invalidate(self) -> None:
        self.result = None
        self.mount_view.setScene(QGraphicsScene())
        self.cut_view.setScene(QGraphicsScene())
        self.svg_button.setEnabled(False)
        self.info.setText("Entradas alteradas: recalcule para atualizar as cotas.")

    def set_result(self, result: Result, kind: str) -> None:
        self.result, self.kind = result, kind
        self.mount_view.show_scene(make_mount_scene(result, kind))
        self.cut_view.show_scene(make_cut_scene(result, kind))
        self.svg_button.setEnabled(True)
        self.info.setText(
            "Cotas derivadas do resultado calculado. A geometria das conexões não "
            "incorpora comprimentos de curvas, conectores ou montagem em torre."
        )

    def export_svg(self) -> None:
        if self.result is None or not self.current_view().scene():
            return
        title = "montagem" if self.tabs.currentIndex() == 0 else "corte"
        filename, _filter = QFileDialog.getSaveFileName(
            self, "Exportar desenho vetorial", f"eftx-tilt-{title}.svg",
            "Desenho vetorial SVG (*.svg)",
        )
        if filename:
            export_scene_svg(self.current_view().scene(), Path(filename))


def export_scene_svg(scene: QGraphicsScene, path: Path) -> None:
    """Grava cotas vetoriais; usa a mesma cena que foi aprovada na interface."""
    bounds = scene.sceneRect()
    if bounds.isEmpty():
        raise ValueError("Não há desenho para exportar.")
    device = QSvgGenerator()
    device.setFileName(str(path))
    device.setSize(QSize(int(bounds.width()), int(bounds.height())))
    device.setViewBox(bounds.toRect())
    device.setTitle("EFTX Tilt — desenho técnico")
    device.setDescription("Cotas derivadas do cálculo. Conexões ilustrativas.")
    painter = QPainter()
    if not painter.begin(device):
        raise OSError(f"Não foi possível exportar o desenho para {path}.")
    try:
        scene.render(painter, QRectF(bounds), bounds)
    finally:
        painter.end()
