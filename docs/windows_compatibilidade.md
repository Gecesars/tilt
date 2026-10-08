# Compatibilidade Windows — EFTX Tilt 1.4.1

## Plataforma de destino

Aplicativo, ZIP portátil, instalador MSI e EXE auxiliar são destinados a **Windows 10 versão
1809 ou posterior, x64 (64 bits)**, e Windows 11 x64. O mínimo é o build 17763.
Windows 10 22H2 (19045), LTSC 2019 (17763) e LTSC 2021 (19044) estão dentro dessa
faixa. Windows 7/8/8.1, Windows 10 anterior a 1809 e processos x86 de 32 bits
não são suportados por este pacote. Não há homologação de emulação x64 em ARM.

Base técnica, consultada em 07/10/2026:

- [Qt 6.11 para Windows](https://doc.qt.io/qt-6.11/windows.html): Windows 10 1809+
  x86_64 e Windows 11. O projeto fixa PySide6/Qt **6.11.2**.
- [Python 3.12 no Windows](https://docs.python.org/3.12/using/windows.html):
  Windows 8.1 ou posterior. O Python incorporado é **3.12.10 x64**; o mínimo
  efetivo do aplicativo é o requisito mais restritivo do Qt.
- [Universal CRT](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment):
  UCRT faz parte do Windows 10/11 e o sistema usa sua própria cópia.
- [Windows API sets](https://learn.microsoft.com/en-us/windows/win32/apiindex/windows-apisets):
  contratos de APIs resolvidos pelo carregador do Windows.

Isso define o alvo de compatibilidade e não substitui execução em uma máquina
Windows 10. O estado dos testes está separado abaixo.

## Ajustes do pacote

1. `EFTX_Tilt.spec` limita a busca de DLLs ao ambiente Python e ao Windows.
   DLLs de Poppler/libheif ou de outros programas no PATH não entram na release.
2. UCRT, API-set forwarders e ICU do sistema não são copiados para o pacote.
   O Windows fornece esses componentes. Bibliotecas Visual C++ redistribuíveis
   e bibliotecas necessárias do Python/Qt permanecem incluídas.
3. O backend OpenSSL opcional do Qt foi excluído. Qt Network mantém Schannel,
   fornecido pelo Windows. As bibliotecas OpenSSL próprias do Python permanecem.
   A aplicação não solicita instalação de bibliotecas adicionais pelo usuário.
4. O MSI lê `CurrentBuildNumber` do Registro na visão de 64 bits e exige
   build >= 17763. Instala por usuário, sem .NET ou download de pré-requisitos.
   O EXE auxiliar incorpora e abre o mesmo MSI.
5. O aplicativo verifica o build real reportado pelo Python e a arquitetura do
   processo antes de importar Qt, incluindo a distribuição portátil. Sistemas
   abaixo do mínimo recebem uma mensagem de requisito, em vez de tentar carregar
   as bibliotecas Qt. O manifesto do executável inclui o identificador Windows 10.
6. As DLLs MSVC incorporadas pelo Python/Qt são consolidadas na pasta de busca
   inicial `_internal`. O teste instalado limpa o PATH e registra os módulos
   carregados, rejeitando runtime redistribuível externo à pasta do aplicativo.

## Estado da validação

O ambiente disponível em 07/10/2026 é **Windows 11 x64, build 26300**. Testes
unitários cobrem os limites de versão/arquitetura, mas simular esses valores não
equivale a executar o aplicativo em Windows 10. Nenhuma VM Windows 10 disponível
foi encontrada nas ferramentas locais de virtualização.

A suíte, os testes locais do EXE e as evidências de empacotamento estão em
[validacao.md](validacao.md). CI `windows-latest` também não representa Windows 10.
O teste real em Windows 10 continua pendente e não é apresentado como homologado.

Para completar a homologação em Windows 10 x64, registrar `winver`, instalar o
EXE, abrir projetos/catálogo, calcular cabo e linha rígida, visualizar diagramas,
salvar/reabrir SQLite, gerar PDF, abrir prévia e testar reinstalação/desinstalação
preservando o banco. Preferir uma máquina sem Python, Qt ou ferramentas de
desenvolvimento instaladas. Impressão física depende também do driver disponível.
