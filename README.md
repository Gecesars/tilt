# EFTX Tilt elétrico

Aplicação desktop em **PySide6 + SQLite3** para dimensionar o tilt elétrico entre
elementos de um arranjo vertical, usando cabos coaxiais ou linhas rígidas.
Identidade visual: logo **EFTX ANTENNAS** fornecido pelo usuário.

## Executar no Windows

- Ambiente preparado: abra **`iniciar.cmd`**.
- Distribuição portátil: abra **`dist/EFTX_Tilt/EFTX_Tilt.exe`**. A pasta
  `_internal` deve permanecer junto ao executável; não é necessário instalar Python.
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

## Fluxo da bancada

1. Informe frequência em MHz **ou** escolha canal TV. O modo de canal calcula o
   centro geométrico de 6 MHz; o deslocamento +1/7 MHz é opcional.
2. Escolha cabo coaxial ou linha rígida e pesquise o modelo na lista.
3. Defina número de elementos (2–64), espaçamento, tilt, ramal mínimo e passo de corte.
4. Informe linha comum, perdas adicionais e potência antes da alimentação.
5. Clique **Calcular** (`Ctrl+Enter`); confira esquema, diagrama, comprimentos e perdas.
6. **Salvar revisão** (`Ctrl+S`) preserva uma nova cópia das entradas e resultados.
   Abrir uma revisão exige recalcular antes de exportar.
7. Exporte PDF ilustrado, CSV com separador `;` ou memória JSON.

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

Os botões **Exemplo: cabo** e **Exemplo: rígida** reproduzem os casos fornecidos.
Consulte [a memória de engenharia](docs/engenharia.md) para unidades, equações,
fixtures, origem dos dados e limites.

**Eficiência de alimentação** é a fração de potência que chega aos elementos.
Não inclui eficiência de radiação, ROE, acoplamento ou perdas não informadas.
A coerência no alvo é calculada separadamente. O gráfico é fator de arranjo,
não ganho em dBi nem diagrama de uma antena medida.

## Desenvolvimento e validação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/visual_check.py
.\.venv\Scripts\python.exe -m tilt --database .artifacts/smoke.sqlite3 --smoke-test
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
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
tilt/window.py         bancada, catálogo, projetos e exportações
tilt/visuals.py        ilustrações e gráficos vetoriais Qt
tilt/reports.py        memória HTML, CSV e JSON
tilt/data/cables.json  catálogo portátil com origem e SHA-256
tests/                regressão numérica, persistência e interface
```

Os dados de trabalho e executáveis ficam fora do Git. O logo foi adotado por
instrução do usuário; não foi redesenhado. Antes de redistribuição a terceiros,
confira os direitos do catálogo e os termos de distribuição do Qt/PySide6.
