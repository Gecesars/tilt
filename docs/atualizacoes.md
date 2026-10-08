# Atualizações pelo GitHub

## Fluxo de uso

- Consulta assíncrona três segundos após abrir, depois a cada 24 horas.
- Consulta manual em **Ajuda → Verificar atualizações…**.
- Somente releases estáveis e numericamente superiores à versão instalada.
  `1.10.0` é posterior a `1.9.0`; versões iguais, antigas e prévias não são oferecidas.
- O usuário autoriza o download. Pode cancelar ou continuar calculando.
- Após conferir o arquivo, **Salvar cálculo e instalar** recalcula os campos atuais,
  salva uma revisão no SQLite e abre o assistente. Entrada inválida, banco indisponível
  ou falha ao iniciar o instalador mantêm o aplicativo aberto.
- O aplicativo encerra após abrir o assistente; o instalador reaproveita a pasta registrada e
  conserva o banco. Mantém aceite da licença e interação normal do assistente.
- Ao terminar, abrir **EFTX Tilt Desktop**. Não há instalação silenciosa implícita.
- Erros na consulta automática não abrem modais; o menu permite tentar novamente.

Não há credencial GitHub, envio de projetos, banco ou campos RF. São feitos GETs
públicos para a API e o arquivo da release. GitHub recebe os metadados normais
de rede, incluindo IP e User-Agent com a versão do aplicativo.

## Contrato de distribuição e integridade

`tilt/updates.py` usa Qt Network e o backend **Schannel**, com TLS e certificados
do Windows. Não precisa de OpenSSL instalado no computador. Certificados inválidos
não são ignorados. Downloads usam HTTPS e só aceitam redirecionamento para
`github.com` ou `release-assets.githubusercontent.com`.

Endpoint fixo: `https://api.github.com/repos/Gecesars/tilt/releases/latest`.
Exige `draft=false`, `prerelease=false`, tag `vMAJOR.MINOR.PATCH` (ou sem `v`),
URL do repositório exato e um único asset `EFTX_Tilt-VERSAO-Windows-x64.msi`.
Na ausência de MSI, aceita `EFTX_Tilt-VERSAO-Setup-x64.exe` de releases anteriores.
Um MSI presente com metadados inválidos não permite fallback para EXE.
O asset deve estar `uploaded`, declarar tamanho de 1 a 512 MiB e
`digest=sha256:<64 dígitos hexadecimais>`. Metadados limitados a 1 MiB;
consulta limitada a 20 s, inatividade da transferência a 30 s e download total
a 30 minutos. Respostas inválidas não são executadas.

O arquivo é transmitido em blocos para uma pasta exclusiva no cache do usuário.
Tamanho, cabeçalho Windows e SHA-256 são conferidos ao terminar e antes de executar.
O SHA informado pelo próprio GitHub comprova integridade de transporte, não
substitui assinatura digital do editor nem protege contra comprometimento do
repositório. A distribuição continua sem assinatura digital.

O MSI é aberto pelo `System32/msiexec.exe` com `/i`, `/norestart` e log local,
sem shell ou argumentos recebidos da release. O assistente mantém o aceite da
licença e a detecção de arquivos em uso. Downloads cancelados, inválidos e
recusados são removidos; o instalador entregue fica no cache para reparação.

O EXE auxiliar 1.4.1 contém esse mesmo MSI para o atualizador EXE da edição 1.4.0.
Esse caminho continua aceitando `/WAITPID=<processo atual>`: aguarda até 60 s
antes de iniciar o MSI e aborta se o aplicativo não encerrar. Não aceita
silenciosamente a licença durante o fluxo normal do atualizador.

Fontes oficiais: [API de releases GitHub](https://docs.github.com/en/rest/releases/releases#get-the-latest-release),
[redirecionamento e timeout Qt](https://doc.qt.io/qt-6/qnetworkrequest.html),
[System plug-in NSIS](https://nsis.sourceforge.io/Docs/System/System.html).

## Reconstrução solicitada da release 1.4.0

O usuário pediu incluir o atualizador na mesma release. Os nomes do EXE e ZIP
continuam 1.4.0, com novos hashes e notas explícitas. A tag original `v1.4.0`
é preservada; o código da reconstrução é marcado por **`v1.4.0-update.1`** e
acompanha o asset **`EFTX_Tilt-1.4.0-Source.zip`**. Os arquivos automáticos
“Source code” da tag original correspondem à primeira edição; para esta
reconstrução, usar o asset de fontes ou a tag adicional.

A primeira edição não contém atualizador e precisa desta reinstalação manual
uma vez. A comparação futura continua estritamente por versão: uma nova
reconstrução de mesmo número não será oferecida automaticamente. Para futuras
atualizações, publicar uma versão maior, por exemplo 1.4.1.

## Validação

`tests/test_updates.py` cobre comparação, origem, assets incompletos, integridade,
limites, erro HTTP/TLS, timeout, cancelamento, consentimento, recusa, salvar antes
de iniciar e preservação do app quando o salvamento ou lançamento falha.

`tools/test_installer.ps1` instala o MSI, testa o app congelado, repara e desinstala.
`-FromExe 1.4.0 -UseBridge` verifica `/WAITPID` com o app antigo em execução.
`-CheckUpdates` também consulta e baixa a release
pública pelo aplicativo instalado, valida SHA-256 e remove o download; **nunca
executa o arquivo baixado nesse diagnóstico**. O parâmetro é opcional porque
depende da rede e do limite público de consultas do GitHub.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File .\tools\test_installer.ps1 -CheckUpdates
```

Evidência datada e limitações: [validação](validacao.md).
