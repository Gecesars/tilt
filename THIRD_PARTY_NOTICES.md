# Componentes de terceiros — EFTX Tilt 1.3.0

A licença proprietária EFTX cobre apenas os componentes próprios. Os componentes
abaixo conservam suas licenças e direitos originais. Os textos e avisos estão em
`licenses/`; as fontes correspondentes e instruções de substituição das bibliotecas
compartilhadas estão em `licenses/SOURCES.md`.

| Componente | Versão | Termos utilizados |
| --- | --- | --- |
| Python | 3.12.10 | Python Software Foundation License e avisos incorporados |
| Qt / PySide6 / Shiboken6 | 6.11.2 | LGPL-3.0, com avisos dos componentes incorporados |
| Qt PDF / PDFium | Qt 6.11.2 | LGPL-3.0 para Qt PDF; BSD e avisos incorporados do PDFium |
| PyInstaller, bootloader | 6.22.3 | GPL-2.0-or-later com exceção de distribuição do bootloader |
| SQLite | versão incluída no Python | domínio público, conforme o projeto SQLite |
| OpenSSL | 3.0.16 (Python) / 3.6.4 (Qt) | Apache-2.0 e avisos incorporados |
| Microsoft Visual C++ Runtime | DLLs incluídas no Python/Qt | termos de redistribuição Microsoft |
| WiX UI, suporte do instalador | 5.0.2 | MS-RL; termos próprios não se transferem ao aplicativo |

Qt: Copyright (C) The Qt Company Ltd. e demais autores identificados nos avisos.
Python: Copyright (C) Python Software Foundation e demais autores identificados
em sua licença. Os arquivos originais de aviso identificam os demais titulares.

O aplicativo utiliza Qt Core, Gui, Widgets, Network, PrintSupport, PDF e SVG,
além de plugins de plataforma e formatos de imagem. Qt Virtual Keyboard não é
utilizado nem distribuído. As DLLs e extensões `.pyd` ficam separadas do executável,
em `_internal/`; não há verificação de assinatura que impeça sua substituição por
bibliotecas modificadas compatíveis. Uma reparação manual do MSI restaura os
arquivos originais; guarde suas modificações antes de solicitar reparação.

O catálogo `CableRating.xml` foi fornecido a partir do ADT-PY pelo responsável
pelo projeto. Sua origem e hash estão preservados em `tilt/data/cables.json`;
os dados não são relicenciados pela licença EFTX. O logo EFTX foi fornecido e
aprovado pelo responsável pelo projeto.
