# Evidência de validação — 07/10/2026

Ambiente: Windows 11 x64, Python 3.12.10, PySide6 6.11.2,
SQLite da biblioteca padrão, PyInstaller 6.22.3.

## Cálculos, diagramas e impressão 1.2.0

- **104 testes aprovados**. Mantida a paridade com as duas planilhas; acrescida
  comparação independente do fator de arranjo com a solução fechada de um
  arranjo uniforme. Somatórios de campo, coerência e potência usam `math.fsum`.
- Preenchimento de `d = λ₀`: frequência decimal, canal, deslocamento OFDM e
  constante SI conferidos com tolerância absoluta de `1e-9 mm`. Trocar cabo
  por linha rígida não aplica o VF ao espaçamento livre.
- Edição manual, retorno ao automático, entradas inválidas e reabertura de
  projetos antigos sem `spacing_auto` verificados. Exemplos XLS permanecem
  com o espaçamento original e modo manual.
- Aba Diagramas: limites válidos/inválidos, normalização independente do zoom,
  direção do tilt, alvo fora da faixa e amostragem limitada em abertura extrema.
  Comparação após corte/ideal/sem tilt, em dB e campo relativo.
- PDF gerado e lido com QtPdf e pypdf: cinco páginas nos exemplos de quatro
  antenas, entradas, resultados, versões, catálogo, tabela, memória e figuras.
  PDFs de cabo e linha rígida renderizados com Poppler e inspecionados.
- Caso de 64 antenas: presença de E1 até E64, perdas desconhecidas como `n/d`,
  paginação da tabela e repetição de cabeçalhos conferidas.
- Impressão testada com saída para arquivo: intervalo, ordem inversa, cópias,
  aceitação e cancelamento do diálogo. Sem impressora, PDF/prévia disponíveis
  e envio desabilitado. Alteração de entradas bloqueia impressão de resultado
  desatualizado; falha de gravação não abre a prévia.
- Executável final em `dist/1.2.0/EFTX_Tilt`: inicialização, PDF e prévia
  testados com Qt offscreen e Windows nativo. Ambos retornaram código 0,
  PDF com texto/valores corretos e catálogo com 47 modelos e 1669 amostras.
- Corrigida a ausência de fontes no plugin Windows offscreen também no
  caminho de diagnóstico do executável. Corrigida a aplicação duplicada de
  margens do QPrinter e QTextDocument para evitar páginas residuais.
- `compileall` e `git diff --check` executados. PyInstaller inclui QtPdf.

Não foi enviada nenhuma página a impressora física. A seleção da impressora
padrão e a prévia foram verificadas; papel, driver físico, duplex e qualidade
da impressão real permanecem sem validação. Os limites RF descritos abaixo
continuam válidos.

## Interface 1.1.0 — revisão para uso por leigos

- **77 testes aprovados**, incluindo os 64 testes da versão anterior.
- Fluxo em três passos; botões de cabo coaxial e linha rígida conferidos com
  filtragem real do catálogo e atualização da ilustração.
- Painéis avançados recolhidos no início; recolher e reabrir preserva entradas,
  cálculo e capacidade de salvar. Erros numéricos em campos avançados abrem
  o painel, incluindo potência e comprimento do trecho comum.
- Conversão canal/frequência, direção da inclinação positiva/negativa/zero,
  tabela simples de comprimentos e avisos técnicos verificados por testes Qt.
- Paleta clara explícita conferida após simular uma paleta de sistema escura.
  Contraste calculado das cores: texto principal 13,95:1; texto secundário
  6,96:1; texto dos botões azuis 10,27:1; bordas dos campos 4,48:1.
  Isso verifica essas combinações, não constitui auditoria completa de acessibilidade.
- Capturas inspecionadas em 1540×1000, 1366×768 e 1100×760, com rolagem nas
  janelas menores. Lista suspensa, seleção de material, tabela simples,
  ajustes avançados, detalhes técnicos, comprimentos e perdas conferidos.
- PDFs de cabos e linhas rígidas regenerados: quatro páginas em cada um;
  conteúdo extraído e páginas de figuras conferidas visualmente com Poppler.
- Executável **dist/1.1.0/EFTX_Tilt/EFTX_Tilt.exe** testado em Qt offscreen
  e Windows nativo; ambos encerraram com código 0. Cada banco de teste
  confirmou os 47 modelos e 1669 amostras.
- Motor RF, catálogo e formato das revisões SQLite preservados. A identificação
  1.1.0 no título permite distinguir a nova janela de uma versão anterior aberta.
- A distribuição usa uma pasta por versão para não substituir arquivos de uma
  instância anterior em execução.

Ainda não realizado: teste de usabilidade com pessoas leigas, leitor de tela
e instalação em outro computador limpo.

## Versão inicial 1.0.0 — executado

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
