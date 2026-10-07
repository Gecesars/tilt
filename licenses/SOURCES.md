# Fontes e substituição de bibliotecas

Distribuição: EFTX Tilt 1.3.1 para Windows 10 1809+ / Windows 11 x64. Bibliotecas não modificadas.
Consulta às fontes oficiais: 7 de outubro de 2026.

## Fontes correspondentes

Os arquivos abaixo são disponibilizados pelos projetos originais, com acesso
gratuito ao código correspondente. Qt inclui as fontes e avisos de seus
componentes incorporados, inclusive PDFium e bibliotecas de formatos de imagem.

- [Qt 6.11.2, código completo e arquivos de construção](https://download.qt.io/official_releases/qt/6.11/6.11.2/single/qt-everywhere-src-6.11.2.tar.xz).
- [PySide6 e Shiboken6 6.11.2, código e scripts de construção](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/pyside-setup-everywhere-src-6.11.2.tar.xz).
- [Python 3.12.10](https://www.python.org/ftp/python/3.12.10/Python-3.12.10.tar.xz).
- [OpenSSL 3.0.16, utilizado pelo Python](https://github.com/openssl/openssl/tree/openssl-3.0.16).
- [OpenSSL 3.6.4, referência histórica do pacote 1.3.0; DLLs excluídas de 1.3.1](https://github.com/openssl/openssl/tree/openssl-3.6.4).
- [PyInstaller 6.22.3, incluindo bootloader](https://github.com/pyinstaller/pyinstaller/tree/v6.22.3).
- [WiX Toolset 5.0.2, incluindo biblioteca de diálogos](https://github.com/wixtoolset/wix/tree/v5.0.2).
- [SQLite: código e domínio público](https://sqlite.org/copyright.html).
- [Microsoft: bibliotecas de runtime redistribuíveis](https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files).

O instalador utiliza WiX 5.0.2 (MS-RL), fixado no manifesto `dotnet-tools.json`.
Não utiliza WiX 6/7 nem presume contratação ou aceite da OSMF dessas versões.

## Recombinação com bibliotecas modificadas

O programa usa bibliotecas compartilhadas, sem vinculação estática ao Qt e sem
travamento criptográfico das DLLs. Feche o programa, faça uma cópia de segurança
da pasta instalada e substitua as DLLs e extensões `.pyd` abrangidas pela LGPL
por versões Windows x64 de interface binária compatível com Qt/PySide6 6.11 e
Python 3.12. Os arquivos ficam em `_internal/PySide6`, `_internal/shiboken6` e
`_internal`; os plugins Qt ficam em `_internal/PySide6/plugins`.

As instruções de construção acompanham as fontes oficiais acima. A instalação
é por usuário e não exige uma chave EFTX para substituir bibliotecas compatíveis.
Os atalhos são normais, sem reparação automática por anúncio MSI. Uma reparação
solicitada manualmente restaura os arquivos originais; preserve suas alterações
antes de reparação ou atualização. A licença EFTX não restringe modificação,
substituição nem engenharia reversa necessária para depurar essas modificações
nos componentes abrangidos pela LGPL.

## Avisos incluídos

`manifest.json` registra fonte e SHA-256 dos textos copiados. Os arquivos em
`qt-attributions` reproduzem os avisos publicados pela Qt para os módulos
distribuídos; alguns avisos abrangem também variantes de plataforma que não são
usadas neste pacote. LGPL e GPL acompanham o programa como exigido pela LGPL.
Isso não transforma os componentes próprios da EFTX em software livre.
