# Instalação e publicação Windows

## Usuário final

Em [Releases](https://github.com/Gecesars/tilt/releases/latest), baixe
**`EFTX_Tilt-1.3.2-Setup-x64.exe`**. Abra o arquivo, leia e aceite os termos EFTX,
confirme a pasta e conclua. Abra **EFTX Tilt Desktop** pelo menu Iniciar ou pelo
atalho na área de trabalho. Uso restrito à EFTX e a usuários autorizados por
escrito, conforme `LICENSE.txt`.

Requer **Windows 10 1809 ou posterior (build 17763+), x64**, ou Windows 11 x64.
O instalador é offline e inclui Python 3.12.10, Qt/PySide6 6.11.2, Qt PDF,
SQLite, catálogo de cabos, logo e as DLLs redistribuíveis Visual C++ necessárias.
Não é necessário instalar Python, Qt, .NET ou Visual C++ separadamente.
As APIs de sistema, UCRT e ICU são fornecidas pelo próprio Windows.
Leia a [base técnica e os limites de validação](windows_compatibilidade.md).

Instalação por usuário, sem serviço ou tarefa agendada. Pasta padrão:
`%LOCALAPPDATA%\Programs\EFTX\Tilt-Desktop`. O EXE usa NSIS e não chama o MSI
nem depende do Windows Installer. Uma instalação MSI anterior pode permanecer:
as pastas e os atalhos são separados, mas os projetos continuam no mesmo banco
`%LOCALAPPDATA%\EFTX\EFTX Tilt\tilt.sqlite3`. Feche as versões anteriores antes
de usar a nova. Não escolha a pasta antiga do MSI para o novo instalador.

Para restaurar arquivos, feche o aplicativo e execute o EXE novamente na mesma
pasta. Para remover, use **EFTX Tilt Desktop** em Aplicativos Instalados do
Windows ou o atalho **Desinstalar**. A remoção preserva o banco e arquivos extras
que você colocou na pasta. Faça backup do banco separadamente.

O ZIP portátil contém o mesmo aplicativo: extraia toda a pasta antes de executar
`EFTX_Tilt.exe`. Não há atualização automática. Bibliotecas Qt/PySide são
substituíveis conforme `licenses/SOURCES.md`; reinstalar restaura os originais,
por isso preserve suas modificações antes de reinstalar.

Após ler os termos e obter autorização, instalação silenciosa:

```powershell
.\EFTX_Tilt-1.3.2-Setup-x64.exe /S /ACCEPTEULA=1
```

Sem `/ACCEPTEULA=1`, a instalação silenciosa retorna 1603 sem instalar.
O parâmetro declara aceite; não é chave de ativação. A interface completa exige
marcar a caixa da licença. Para pasta personalizada, `/D=C:\Pasta escolhida`
deve ser o último argumento, sem aspas, conforme a sintaxe NSIS.

Compare o SHA-256 com `SHA256SUMS.txt` da mesma release:

```powershell
Get-FileHash .\EFTX_Tilt-1.3.2-Setup-x64.exe -Algorithm SHA256
```

O instalador e o aplicativo não têm assinatura digital de editor. O hash
confere integridade; não substitui assinatura nem dispensa políticas locais.

## Manutenção

Requer Windows x64, Python 3.12 e dependências de desenvolvimento:

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
powershell -ExecutionPolicy Bypass -File .\build_setup.ps1
```

O build baixa o compilador portátil **NSIS 3.12** para `build/tools`, somente
se necessário, e exige SHA-256 fixado em `tools/fetch_nsis.py`. SourceForge é
a origem primária; o espelho MacPorts fornece o mesmo arquivo verificado.
Não instala o compilador no sistema. O computador de destino não precisa de rede.

O aplicativo fica em `dist/release/1.3.2/EFTX_Tilt`. Licença RTF, ícone EFTX,
inventário SHA-256 e listas explícitas de instalação/remoção ficam em
`build/installer/1.3.2`. O EXE fica em `dist/`. Use `-SkipApplicationBuild`
somente quando o payload não mudou. A compilação NSIS usa UTF-8 explícito e
trata avisos como erros. `build_installer.ps1` e WiX permanecem como referências
para os MSIs históricos; a distribuição 1.3.2 usa EXE.

O pacote consolida a cópia mais recente de cada DLL MSVC incorporada pelo
Python/Qt em `_internal`. A busca do empacotador não usa dependências de outros
aplicativos no PATH. Qt Virtual Keyboard/QML/Quick não utilizados ficam excluídos.
Licenças e fontes de terceiros acompanham o pacote, inclusive NSIS.

## Verificação antes da publicação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File .\tools\test_setup.ps1
.\.venv\Scripts\python.exe tools/package_release.py
git diff --check
```

O teste exige ausência da instalação e dos atalhos EXE; use uma conta de teste
quando necessário. Instala em pasta exclusiva com espaços dentro de `.artifacts`,
compara todos os arquivos com o inventário, verifica o atalho e executa o programa
nos plugins Qt offscreen e Windows. Limpa referências Python/Qt do ambiente e
limita PATH ao Windows. O diagnóstico registra o caminho real das DLLs carregadas
e rejeita runtime Python/Qt/MSVC/SQLite fora da pasta instalada. Gera PDF e prévia,
remove um arquivo próprio para testar reinstalação e desinstala o produto testado.
Verifica preservação dos dados reais, atalhos EFTX anteriores e arquivo extra.

Os JSONs de diagnóstico contêm caminhos locais e ficam fora do Git. A opção
`--smoke-diagnostics arquivo.json` exige `--smoke-test`; não coleta dados no uso
normal. O CI também constrói e testa o EXE em um runner Windows separado;
`windows-latest` é Windows Server, não validação em Windows 10 cliente.

`package_release.py` confere o payload contra o inventário, gera o ZIP, valida
CRC e SHA-256 de cada entrada e escreve `SHA256SUMS.txt`. Publique EXE, ZIP,
licença, avisos e hashes na tag do commit com CI aprovado. Não substitua os bytes
de uma release publicada; incremente a versão. Não publique bancos ou logs privados.

Evidências executadas: [validacao.md](validacao.md). O erro específico do MSI
relatado pelo usuário não foi reproduzido sem sua mensagem/log; o EXE oferece
uma instalação independente dessa tecnologia.