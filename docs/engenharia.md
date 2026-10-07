# Memória de engenharia e rastreabilidade

## Fontes inspecionadas em 07/10/2026

| Fonte | SHA-256 |
|---|---|
| `calculo de tilt eletrico no cabo.xls` | `a011fcc63916e8aec6caca7a320c3d197ed5e4346a8718d3658fccb16a5e180b` |
| `calculo de tilt eletrico na linha rigida.xls` | `0839e84841eecbaa1a5eeaddedfdd2b85c8e344403e7215789982cf5d4d4b76a` |
| `CableRating.xml` do ADT-PY indicado | `22af366649dbec9f843de82cef7e0e4d7029b129790c066f32cd8e376af5725e` |
| `logo_eftx_novo.jpeg` fornecido pelo usuário | `e6209b8b2834a823b59ed18a29ce0b41ca53959194e1b468da0dc5d961422bc9` |

As planilhas foram abertas somente para leitura. As células e fórmulas BIFF
foram extraídas por `tools/inspect_sources.py`; nenhum conteúdo foi tratado
como instrução de execução. As abas Plan2/Plan3 estão vazias.

## Paridade com Plan1

| Entrada/saída | Cabo | Linha rígida |
|---|---:|---:|
| D5: frequência (MHz) | 623 | 107,7 |
| D7: espaçamento (mm) | 1960 | 2771,5877437325903 |
| D9: tilt (graus) | 2 | 5 |
| D11: VF | 0,88 | 0,995 |
| D15: fase (graus) | 51,13809292018786 | 31,219187052211154 |
| D17: diferença (mm) | 60,194651912473674 | 240,35198945334338 |

Fórmulas originais comuns:

```text
I5  = 300000 / D5               (λ₀ em mm, frequência em MHz)
F9  = D9 × 2 × PI() / 360
I11 = I5 × D11
D15 = 360 × D7 / I5 × SIN(F9)
D17 = I11 × D15 / 360
```

No cabo: `D24 = D7/2 + 50 = 1030 mm` (inferior) e
`D22 = D24 − D17 = 969,8053480875263 mm` (superior).
O exemplo da aplicação usa esse último como ramal mais curto, sem arredondamento.

Na rígida, `D7 = I11`. `K16 = D17/4` é uma célula sem identificação suficiente
da geometria mecânica. O aplicativo não presume um fator de quatro no curso de
um ajuste telescópico. O exemplo usa ramal mínimo arbitrário de 1 m, declarado
na entrada; esse comprimento não veio da planilha. O VF 0,995 desse exemplo
é preservado e não confundido com 0,998 das linhas rígidas do catálogo ADT.

Os rótulos das planilhas para LCF12/SCF12 não identificam sempre a mesma
marca/variante. O aplicativo importa os modelos completos do XML e não funde
variantes apenas por semelhança do nome. O modo personalizado reproduz os VFs
das planilhas sem inventar suas atenuações.

## Progressão e convenção

Posições `zᵢ = i d`, `i = 0…N−1`, E1 embaixo. Tilt θ positivo é downtilt.
`ΔL = VF d sen θ`. Use `Lᵢ = Lmin + max(j ΔL) − i ΔL`.
O deslocamento comum mantém todos os comprimentos não negativos e não muda o feixe.
Os comprimentos não são reduzidos módulo λg, preservando atraso real.

Com convenção de fase do campo `exp(j k z sen ε)`, a fase de alimentação é
`φᵢ = −2π(Lᵢ − L₀)/λg`. Portanto o máximo ideal ocorre em elevação `ε = −θ`.
Comprimentos físicos são arredondados ao passo informado, com empate para cima.
Erros de fase e perdas usam os comprimentos arredondados.

O tilt da progressão após corte vem da regressão linear de L versus índice,
seguida de `asin(−inclinação / (VF d))`. Ele não é uma alegação de máximo único
do padrão. Lóbulos de grade são as outras soluções visíveis de
`sen ε = −sen θ + m λ₀/d`, `m` inteiro não nulo.

## Perdas e eficiência

O modelo é uma rede **paralela**, com divisor ideal de potência igual, ramais
individuais e uma linha comum opcional do mesmo tipo. Não representa uma
alimentação série por taps, um divisor com potências desiguais ou linhas mistas.

```text
Aᵢ = α × (Lcomum + Lᵢ)/100 + Aextra          [dB]
Pᵢ = Pin/N × 10^(−Aᵢ/10)                   [W]
ηalimentação = ΣPᵢ / Pin
Aequivalente = −10 log₁₀(ηalimentação)      [dB]
ηcoerência = |Σ aᵢ exp(j erroᵢ)|² / (N Σ aᵢ²)
```

`aᵢ` é a amplitude transmitida relativa. ηcoerência é avaliada no tilt
solicitado e separa o efeito da distribuição de amplitudes/erros do rendimento
de transmissão. Não é eficiência de radiação. Não se aplica fator cos(tilt)
inventado para representar perda de abertura.

`Aextra` é uma perda adicional total por caminho, incluindo inserção real do
divisor e conectores. A divisão ideal `1/N` não é perda térmica.
Potência nominal de catálogo é apenas referência; sem condições ambientais,
ROE e dados dos conectores, não existe certificação térmica ou de tensão.

## Catálogo e interpolação

47 modelos, 1669 amostras. A unidade XML `AttenuationdBm` é **dB/100 m**,
conforme o parser real do ADT, e não dBm de potência. `Avpower` e `PeakPower`
estão em kW; `PeakVol` em V; VF é adimensional.

Dentro de amostras adjacentes do próprio modelo:

```text
t = ln(f/fa) / ln(fb/fa)
y = exp(ln(ya) + t ln(yb/ya))
```

Aplica-se a α e potência média. Amostras exatas retornam o valor original.
Valores zero, caso existam, usam interpolação linear; nenhuma extrapolação é aceita.
O algoritmo legado de ponto mais próximo não é reutilizado. A tabela inteira
foi conferida contra os dados normalizados em testes.

## Frequência, canal e constante c

A tabela de conversão é geométrica e inclui canais TV históricos 2–69:
2–4: `57+6(ch−2)`; 5–6: `79+6(ch−5)`; 7–13: `177+6(ch−7)`;
14–69: `473+6(ch−14)` MHz. Não é uma base de destinação ou licenciamento.
O usuário escolhe explicitamente o modo canal ou frequência, evitando conflitos.
Deslocamento OFDM opcional: `+1/7 MHz`.

Referência histórica da tabela e deslocamento:
[DOU de 05/04/2010, documento disponibilizado pelo MME](https://www.gov.br/mme/pt-br/arquivos/do-05-04-2010-s1.pdf).
Esta referência é usada somente para conversão numérica, sem afirmar vigência
de obrigação regulatória.

As planilhas usam c = 300.000.000 m/s. A opção SI usa 299.792.458 m/s.
Mudar c ou f altera λ e fase, mas não ΔL para d, VF e θ constantes.

## Limites físicos

- Padrão exibido: fator de arranjo de elementos isotrópicos, normalizado em dB de campo.
- Sem ganho absoluto, diagrama individual, cobertura, terreno ou análise regulatória.
- Sem acoplamento, descasamento, dispersão medida, efeito da torre ou tolerância de VF.
- Ramal mínimo escolhido pelo usuário; as ilustrações não verificam roteamento mecânico.
- Linhas rígidas exigem modelagem/medição de descontinuidades e transições.
- Validar comprimentos elétricos em analisador de redes antes da fabricação definitiva.

Base técnica complementar:
[Analog Devices, fator de arranjo](https://www.analog.com/en/resources/analog-dialogue/articles/phased-array-antenna-patterns-part1.html),
[Analog Devices, lóbulos de grade e atraso real](https://www.analog.com/en/resources/analog-dialogue/articles/phased-array-antenna-patterns-part2.html).
