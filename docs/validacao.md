# Evidência de validação — 07/10/2026

Ambiente: Windows 11 x64, Python 3.12.10, PySide6 6.11.2,
SQLite da biblioteca padrão, PyInstaller 6.22.3.

## Executado

- `python -m pytest -q`: **64 testes aprovados**.
- Paridade com as duas planilhas XLS: tolerância absoluta de `1e-9 mm` para
  diferença de comprimento e `1e-10 grau` para fase dos casos de referência.
- Valores das 1669 amostras conferidos, interpolação independente testada,
  bloqueio fora da faixa por modelo e ausência de atenuação diferenciada de zero.
- Sinal do feixe verificado por busca do máximo do fator de arranjo, para tilt
  positivo, zero e negativo, com espaçamento sem lóbulos de grade.
- Orçamento de potência independente, coerência, quantização, limites, não
  finitos, vírgula/ponto decimal e casos extremos de atenuação.
- Persistência SQLite entre conexões, revisões independentes e consultas
  parametrizadas; carregar, recalcular e exportar no Qt.
- Capturas Qt inspecionadas: cabo, linha rígida, comprimentos, perdas, catálogo,
  janela de 1540×1000 e janela compacta de 1100×760 com rolagem.
- Dois PDFs de quatro páginas gerados pela própria aplicação, texto/valores
  extraídos com pypdf e páginas renderizadas com Poppler. Logo e figuras
  incorporados, tabela e fórmulas legíveis. Os relatórios têm geometria de
  figuras fixa, independente do tamanho da janela.
- CSV com BOM UTF-8, separador `;`, decimais com vírgula; JSON com valores
  numéricos e `null` para dados indisponíveis.
- `compileall`, instalação editável e `git diff --check`.
- Executável PyInstaller: abertura, cálculo inicial, catálogo SQLite e
  encerramento automático testados com os plugins Qt **offscreen** e
  **Windows nativo**. Ambos retornaram código zero. Banco do executável
  confirmou 47 modelos e 1669 amostras.

## Correções encontradas na validação

1. Fonte do plugin Qt offscreen no Windows: ele não enumera fontes do sistema.
   A ferramenta de captura carrega Segoe UI explicitamente para evitar falsos
   defeitos de caracteres. A aplicação nativa usa as fontes normais do Windows.
2. Empacotamento: PyInstaller selecionou uma `icuuc.dll` de Poppler no PATH,
   cujos símbolos diferem da API ICU do Windows usada pelo Qt. O spec exclui
   essa biblioteca externa e seus dados ICU para usar a dependência do sistema.
   A falha foi reproduzida e a correção conferida no executável final.
3. Coerência normalizada para evitar underflow quando a perda comum é muito alta.
4. Mudanças de entrada desativam resultados e bloqueiam salvamento/exportação;
   personalização da linha não herda atenuação do modelo anterior.

## Não validado

- Medições de fase, perdas ou padrão em bancada RF.
- Rendimento de radiação, acoplamento, ROE e validação térmica de cabos/conectores.
- Instalação em outro computador limpo, Windows 10, Linux ou macOS.
- Assinatura digital do executável e instalador MSI.

Os testes de interface são automatizados com Qt e capturas reais de widgets.
O teste nativo do executável verifica inicialização; não equivale a uma sessão
manual completa em outro computador. A evidência é datada e deve ser renovada
quando o motor, o catálogo, Qt ou o empacotamento mudarem.
