# EFTX Tilt elétrico

Aplicação desktop em **PySide6 + SQLite3** para dimensionar o tilt elétrico entre
elementos de um arranjo vertical, usando cabos coaxiais ou linhas rígidas.
Identidade visual: logo **EFTX ANTENNAS** fornecido pelo usuário.

## Executar no Windows

- Requisito: **Windows 10 versão 1809 ou posterior, 64 bits (x64)**, ou Windows
  11 x64. Inclui Windows 10 22H2 e LTSC 2019/2021. Consulte a
  [compatibilidade e seus limites de validação](docs/windows_compatibilidade.md).
- Ambiente preparado: abra **`iniciar.cmd`**.
- Baixe o **MSI para Windows x64** em [Releases](https://github.com/Gecesars/tilt/releases).
  Leia e aceite a licença, escolha a pasta e conclua. O programa cria atalhos no
  menu Iniciar e na área de trabalho; não é necessário instalar Python.
- Distribuição portátil: extraia todo o ZIP e abra **`EFTX_Tilt/EFTX_Tilt.exe`**.
  Mantenha `_internal`, `LICENSE.txt`, `THIRD_PARTY_NOTICES.md` e `licenses/` na pasta.
- Instalação a partir do código (Python 3.11 ou superior):

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
.\.venv\Scripts\python.exe -m tilt
```

O banco é criado no diretório de dados locais do usuário, normalmente
`%LOCALAPPDATA%/EFTX/EFTX Tilt/tilt.sqlite3`. Não é gravado junto ao executável.
Para definir outro banco:

```powershell
.\.venv\Scripts\python.exe -m tilt --database D:\projetos\meu_tilt.sqlite3
```

O MSI instala para o usuário atual em `%LOCALAPPDATA%/Programs/EFTX/Tilt` por
padrão. Reparar ou desinstalar o programa preserva o banco no diretório de dados.
Consulte [instalação e empacotamento](docs/instalador.md) para uso silencioso,
geração do MSI e validação de integridade. Esta distribuição não possui assinatura
digital de editor.

## Licença

O código próprio é proprietário EFTX. O uso é restrito à EFTX e a usuários
expressamente autorizados por escrito; o acesso ao repositório ou ao download
não concede autorização. Leia [LICENSE.txt](LICENSE.txt). O instalador solicita
aceite dos termos; não implementa ativação ou controle de acesso remoto.

As bibliotecas conservam suas licenças originais, inclusive os direitos LGPL
aplicáveis. Consulte [avisos de terceiros](THIRD_PARTY_NOTICES.md) e
[fontes e substituição das bibliotecas](licenses/SOURCES.md).

## Uso em três passos

1. Clique em **Cabo coaxial** ou **Linha rígida** e escolha o modelo na lista.
2. Informe a frequência em MHz **ou** o canal de TV. O espaçamento é preenchido
   automaticamente com **1 λ no espaço livre (c/f)**, usando a constante escolhida.
3. Informe a quantidade de antenas, a distância entre seus centros em mm,
   a inclinação desejada em graus e o trecho mais curto em metros.

Clique em **Calcular comprimentos** (`Ctrl+Enter`). A tela mostra uma orientação
em texto, o esquema das conexões, os comprimentos de E1 (inferior) até EN (superior)
e a energia estimada que chega às antenas. Os valores iniciais são um exemplo.

A tabela usa medidas **de malha a malha**, ao longo do cabo, entre extremidades
da blindagem; para linhas rígidas, extremidades do condutor externo. Pontas
expostas e conectores ficam fora da medida. As terminações são consideradas
iguais em todos os ramais. As colunas mostram diferenças em relação ao anterior
e a E1, **após arredondar** ao passo de corte; negativo significa mais curto.

**Mostrar ajustes avançados** abre fator de velocidade, perdas, trecho comum,
potência, passo de corte e referência de cálculo. Recolher mantém os valores;
o resumo indica o passo de corte e as perdas adicionais em uso. O modelo
personalizado abre automaticamente os campos necessários. Um erro em um campo
avançado abre o painel para permitir a correção.

Ao editar a distância, o modo passa para manual e novas frequências preservam
essa medida. Marque **Espaçamento automático: 1 λ** para retomar o acompanhamento.
Projetos antigos mantêm o espaçamento salvo. λ livre é diferente de λ na linha;
o fator de velocidade do cabo não reduz a distância automática entre antenas.

**Ver detalhes técnicos** abre fase, potência, perdas, tabela completa e memória
de cálculo. **Salvar cálculo** (`Ctrl+S`) cria uma nova revisão no banco local.
Ao abrir uma revisão, recalcule antes de exportar. **Exportar** gera PDF ilustrado,
CSV com separador `;` ou JSON.

O canal usa centro geométrico de 6 MHz; o deslocamento +1/7 MHz é opcional nos
ajustes avançados. A seleção de material aplica um único modelo ao cálculo:
cabo coaxial **ou** linha rígida, incluindo eventual trecho antes do divisor.

## Diagramas verticais

Na aba **Diagramas**, defina início/fim do eixo X entre **−90° e +90°** e clique
**Aplicar faixa**. **Faixa completa** restaura os limites e **Focar no tilt**
mostra ±10° em torno do alvo. O eixo representa **elevação**: valores negativos
apontam para baixo. Não é azimute horizontal.

As curvas mostram o resultado após o corte, o caso com comprimentos ideais e
o caso sem tilt (fases zeradas, mesmas amplitudes). Escolha dB ou campo relativo.
Mudar a faixa altera apenas a visualização; não recalcula comprimentos nem
renormaliza os níveis. O gráfico indica lóbulos de grade e limitações de amostragem.

O modelo inicial é **dipolo vertical de meia onda (aproximação)**: campo total =
campo do elemento × fator de arranjo. Os nulos em ±90° resultam desse modelo.
A subaba técnica permite conferir o fator de arranjo isolado, que pode ter máximos
axiais com espaçamento de 1 λ. Outros lóbulos físicos permanecem visíveis.
Projetos anteriores preservam a opção isotrópica até uma troca explícita.

## PDF e impressão

**Imprimir…** (`Ctrl+P`) gera o PDF detalhado em
`Documentos/EFTX Tilt/Relatorios` com nome datado e abre sua prévia. Ela usa a
impressora padrão do Windows e permite navegar pelas páginas, ampliar e abrir
o PDF. **Imprimir…** na prévia abre o diálogo do sistema para escolher impressora,
páginas e cópias; cancelar não envia o trabalho. Sem impressora configurada,
o PDF e a prévia continuam disponíveis.

O relatório contém entradas e modo de espaçamento, resultados, tabela completa,
memória de cálculo, avisos, diagrama completo e faixa selecionada, esquema de
montagem, versão e identificação do catálogo. Se a tela estiver na faixa completa,
o PDF também inclui uma ampliação automática do tilt. A prévia e a impressão
usam as páginas do PDF salvo, sem recalcular o projeto.

Inclui a potência média máxima do material na frequência, limite de pico separado,
entrada e margem dos ramais e da linha comum, amostras usadas na interpolação,
tabelas de diferenças e desenhos cotados de **todos** os trechos (até 64).

Entradas numéricas aceitam vírgula ou ponto decimal, sem separadores de milhar.
Valores inválidos são rejeitados. Alterar uma entrada desativa os resultados
anteriores, o salvamento e a exportação até novo cálculo.

## Catálogo

**47 modelos e 1.669 pontos** foram importados do
`ADT_PY/assets/original_adt/Rating/CableRating.xml` indicado pelo usuário:
VF, impedância, atenuação, potência média por frequência, potência e tensão de pico.
O catálogo está incluído na aplicação; o ADT-PY não precisa estar instalado.

Interpolação **log-log**, por modelo e somente dentro da faixa disponível.
Não se reproduz o comportamento legado de amostra mais próxima/global de frequência.
O modo personalizado permite VF informado e atenuação opcional. Ausência de
atenuação produz **n/d**, nunca eficiência fictícia de 100%.

A potência média máxima exibida é a referência de catálogo na frequência informada.
Não é substituída pela potência de pico. Temperatura, altitude, ROE e fatores de
redução não constam do XML; conectores e divisor podem impor limites menores.
O fator de crista não foi informado, portanto a condição de pico não é verificada.
Limites, amostras, margens, comprimentos e modelo do diagrama são copiados para a
revisão SQLite; alterações posteriores no catálogo não alteram a revisão salva.

## Engenharia

E1 é o elemento inferior; tilt positivo aponta para baixo. O elemento superior
usa um percurso mais curto e recebe avanço de fase. O padrão inicial de constante
`c = 300.000.000 m/s` reproduz as planilhas; a opção SI está disponível.

```text
λ₀ = c / f
λg = VF × λ₀
Δφ = 360° × d / λ₀ × sen(θ)
ΔL = VF × d × sen(θ)
```

Em **Ajustes avançados → Carregar exemplo**, escolha a planilha de cabo ou linha rígida.
Consulte [a memória de engenharia](docs/engenharia.md) para unidades, equações,
fixtures, origem dos dados e limites.

**Eficiência de alimentação** é a fração de potência que chega aos elementos.
Não inclui eficiência de radiação, ROE, acoplamento ou perdas não informadas.
A coerência no alvo é calculada separadamente. O gráfico principal inclui a
aproximação analítica do elemento selecionado; não é ganho em dBi ou diagrama medido.

## Desenvolvimento e validação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/visual_check.py
.\.venv\Scripts\python.exe -m tilt --database .artifacts/smoke.sqlite3 --smoke-test
.\.venv\Scripts\python.exe -m tilt --database .artifacts/smoke.sqlite3 --smoke-test --smoke-pdf .artifacts/smoke.pdf
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
powershell -ExecutionPolicy Bypass -File .\build_installer.ps1
```

Os testes cobrem paridade numérica com XLS, sentido do feixe, orçamento de
potência, ausência de dados, arredondamento, limites, interpolação, SQLite e
fluxos Qt. Evidência datada: [validação](docs/validacao.md).

Dependências de execução: PySide6 (Qt), biblioteca padrão Python e sqlite3.
`pytest`, PyInstaller e Pillow são dependências de desenvolvimento/empacotamento.
Os leitores `xlrd` e `olefile` são opcionais e usados somente pela ferramenta de
inspeção das fontes XLS. A aplicação não executa macros ou instruções das planilhas.

## Estrutura

```text
tilt/engineering.py    equações RF e validação, independentes de Qt
tilt/storage.py        catálogo e revisões SQLite
tilt/specification.py  limites de potência e evidência imutável do material
tilt/window.py         bancada, catálogo, projetos e exportações
tilt/workbench.py      fluxo simples e painéis avançados
tilt/diagrams.py       diagramas verticais e faixa angular
tilt/printing.py       PDF detalhado e prévia/impressão nativa
tilt/theme.py          contraste de controles e paleta clara explícita
tilt/visuals.py        ilustrações e gráficos vetoriais Qt
tilt/reports.py        memória HTML, CSV e JSON
tilt/data/cables.json  catálogo portátil com origem e SHA-256
tests/                regressão numérica, persistência e interface
```

Os dados de trabalho e executáveis ficam fora do Git. O logo foi adotado por
instrução do usuário; não foi redesenhado. Os termos EFTX não alteram os direitos
sobre o catálogo importado nem as licenças dos componentes de terceiros.
