# Instalação e publicação Windows — 1.4.1

## Instalar ou atualizar

Baixe **EFTX_Tilt-1.4.1-Windows-x64.msi** em
[Releases](https://github.com/Gecesars/tilt/releases/latest). Feche o aplicativo,
abra o MSI, leia e aceite a licença EFTX e conclua. Abra **EFTX Tilt Desktop**
pelo menu Iniciar ou pela área de trabalho.

O MSI detecta MSIs anteriores do mesmo produto e as edições EXE 1.3.2/1.4.0 do
usuário atual. Reutiliza a pasta registrada. Na migração do EXE, remove somente
o registro e os arquivos administrativos do instalador antigo; o Windows
Installer passa a gerenciar o aplicativo. Um MSI mais antigo é bloqueado quando
uma versão mais nova já está instalada.

Pasta padrão: `%LOCALAPPDATA%\Programs\EFTX\Tilt-Desktop`. O banco permanece em
`%LOCALAPPDATA%\EFTX\EFTX Tilt\tilt.sqlite3` e não faz parte do pacote:
atualização, reparação e desinstalação o preservam. Arquivos extras do usuário
também não fazem parte da lista de remoção. Os arquivos próprios do aplicativo
são restaurados; guarde separadamente modificações nas bibliotecas.

O **EXE auxiliar** contém o mesmo MSI e abre o mesmo assistente. Atende ao
atualizador 1.4.0, que só reconhecia EXE. Não cria uma instalação independente.
O aplicativo 1.4.1 prefere baixar MSI. Para reparar ou remover, use **Aplicativos
instalados** do Windows ou abra novamente o MSI da mesma versão. Guarde o MSI
para reparação. O EXE auxiliar mantém uma cópia em
`%LOCALAPPDATA%\EFTX\Installers\1.4.1`.

## Requisitos

Requer **Windows 10 1809 ou posterior, x64**, ou Windows 11 x64. Inclui Python
3.12.10, PySide6/Qt 6.11.2, Qt PDF, SQLite, catálogo, logo e runtime MSVC.
Não exige instalar Python, Qt, .NET ou Visual C++ separadamente, nem baixar
dependências durante a instalação. UCRT e APIs de sistema vêm do Windows.
Veja [compatibilidade e limites dos testes](windows_compatibilidade.md).

Não há assinatura digital de editor. Confira o SHA-256 com `SHA256SUMS.txt` da
mesma release; hash não substitui assinatura. O ZIP portátil contém o mesmo
app: extraia tudo, mantendo `_internal`, licenças e avisos. Aceitar atualização
na edição portátil abre o instalador por usuário, sem substituir a pasta extraída.

## Uso silencioso autorizado e diagnóstico

Após ler os termos e obter autorização de uso:

```powershell
msiexec /i "EFTX_Tilt-1.4.1-Windows-x64.msi" /qn /norestart EFTX_ACCEPT_LICENSE=1 /L*v "$env:TEMP\EFTX-install.log"
# Alternativa compatível com o atualizador antigo:
.\EFTX_Tilt-1.4.1-Setup-x64.exe /S /ACCEPTEULA=1
Get-FileHash .\EFTX_Tilt-1.4.1-Windows-x64.msi -Algorithm SHA256
```

Sem aceite explícito, o modo silencioso retorna 1603. O parâmetro declara aceite,
não é chave de ativação. Na primeira instalação, `INSTALLFOLDER="C:\Minha pasta"`
permite um caminho personalizado; a atualização conserva o caminho registrado.
Código 3010 indica reinicialização necessária; `/norestart` impede reinício automático.

Feche o app antes de instalar silenciosamente. O MSI detecta arquivos em uso,
sem encerramento forçado do aplicativo. Pelo atualizador antigo, o EXE espera até
60 s pelo PID informado antes de iniciar o MSI. Log do EXE:
`%TEMP%\EFTX_Tilt-1.4.1-install.log`. Log do atualizador MSI:
`%LOCALAPPDATA%\EFTX\EFTX Tilt\logs`.

## Falha de cópia 1.4.0

A leitura de `/WAITPID=` opcional no NSIS podia deixar o indicador de erro ativo
quando o parâmetro não existia. O teste seguinte de cópia interpretava esse
indicador antigo como falha, mesmo após copiar o arquivo. Um teste mínimo
reproduziu o comportamento. A versão 1.4.1 usa a cópia transacional do MSI;
os caminhos NSIS preservados também limpam o indicador antes da cópia.
Falhas de disco, permissões ou arquivos em uso devem ser diagnosticadas pelo log.

Referências: [GetOptions](https://nsis.sourceforge.io/GetOptions),
[IfErrors](https://nsis.sourceforge.io/Reference/IfErrors),
[ClearErrors](https://nsis.sourceforge.io/Reference/ClearErrors),
[MajorUpgrade WiX](https://docs.firegiant.com/wix/schema/wxs/majorupgrade/).

## Compilar e testar

O desenvolvimento requer Windows x64, Python 3.12 e SDK .NET compatível com WiX.
O .NET é necessário somente no computador que compila.

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
powershell -ExecutionPolicy Bypass -File .\build_setup.ps1
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File .\tools\test_installer.ps1 -CheckUpdates
powershell -ExecutionPolicy Bypass -File .\tools\test_installer.ps1 -UpgradeFrom 1.3.1
powershell -ExecutionPolicy Bypass -File .\tools\test_installer.ps1 -FromExe 1.4.0
powershell -ExecutionPolicy Bypass -File .\tools\test_installer.ps1 -FromExe 1.4.0 -UseBridge
.\.venv\Scripts\python.exe tools/package_release.py
git diff --check
```

`build_setup.ps1` gera aplicativo, MSI WiX 5.0.2 e EXE auxiliar NSIS 3.12. O NSIS
portátil é baixado com hash fixado. Use `-SkipApplicationBuild` somente quando
o aplicativo e seus arquivos distribuídos não mudaram. Payload:
`dist/release/1.4.1/EFTX_Tilt`. Inventário: `build/installer/1.4.1`. Pacotes: `dist/`.

O teste exige ausência de instalações e atalhos EFTX; use uma conta de teste.
Confere todos os hashes, Qt offscreen/Windows com PATH limpo, divisor central,
SQLite, PDF, reparação, remoção e preservação de dados/arquivos extras. As versões
antigas devem estar em `dist/`. O CI baixa fixtures oficiais com hashes fixados.
`-CheckUpdates` consulta e baixa a release, mas nunca executa o download recebido.

`package_release.py` compara payload e inventário, verifica CRC e hashes do ZIP
e gera `SHA256SUMS.txt`. Publique MSI, EXE auxiliar, ZIP, licença, avisos e hashes
na tag validada. Não publique bancos nem logs locais privados.
Evidências e limitações: [validacao.md](validacao.md).
