# Instalação e publicação Windows

## Usuário final

Em [Releases](https://github.com/Gecesars/tilt/releases), baixe
`EFTX_Tilt-1.3.0-Windows-x64.msi`. O assistente em português apresenta os termos
EFTX e solicita aceite. Uso permitido somente para EFTX e pessoas/organizações
autorizadas por escrito, conforme `LICENSE.txt`.

Instalação por usuário, sem serviço ou tarefa agendada. Pasta padrão:
`%LOCALAPPDATA%\Programs\EFTX\Tilt`. Atalhos: menu Iniciar, área de trabalho e
licença no menu EFTX. Use Aplicativos Instalados do Windows para reparar/remover.
O MSI não inclui nem remove os projetos em
`%LOCALAPPDATA%\EFTX\EFTX Tilt\tilt.sqlite3`; faça backup desse arquivo separadamente.
Arquivos extras que você colocar na pasta do programa não são removidos.

Após ler os termos e obter autorização, instalação silenciosa:

```powershell
msiexec /i EFTX_Tilt-1.3.0-Windows-x64.msi /qn /norestart EFTX_ACCEPT_LICENSE=1
```

Sem essa propriedade, instalações com interface reduzida ou silenciosas são
bloqueadas. Ela declara o aceite; não é chave de ativação. Na interface completa,
a caixa de aceite controla o avanço do assistente.

O ZIP portátil contém o mesmo aplicativo e avisos de licença. Extraia toda a
pasta antes de executar. Não há atualização automática. Feche o programa antes
de atualizar ou reparar seus arquivos. Bibliotecas Qt/PySide são compartilhadas
e substituíveis conforme `licenses/SOURCES.md`; reparação manual restaura os
originais, por isso preserve suas modificações antes de reparar.

Compare o SHA-256 do arquivo baixado com `SHA256SUMS.txt` publicado na mesma
release. O hash verifica integridade; não substitui assinatura digital de editor.
O MSI e o executável desta versão não estão assinados.

```powershell
Get-FileHash .\EFTX_Tilt-1.3.0-Windows-x64.msi -Algorithm SHA256
```

## Manutenção

Requer Windows x64, Python 3.12, dependências de desenvolvimento e SDK .NET com
runtime compatível. O manifesto local fixa WiX **5.0.2**, sob MS-RL, e a extensão
`WixToolset.UI.wixext/5.0.2`. Não se presume aceite de termos comerciais de outras
versões WiX. O aplicativo utiliza Qt/PySide 6.11.2 com os avisos LGPL e de terceiros
incluídos; o plugin GPL exclusivo Qt Virtual Keyboard, que não é utilizado, foi
excluído do pacote.

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
powershell -ExecutionPolicy Bypass -File .\build_installer.ps1
```

O script cria o aplicativo em `dist/release/1.3.0/EFTX_Tilt`, prepara licença RTF,
imagens derivadas do logo aprovado, inventário SHA-256 e componentes WiX em
`build/installer/1.3.0`, e gera o MSI em `dist/`. Para alterar somente o instalador
com o payload já existente, use `-SkipApplicationBuild`. A invocação direta da
DLL restaurada do WiX evita a perda de argumentos `-d` observada no dispatcher
de ferramentas do SDK .NET 10. A validação ICE permanece habilitada.

O UpgradeCode é fixo. ProductCode muda com a versão, e os GUIDs dos componentes
são estáveis por caminho. Não substitua uma release publicada com outro conteúdo
sob a mesma versão; incremente `tilt.__version__` antes de publicar uma revisão.
Versões mais antigas do MSI são bloqueadas quando uma mais recente está instalada.

`tools/update_license_notices.py` atualiza os textos de licença a partir de fontes
oficiais; `licenses/manifest.json` registra origem e hash. Revisar essas fontes e
versões ao mudar dependências, preservando avisos incorporados. `LICENSE.txt`
restringe apenas componentes próprios EFTX.

## Verificação antes da publicação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File .\tools\test_installer.ps1
git diff --check
```

O teste MSI exige que essa versão ainda não esteja instalada e que seus atalhos
não preexistam; prefira uma conta de teste. Instala em uma pasta exclusiva dentro
de `.artifacts/`, confere hashes, executa o aplicativo e a prévia PDF em Qt
offscreen/Windows, remove um arquivo próprio para testar reparação e desinstala
somente o ProductCode testado. Confere que os dados e atalhos preexistentes na
pasta EFTX não mudaram. Logs, PDFs, bancos de teste e resultados ficam nessa pasta.

Execute `.\.venv\Scripts\python.exe tools/package_release.py` para criar o ZIP
a partir do mesmo payload do MSI, conferir CRC e hashes e gerar `SHA256SUMS.txt`.
Publique ambos na tag correspondente ao commit da `main` com CI
aprovado. Não inclua SQLite, logs privados, credenciais ou arquivos de trabalho.
Evidências efetivamente executadas estão em [validação](validacao.md).
