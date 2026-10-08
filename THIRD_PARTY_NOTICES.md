# Componentes de terceiros — EFTX Tilt 1.4.1

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
| OpenSSL | 3.0.16 (Python) | Apache-2.0 e avisos incorporados |
| Microsoft Visual C++ Runtime | DLLs incluídas no Python/Qt | termos de redistribuição Microsoft |
| NSIS, instalador EXE | 3.12 | zlib/libpng e avisos dos módulos de compressão, em NSIS-COPYING.txt |
| WiX UI, instaladores MSI anteriores | 5.0.2 | MS-RL; mantido como referência histórica |

Qt: Copyright (C) The Qt Company Ltd. e demais autores identificados nos avisos.
Python: Copyright (C) Python Software Foundation e demais autores identificados
em sua licença. Os arquivos originais de aviso identificam os demais titulares.

O aplicativo utiliza Qt Core, Gui, Widgets, Network, PrintSupport, PDF e SVG,
além de plugins de plataforma e formatos de imagem. Qt Virtual Keyboard não é
utilizado nem distribuído. As DLLs e extensões `.pyd` ficam separadas do executável,
em `_internal/`; não há verificação de assinatura que impeça sua substituição por
bibliotecas modificadas compatíveis. A reinstalação restaura os arquivos
originais; guarde suas modificações antes de reinstalar ou atualizar.

O backend OpenSSL opcional do Qt não é distribuído; permanece o backend Schannel
do Windows. Avisos de OpenSSL 3.6.4 são mantidos como registro da distribuição
1.3.0, mas suas DLLs externas não integram as distribuições 1.3.1 e 1.3.2.

O catálogo `CableRating.xml` foi fornecido a partir do ADT-PY pelo responsável
pelo projeto. Sua origem e hash estão preservados em `tilt/data/cables.json`;
os dados não são relicenciados pela licença EFTX. O logo EFTX foi fornecido e
aprovado pelo responsável pelo projeto.
