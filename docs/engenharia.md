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

## Espaçamento automático e compatibilidade

O aplicativo inicia com `d = λ₀ = c/f`, no espaço livre. A distância em mm
é atualizada ao trocar frequência, canal, deslocamento OFDM ou constante c.
O fator de velocidade só entra em λg e nos comprimentos de alimentação.
No modo automático, mudar a frequência também muda d e, portanto, ΔL.
Editar a distância desliga o acompanhamento automático; marcá-lo novamente
restaura 1 λ. A opção é uma conveniência de preenchimento, não uma otimização
de ganho, nulos ou lóbulos de grade.

A UI preserva até nove casas decimais em mm no preenchimento automático.
O payload de projeto permanece na versão 1 e ganha a chave opcional
`spacing_auto`. Ausência dessa chave significa **manual**, preservando os
espaçamentos de revisões anteriores e dos exemplos das planilhas.

## Diagramas verticais e precisão numérica

O motor RF 1.2 mantém as equações e os casos das planilhas. Usa somas compensadas
(`math.fsum`) para potência e componentes de campo/coerência. A avaliação do
diagrama aceita sequências ou iteradores de ângulos, rejeitando não finitos e
elevações fora de −90° a +90°.

O fator de campo usa `|Σ aᵢ exp(jψᵢ)| / Σ aᵢ`, convertido por `20 log10`, com
piso de −60 dB. A referência é o limite coerente das amplitudes de cada curva,
não o maior ponto amostrado na janela. Alterar o eixo X nunca renormaliza níveis.
O caso sem tilt mantém as amplitudes e zera as fases; o caso ideal remove apenas
o arredondamento dos comprimentos e recalcula suas perdas.

A grade considera abertura em comprimentos de onda e largura angular: ao menos
1801 pontos e 32 amostras por ciclo espacial mais rápido, limitada a 12001 pontos,
mais as direções solicitada e ajustada. Arranjos extremos exibem aviso quando
atingem esse limite. Reduzir a faixa aumenta a resolução angular. As métricas de
fase, coerência e progressão após corte são independentes dessa amostragem visual.

O gráfico é exclusivamente vertical; o eixo é **elevação**, com zero no horizonte
e ângulos negativos abaixo dele. O tilt positivo de entrada aparece em elevação
negativa. A faixa é uma preferência de visualização e não modifica o projeto RF.

Na aplicação 1.3 o padrão inicial é o dipolo vertical de meia onda (aproximação
analítica, fio fino, espaço livre). Em elevação `e`, medida a partir do horizonte:

```text
F_elemento(e) = cos[(π/2) sin(e)] / cos(e)
F_total(e) = F_elemento(e) × AF(e)
F_elemento(±90°) = 0; F_elemento(0°) = 1
```

Próximo aos polos, usa-se a forma equivalente
`sin[(π/2) cos²(e)/(1+|sin(e)|)]/cos(e)` para evitar cancelamento numérico.
O valor zero físico é mostrado no piso de −60 dB. O padrão completo não é
renormalizado ao pico amostrado: mantém o máximo do elemento igual a 1 e a soma
coerente das amplitudes como referência. O pico pode diferir do tilt da progressão.
A multiplicação não desloca os nulos do dipolo quando o tilt elétrico é aplicado.
O fator de arranjo isotrópico continua disponível em uma subaba técnica; seus
máximos em ±90° para d=λ e tilt zero não são erros de seno/cosseno.
Não há supressão artificial de outros lóbulos. Base do elemento:
[Antenna Theory, dipolo de meia onda](https://antenna-theory.com/antennas/halfwave.php).

## Medida de fabricação e potência por trecho

Novos projetos usam `length_reference=shield_edges`: comprimento ao longo do
cabo entre extremidades da blindagem (malha a malha), ou condutor externo da
linha rígida, excluindo pontas expostas e conectores. Atrasos das terminações
são considerados iguais; conectores/transições desiguais exigem medição e
compensação externa. Não é comprimento total do condutor central ou do conjunto
com conectores. Guardam-se `Li − Li−1` e `Li − L1` após quantizar cada comprimento.

`LineSpecification` é congelada no cálculo. Contém modelo, tipo, frequência,
impedância, VF de catálogo, potência média interpolada, pico, tensão de pico,
amostras de suporte `(MHz, dB/100m, kW)`, método, fonte e SHA-256. Exports e
salvamento usam esse objeto, sem consultar novamente o catálogo.

```text
P_entrada_ramal = Pin/N × 10^[-α Lcomum / 1000]
Margem_ramal = Pmédia_catálogo − P_entrada_ramal
Margem_comum = Pmédia_catálogo − Pin  (se houver linha comum)
Pin_máx = Pmédia_catálogo            (com linha comum do mesmo modelo)
Pin_máx = N × Pmédia_catálogo        (sem linha comum)
```

Não se descontam perdas extras da verificação porque sua localização é
desconhecida. O limite de entrada acima considera somente o material; divisor,
conectores e condições da instalação não são certificados. `Avpower` e
`PeakPower` vêm em kW e são convertidos para W. Pico não substitui limite médio;
a condição de pico fica pendente sem fator de crista. O XML não informa condições
de temperatura/altitude/ROE. Modelo personalizado sem rating fica indisponível.

O snapshot JSON passa à versão 2, ainda no mesmo esquema SQLite (user_version=1):
resultados, material, fabricação em mm e metadados do diagrama/faixa. As revisões
continuam imutáveis. Payloads antigos sem `element_pattern` ou `length_reference`
usam isotrópico e planos elétricos de referência, evitando reinterpretar medidas
antigas como malha a malha. A UI informa essa condição e permite escolher o novo
modelo antes de recalcular; o histórico não é reescrito.

## Divisor central e comprimentos por lambda — 1.4.0

Fonte: `Calculo de cabos para antena fm.ods`, aba `Plan1`, SHA-256
`3d45fa6cd20bac11e39c8a39864fad7f331b8ccaf609715a0442ee3a62599bc1`.
Foram lidos valores e fórmulas do XML ODS, sem executar macros ou instruções do arquivo.

| Células | Grandeza |
| --- | --- |
| D2 / D3 | 105,3 MHz / VF 0,87 |
| G2 | `300000 / D2 × D3`, λg em mm = 2478,63247863248 |
| H2 | G2 / 4 = 619,65811965812 mm |
| B6:B7 | 2 elementos: 3098,2905982906 mm nos dois ramais |
| B10:B13 | 4 elementos: 5576,92307692308; 3098,2905982906; 3098,2905982906; 5576,92307692308 mm |
| B16:B21 | 6 elementos: 8055,55555555556; 5576,92307692308; 3098,2905982906; sequência simétrica |

A tabela auxiliar K6:P11 distingue RGC213 (0,82), LCF12 (0,88), SCF12/RFS
(0,77), LCF12/RFS (0,87), SCF12/KING (0,83) e LCF78/KING/DATALINK (0,88).
São referências da planilha, sem substituição automática do catálogo ADT-PY.
O exemplo reproduz especificamente o VF 0,87 de D3; outros valores podem ser
informados no campo de VF. O número OP-3405 e células auxiliares sem vínculo com
as tabelas de ramais não são tratados como parâmetros RF.

`feed_layout=center` é novo; `progressive` preserva o cálculo anterior.
Para índices `i=0…N−1`, E1 inferior e divisor a `zc=q×d`, `q=(N−1)/2`:

```text
λ₀ = c/f                       λg = VF × λ₀
base_i = (ceil(|i − q|) + 0,25) × λg
correção_i = −(i − q) × VF × d × sen(tilt)
percurso_mínimo_i = |(i − q) × d| + folga
ideal_i = base_i + correção_i + k_i × λg
```

`k_i` é o menor inteiro não negativo que respeita o percurso mínimo antes e
depois do arredondamento de corte, acrescido da reserva de ondas informada.
O corte usa o mesmo arredondamento ao passo do motor anterior. O planejamento
limita a um milhão as ondas necessárias ao alcance para rejeitar combinações
numericamente inadequadas de VF, frequência e percurso.

Os casos 2/4/6 sem tilt reproduzem a ODS quando o alcance não exige extensão.
O espaçamento não aparece na planilha: 1 λ₀ é o padrão explícito do aplicativo,
editável em mm ou como múltiplo de λ₀. Folga, tilt, 2–64 elementos e quantidades
ímpares são extensões. Em quantidade ímpar, o elemento no centro usa base 0,25 λg.
O percurso segue a distância vertical mais a folga fornecida; não reconstrói
curvas, obstáculos, conectores nem raio mínimo do cabo.

Fase física relativa = `−360° (L_i − L_0)/λg`. Removem-se voltas inteiras para
expressá-la em torno da progressão solicitada, conservando o erro de corte.
O ajuste de tilt usa essa fase equivalente, e não regressão sobre comprimentos
que diferem por λg inteiros. As perdas sempre usam o comprimento físico completo.
Sem tilt e sem arredondamento, todos os ramais têm a mesma fase, mesmo com
comprimentos diferentes. A coerência pode cair por perdas desiguais e quantização.

Essa equivalência vale na frequência calculada. Cada volta acrescenta atraso
real, podendo alterar o diagrama em outras frequências. Supõem-se saídas do
divisor em fase e terminações iguais. A parcela λg/4 reproduz a referência e
não valida casamento de impedância ou um transformador de quarto de onda.

Persistência: entradas versão **2**, snapshot versão **3**, motor **1.4.0**.
O esquema SQLite permanece `user_version=1`, com novas propriedades no JSON.
`result.center_feed` conserva altura do divisor, fração de fase e, por ramal,
posição, percurso mínimo, base, correção e ondas adicionadas. `result.elements`
conserva ideal, corte, diferenças, fase e potência. Snapshot e CSV incluem a
decomposição; PDF e tela usam o mesmo resultado congelado. Entradas versão 1
continuam aceitas e campos ausentes usam `progressive`, folga zero e reserva zero.
Revisões históricas não são reescritas. A interface salva também `spacing_factor`.

Fixture: `tests/fixtures/fm_center_reference.json`, valores ODS em mm, tolerância
absoluta de `1e-8 mm`. Testes independentes propagam os fasores pelos cabos
físicos e pelo espaço livre para verificar a coerência no tilt solicitado.

## Relatório e impressão

O PDF A4 usa os últimos resultados calculados, com metadados, entradas, tabela
completa, equações, avisos, corte vertical completo e detalhado, esquema e hash
do catálogo. Na faixa completa, a segunda figura amplia ±10° em torno do tilt;
quando o usuário aplica outra faixa, ela é respeitada no relatório.

O PDF original contém texto vetorial e figuras com o dobro da resolução de
renderização. A prévia e a impressão leem suas páginas com QtPdf, preservando
proporções, intervalo, ordem e cópias. A renderização para a impressora é limitada
a 200 dpi por página para limitar memória; o PDF original permanece inalterado.
O relatório é salvo antes de abrir a prévia. Cancelar o diálogo não imprime;
ausência de impressora preserva a geração/visualização do PDF.

Referências de implementação:
[Qt, prévia e impressão](https://doc.qt.io/qtforpython-6/PySide6/QtPrintSupport/QPrintPreviewDialog.html),
[Qt, impressora padrão](https://doc.qt.io/qtforpython-6/PySide6/QtPrintSupport/QPrinterInfo.html),
[Qt, intervalos e cópias](https://doc.qt.io/qt-6/qprinter.html).

## Limites físicos

- Padrão exibido: elemento analítico escolhido × fator de arranjo, em dB de campo.
- Sem ganho absoluto, diagrama individual medido, cobertura, terreno ou análise regulatória.
- Sem acoplamento, descasamento, dispersão medida, efeito da torre ou tolerância de VF.
- Ramal mínimo escolhido pelo usuário; as ilustrações não verificam roteamento mecânico.
- Linhas rígidas exigem modelagem/medição de descontinuidades e transições.
- Validar comprimentos elétricos em analisador de redes antes da fabricação definitiva.

Base técnica complementar:
[Analog Devices, fator de arranjo](https://www.analog.com/en/resources/analog-dialogue/articles/phased-array-antenna-patterns-part1.html),
[Analog Devices, lóbulos de grade e atraso real](https://www.analog.com/en/resources/analog-dialogue/articles/phased-array-antenna-patterns-part2.html).
