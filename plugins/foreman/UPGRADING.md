# Histórico do plugin `foreman`

O que cada versão entregou e o que muda para quem atualiza. O arquivo vai junto com cada versão instalada: a skill `atualizar` lê o **Ao atualizar** de cada versão pulada, da mais antiga para a mais nova. Termine a entrega em andamento, ou pause-a, antes de atualizar o plugin (a skill `atualizar` confere). As ideias que ainda não viraram versão estão no [roadmap](../../docs/roadmap.md); o que é major, minor e patch, no [`CLAUDE.md`](../../CLAUDE.md#versão-e-release).

O fluxo nasceu inspirado no [ECC](https://github.com/affaan-m/ecc) (o pipeline `orch-*`, o `code-reviewer` e o `verification-loop`), em versão enxuta.

## 1.16.7 — head da entrega pela branch e uso por sessão

- **O head da entrega vem da branch que o `start` gravou** (defeito; um projeto do autor, foreman 1.16.0 a 1.16.6, decisão do dono): com o ledger na pasta principal, de volta à `main`, e a branch da entrega numa worktree, o `add`, o `claim` e o `status` liam o HEAD da `main` como head da entrega ("delivery head is now <main>"), e as worktrees de tarefa já integradas não apareciam como sobra. Agora o `start` grava a branch em que roda (quando não é a `--base`), e o head da entrega é o dessa branch; ledger sem branch gravada, ou com a branch apagada, segue lendo o HEAD da pasta do ledger. Número: runs com o head da `main` numa entrega em worktree (meta 0).
- **O uso da conta é gravado por sessão** (defeito; um app do autor, foreman 1.16.5, decisão do dono): duas contas no mesmo projeto gravavam o mesmo `usage.json`, e o `status` de uma sessão podia mostrar a semana da outra conta. Agora o mod grava `usage-<id da sessão>.json`, e o `ledger.py` lê o da própria sessão (`CLAUDE_CODE_SESSION_ID`), ou o `usage.json` quando ele não existe. Número: sessões com o uso de outra conta no `status` (meta 0).

**Ao atualizar:** nada muda. Uma entrega já começada não tem a branch gravada e segue lendo o HEAD da pasta do ledger até o próximo `start`. O `usage.json` antigo fica na pasta do ledger até a primeira gravação do mod novo e pode ser apagado depois dela. Sai o contorno de conferir o uso com `cc -l` com duas contas abertas no mesmo projeto.

## 1.16.6 — correções da vigia noturna

Defeitos vistos com dois projetos do autor no modo autônomo, numa noite.

- **`Touches:` em prosa não vira recurso** (defeito): uma linha como "`a.ts` (só leitura), o resto do módulo" fazia a frase virar um nome de recurso, e duas tarefas sem arquivo em comum colidiam no `claim`. Agora, num trecho com caminhos entre crases, só os caminhos contam. Número: colisões falsas no `claim` (meta 0).
- **O `add` diz o ciclo da própria run** (defeito): com uma run retida para o ciclo seguinte, o `add` que fechava o ciclo dizia o número do ciclo novo. Número: ciclos errados no texto do `add` (meta 0).
- **`gate.py --criteria <tarefa>` avisa só dos ids citados daquela tarefa** (defeito; a docstring já dizia isso): o aviso repetia os ids citados e não definidos do plano inteiro. Número: avisos de ids de outras tarefas (meta 0).
- **Uma pasta que guarda uma worktree não é sobra** (defeito): o `status` listava como sobra a pasta que contém as worktrees de um script do projeto e mandava parar os processos dela, com essas worktrees em uso. Número: sobras que contêm uma worktree viva (meta 0).
- **A margem de uso só conta o salto da mesma janela** (defeito): com duas contas no mesmo projeto, o salto de 8% para 55% entre o uso de uma e o da outra virava o custo de uma run, e o `status` mandava esperar 90 horas. Agora o `add` grava quando cada janela reinicia, e só contam os saltos entre runs da mesma janela. Ledgers antigos seguem legíveis: as runs gravadas antes da 1.16.6 só se comparam entre si, e um salto antigo sai da margem depois de cinco saltos novos. Número: esperas de uso sem consumo real (meta 0).
- **O `status` não pede o heartbeat de uma entrega parada à espera do dono** (defeito): o `autonomous.md` manda apagar o heartbeat quando nada anda sem o dono, e o `status` seguia dizendo "no tick for N min" e mandando recriá-lo. Agora o aviso some depois de uma nota `--validar` mais nova que o último tick, sem nada em voo, e enquanto a varredura de segurança, que espera o dono, é um passo. Número: avisos de heartbeat numa entrega parada para o dono (meta 0).

**Ao atualizar:** nada muda. Contornos que saem, se a sessão os tiver: escrever o `Touches:` só com caminhos; ignorar o aviso de ids citados do `gate.py --criteria`, a sobra de uma pasta com worktrees (como a das partes de um e2e) e a espera de uso que não veio de consumo; recriar o heartbeat numa entrega parada para o dono.

## 1.16.5 — `qa` e merge na worktree da entrega

- **O `qa` que testou o tip do dev não fica stale** (defeito): num projeto do autor, com a entrega numa worktree própria e o ledger na pasta principal, a run do dev de uma `fix-N` gravava como head o da `main`, que tinha andado; o `qa` que testou o commit da `fix-N` saía stale e o `status` pedia o `qa` de novo. Agora o `qa` só é stale quando nem o head nem o tip da última run do dev estão no commit testado. Número: `qa` stale sobre o tip do dev (meta 0).
- **`git merge` na worktree da entrega passa no modo autônomo** (defeito; mesmo projeto, foreman 1.16.0): `cd <worktree da entrega>; git merge --ff-only <tarefa>` era negado como merge na branch principal, porque o passo era lido também na pasta da sessão. Agora, depois de um `cd` absoluto para uma pasta que existe dentro de um repositório, numa cadeia só de `&&` e `;`, o passo é lido só nessa pasta; com `||`, pipe, subshell ou outro `cd` incerto, segue lido nas duas. Número: merges negados na worktree da entrega (meta 0).

**Ao atualizar:** nada muda. Contornos que saem, se a sessão os tiver: o `cherry-pick` no lugar do `git merge` na worktree da entrega; registrar de novo o `qa` que saiu stale sobre o tip da `fix-N`.

## 1.16.4 — frente não é sobra

- **O `status` de uma frente não lista a worktree e a branch dela como sobras** (defeito): num projeto do autor, com o ledger na worktree da entrega, o `status` pedia `git worktree remove` da própria worktree e `git branch -d` da própria branch assim que o head dela estava integrado, e a entrega não chegava ao gate. Agora a worktree do ledger e a branch dela contam como trabalho em andamento. Número: sobras que são a frente do próprio ledger (meta 0).

**Ao atualizar:** nada muda. Sai o contorno de copiar o ledger da frente para a pasta principal para chegar ao gate.

## 1.16.3 — worktree da entrega com claims fechados

- **O `add --full` lê a worktree da entrega mesmo depois de uma `fix-N` rodar nela** (defeito): num projeto do autor, os claims das `fix-N` nomeavam a própria worktree da entrega, e a 1.16.2 tratava toda worktree já nomeada por um claim como worktree de tarefa, voltando a ler a `main` e a recusar a suíte inteira. Agora só contam os claims em voo e os das entregas em preparação. Número: recusas do `--full` com "not in this history" numa entrega em worktree (meta 0).

**Ao atualizar:** nada muda. Sai o contorno de registrar a suíte inteira ou a reverificação sem `--full`/`--after-full`, com uma nota.

## 1.16.2 — `qa` com várias cópias e entrega numa worktree

- **O `add` de um `qa` libera todas as reservas das cópias dele** (defeito): os dois projetos do autor rotularam as cópias do `qa` como `qa-ciclo6` e `qa-full-1` a `qa-full-api`, e o `add` só liberava o rótulo `qa`; a reserva de um `qa` já terminado seguia renovada pelos comandos do projeto, segurando 4 GB do outro. Agora o `add` do `qa` libera `qa`, `qa-<n>` e `qa:<n>`, menos um rótulo que seja id de tarefa do ledger. Número: reservas de `qa` vivas depois do `add` dele (meta 0).
- **O `add --full` confere a entrega na worktree de onde é chamado** (defeito): num projeto do autor, a branch da entrega mora numa worktree e o ledger na pasta principal; o `add --full`, rodado na worktree da entrega, conferia o Reviewed e a Version na pasta principal (na `main`) e recusava a suíte inteira com "reviewed head ... is not in this history". Agora as duas checagens leem a worktree onde o comando roda quando o ledger é o da pasta principal e ela é do mesmo repositório e não é a worktree de uma tarefa; o ledger de uma frente segue lido na frente.

**Ao atualizar:** nada muda. Contornos que saem, se a sessão os tiver: rodar `liberar` para cada cópia do `qa`, ou usar só o rótulo `qa` puro; registrar a suíte inteira sem `--full`, com uma nota, quando a entrega mora numa worktree (rode o `add --full` e o `gate.py` de dentro da worktree da entrega).

## 1.16.1 — fila de memória por rótulo e revisão antes do add

- **Um projeto que segura uma reserva espera a vez para um trabalho novo** (defeito): o conserto do travamento na 1.16.0 isentava da fila todo projeto que já segurava qualquer reserva, então um app do autor, segurando a do `qa`, reservaria cópias novas à frente do pedido de um projeto de prioridade maior. A isenção vale agora só para a `manager:<tarefa>` de uma tarefa que o projeto já segura, a suíte que confere o relatório dela, porque sem ela a tarefa nunca liberaria a memória. Número: reservas novas concedidas com um pedido de prioridade maior na fila (meta 0). A decisão é rótulo por rótulo: num pedido misto, a `manager:<tarefa>` sai na hora e o trabalho novo segue na fila, sem perder o lugar.
- **A revisão do próprio commit do dev, gravada antes do `add` dele, vale** (defeito): num app do autor, o `reviewer` revisou o range da worktree da `fix-4` e foi gravado enquanto a suíte ainda conferia o commit; depois do `add` do dev, o `status` pediu a revisão de novo, e o registro repetido caiu no ciclo seguinte como revisão de outra tarefa. Agora, no ciclo aberto, a revisão cujo head é o `tip` de cada run do dev gravada depois dela conta para essas runs; vale para a rodada de correção (`fix-N`), que fica no ciclo aberto. Uma tarefa nova que abre o ciclo seguinte ainda precisa da revisão gravada depois do `add` dela.
- **A `reason` do `capacity --rotulo` mostra a conta com as reservas dos outros projetos** (defeito): num projeto do autor, o `capacity` reservou um rótulo de quatro e dizia "3 parallel copies fit", porque o texto mostrava a memória livre sem o desconto dos 8 GB que outro projeto reservava; a conta estava certa e o texto não. Agora a `reason` parte da memória que sobra para o projeto.
- **O `add` de uma revisão diz a rodada certa** (defeito): o PASS que fecha o laço da spec ou do plano dizia "round 0", porque a conta recomeça depois de um PASS; agora diz a rodada dele.

**Ao atualizar:** nada muda. Contornos que saem, se a sessão os tiver: gravar de novo, depois do `add` de uma `fix-N`, a revisão do `reviewer` sobre o tip dela, só para a ordem do ledger; ler os "pedidos" do `memoria.json` antes de cada `capacity --rotulo` e não reservar nada novo com um pedido de outro projeto na fila.

## 1.16.0 — memória mediada entre os projetos da máquina

- **Os projetos da mesma máquina reservam a memória antes do trabalho pesado** (melhoria, decisão do dono): duas entregas não se enxergavam, e o `capacity` lia a memória livre só no despacho; um app do autor teve a suíte inteira parada três vezes num dia enquanto outro projeto rodava a dele, com workers órfãos de até 8 GB e a entrega pausada. Agora o `capacity --rotulo` reserva o pico de cada cópia num arquivo da máquina (`~/.foreman/memoria.json`, regras na docstring de `memoria.py`), a conta de qualquer projeto desconta as reservas dos outros, e quem chega depois espera a vez com `--esperar`, na ordem da prioridade que o dono define no hub (`hub.py set --prioridade`). O `add` e o `release` liberam a reserva da tarefa, o `liberar` a da suíte do manager, e uma reserva sem renovação some em 2 h; o `hub.py status` mostra quem ocupa e quem espera, e o `hub.py liberar` solta a de uma sessão que caiu. O prompt do manager cresceu uma frase no passo 4.1: é o comportamento novo, e a regra antiga do `capacity` ficou dentro dela. Número: paradas por memória com outro projeto rodando, por entrega (meta 0).

**Ao atualizar:** nada quebra; os ledgers não mudam. A mediação vale entre os projetos já atualizados: um projeto numa versão anterior não reserva, e o `hub.py status` já avisa a versão diferente. Contornos que saem, se o projeto os tiver: a regra de não rodar a suíte inteira enquanto outro projeto roda a dele, ou de combinar a vez por mensagem entre as sessões.

## 1.15.0 — contorno do projeto removido na atualização

PR #22.

- **A atualização procura o contorno que o conserto tornou desnecessário** (melhoria, decisão do dono): um projeto resolve um atrito por conta própria antes de o plugin consertá-lo, com uma lição, uma linha no `CLAUDE.md` ou um passo que o manager repete, e depois do conserto esse contorno ficava como regra morta. O "Ao atualizar" de cada versão passa a nomear o contorno, e a skill `atualizar` o procura no projeto e propõe removê-lo na mesma lista das decisões; nada sai sem o sim do dono. O prompt da `atualizar` cresceu cerca de 40 palavras: é comportamento novo, e nenhuma frase dela ficou redundante. Número: contornos de versões já entregues ainda presentes nos projetos (meta 0).

**Ao atualizar:** nada muda.

## 1.14.3 — `claim` e `add` do `qa` sem atrito de formato

PR #21.

- **Uma nota entre parênteses no `Touches:` não é arquivo** (defeito): duas tarefas com "(novo)" ao lado de um arquivo novo colidiam no `claim` por "(novo)", e uma delas esperou a outra cerca de 17 min sem dividir arquivo nenhum num projeto do autor. Os parênteses depois de um espaço saem; os de dentro de um caminho (um grupo de rotas, `app/(tabs)/x.tsx`) ficam. Número: colisões falsas por entrega (meta 0).
- **O plano de uma preparação é lido na worktree dela** (defeito): com `plan --path` relativo numa entrega em preparação (`start --next --worktree`), o `claim` procurava o plano só na worktree principal e respondia que a tarefa não tinha linha `Touches:`, quando o arquivo é que não foi achado. Agora o caminho relativo é procurado também na worktree registrada, e, sem plano achado, o `claim` diz isso e pede o caminho absoluto.
- **`ports:` na linha logo abaixo de `Processes:`** (melhoria): o `add` do `qa` recusava o relatório que trazia as portas na linha seguinte, e o manager de um projeto do autor teve de editar uma cópia à mão. A informação está lá; o `add` passa a lê-la, e a porta que ainda aceita conexão continua barrando.

**Ao atualizar:** nada quebra. Contornos que saem, se o projeto os tiver: o caminho absoluto no `plan --path` de uma preparação; a regra de evitar nota entre parênteses no `Touches:`; a regra de escrever `ports:` na mesma linha de `Processes:`, ou de editar à mão a cópia do relatório do `qa` antes do `add`.

## 1.14.2 — dois-pontos no parêntese do rótulo

PR #20.

- **Os rótulos do `CLAUDE.md` aceitam dois-pontos dentro do parêntese** (`- Arquivos globais (o que toda tela herda: tema): ...`). Antes o `gate.py` e o `ledger.py` cortavam o rótulo no primeiro dois-pontos e ignoravam a linha em silêncio: "Arquivos globais" deixava de dispensar a suíte inteira, e o mesmo valia para os comandos, o "Tempo máximo", o "Ambiente dos comandos" e a "Verificação de interface". Um projeto do autor precisou de um commit só para tirar o dois-pontos.

**Ao atualizar:** nada muda. Uma linha com dois-pontos no parêntese passa a ser lida.

## 1.14.1 — critério em item de checklist

PR #19.

- **O `gate.py` reconhece o critério que abre um item de checklist** (`- [ ] **AC-T3-2**`, `- [x] AC-T3-2`). Antes ele virava "cited, never defined" e saía do rastreio dos critérios sem teste quando o plano misturava as duas formas, e um projeto do autor precisou de um commit só para tirar as caixas do plano.

**Ao atualizar:** nada muda. Um plano escrito como checklist passa a ter esses critérios rastreados; os que não tiverem teste aparecem no `Criteria`.

## 1.14.0 — texto publicado conferido, documentação conferida na atualização, ledger mais claro

PR #18.

- **Texto publicado pelo `gh` passa pela lista de termos** (melhoria, decisão do dono): um comentário de PR público trouxe nomes internos de um projeto e teve de ser apagado; o `pre-commit` só lê o que entra no git. O `bash-guard.py` nega um `gh pr`, `gh issue` ou `gh release` cujo título, corpo ou notas (ou o arquivo de `--body-file`), ou um `gh api` cujo campo de texto, tenha um termo do dono ou um caminho de home, pelas regras do scanner, sem imprimir o termo; um valor que o shell monta (`$( )`, heredoc, here-string, variável) é lido do comando inteiro, e um arquivo que ninguém consegue ler daqui é negado. Pela revisão do Fable. A skill `anonimizar` passa a ler também o texto do host (PRs, issues, releases e comentários) e a julgar além da lista o que um estranho aprende sobre o dono e os outros projetos dele; o que o dono confirmar vira termo. Número: comentários ou PRs apagados por vazamento (meta 0).
- **`gate.py --docs` na atualização** (melhoria): a checagem `Docs` do gate barrou só no fim de uma entrega 6 docs de módulo fora do lugar, que o kickoff comparou pelo sentido (custou um `fix`, uma revisão e um `qa --full`). O `gate.py --docs` roda só essa checagem contra a árvore, e a skill `atualizar` o roda e conserta o que ele mostra antes da próxima entrega. Número: reprovações do gate por estrutura anterior à entrega (meta 0).
- **`Isolates:` fora do `Touches:`** (melhoria; duas vezes num projeto): "Sem banco." ou "Pilha: cópia própria." no `Touches:` faziam tarefas independentes colidirem no `claim`. O plano põe o que a tarefa isola em `Isolates:`, que o `claim` não lê. Número: colisões falsas por entrega (meta 0).
- **"Verificação de interface" vale a partir do ciclo em que a linha entra** (melhoria): criada no meio da entrega, a linha reabria o ciclo 1 já fechado e abria um ciclo sem diff. O primeiro `add` que vê a linha grava a marca no ledger, e a cobrança vale só para o ciclo aberto nesse momento. Número: ciclos reabertos ou sem diff (meta 0).
- **`status` em texto abre com o próximo passo** (melhoria): numa entrega pausada, o `status` tinha 89 linhas. Agora a primeira linha é `next step:`, e as runs retidas e os deferidos sem decisão viram uma linha cada, com a contagem; o texto de cada deferido fica no `--json`, que não mudou. Número: linhas do `status` numa entrega pausada.

**Ao atualizar:** nada quebra; ledgers antigos seguem legíveis. Um ledger começado antes desta versão segue contando a linha "Verificação de interface" desde o início, como antes; só as entregas começadas nesta versão ganham a regra nova. No plano, o que a tarefa isola sai do `Touches:` e vai para `Isolates:`. Rode o `gate.py --docs` uma vez em cada projeto (a skill `atualizar` já o faz).

## 1.13.0 — suíte inteira do `qa` enxuta

PR #17.

- **A execução completa roda o comportamento só nos "Formatos do ciclo"** (melhoria, decisão do dono): num app, o `qa` da suíte inteira rodava 44 fluxos em 2 larguras e 3 modos, 6 passadas de 2 h 10 a 2 h 54 (~15 h), e um `qa` final de 23.757 s terminou em FAIL. Tema e largura mudam a aparência, não o comportamento. Agora a suíte de interface roda inteira nos "Formatos do ciclo" (o caso mais restritivo); os outros formatos, temas e ajustes entram só nas capturas e na gravação do fluxo principal. Pela revisão do Fable: uma entrega com tarefa `Global:` roda a suíte inteira em cada um, um teste cujo critério nomeia formato, tema ou ajuste roda nele, e uma suíte interrompida não entra com `--full`. Número: segundos do `qa --full` por entrega (meta no app: abaixo de 2 h).
- **Conserto depois do `qa` completo reverificado só no que ele toca** (melhoria, decisão do dono): o passo 6 repetia a execução completa depois de cada Critical ou Important, o que dobrava o custo. Com a linha opcional "Arquivos globais" no "Comandos", depois do PASS do `reviewer` sobre o conserto (que nomeia os fluxos tocados) o `qa` roda os fluxos que falharam e esses, nos formatos onde falharam, e entra com `add --after-full`, recusado sem um `--full` antes ou com `full_qa_blockers`. O `full_suite` do `gate.py` aceita o `--full` mais o último `--after-full` em PASS quando nada mudou depois dele, nenhum arquivo dos globs mudou desde o `--full` (rename conta pelos dois nomes, e mudar o "Comandos" conta como global, para a linha não se estreitar no meio), não entrou merge, e avisa o glob que não casa nenhum arquivo; sem a linha, como antes. O `status` mede o que mudou a partir da última reexecução em PASS. O intervalo é sempre o do `--full` até o head (cumulativo, revisão do Fable). Número: segundos de `qa` depois do primeiro `--full` por entrega.

**Ao atualizar:** nada quebra; ledgers antigos seguem legíveis. Para ganhar a reexecução parcial, acrescente ao "Comandos" do `CLAUDE.md` de cada projeto com tela a linha "Arquivos globais" com os globs do que toda tela herda (tema, navegação, configuração); sem ela, o gate segue pedindo a execução completa de novo. Confira que "Formatos do ciclo" nomeia o caso mais restritivo (a menor tela) e que "Formatos de tela" lista os temas e ajustes que as capturas cobrem.

## 1.12.0 — hub: uma sessão que delega a vários projetos

PR #16.

- **Foreman Hub** (melhoria, decisão do dono): com três projetos ativos, o dono mantinha uma aba por projeto e entrava em cada uma para pedir e aprovar. A skill `hub` e o `hub.py` (`init`, `status`, `add`, `set`, `remove`, `delegate`, `abrir`, `claim`) listam os projetos com o plugin sob uma pasta-raiz, repassam pedidos por `SendMessage`, abrem a sessão que falta (por padrão `wt.exe` no Windows e `Start-Process`, com `-n <nome>`; ou o comando `abrir` do registro) e mostram o que espera o dono lendo o `ledger.py status --json` de cada projeto. O `session-start.py` reconhece a pasta do hub e assume a posse da sessão; o `bash-guard.py` deixa a sessão de hub só com git de leitura, sem escrever no ledger, rodar o gate ou o kickoff nem fazer merge de PR, também de dentro de um projeto abaixo da raiz que traga um `hub.json` solto, e, depois de assumido, só o dono escreve no registro. Uma mensagem de hub é repasse, nunca o usuário: não traz aprovação e só liga o modo autônomo, nunca o desliga. O prompt do manager cresceu cerca de 37 palavras líquidas (a regra do repasse do hub, na regra do `PushNotification`), com uma oração retirada. Número: janelas de projeto que o dono visita por entrega delegada (meta 0 para começar e acompanhar; uma visita por aprovação) e a espera nas aprovações pelos horários do ledger, que não sobe; rodadas por ciclo não mudam. Spec em [`docs/specs/foreman-hub.md`](../../docs/specs/foreman-hub.md), plano em [`docs/plans/foreman-hub.md`](../../docs/plans/foreman-hub.md).
- **Merge na principal pergunta no modo supervisionado ou sem ledger** (melhoria, decisão do dono): as sessões abrem em `--permission-mode auto`, onde nada segurava o `git merge` na principal nem o merge de PR ou MR; o `bash-guard.py` passa a devolver `ask` para eles, como já fazia com o push. Número: merges na principal sem pergunta no modo supervisionado (meta 0).
- **`bash-guard` mais completo em toda sessão** (melhoria, decisão do dono, do VALIDAR da T8): `git -C <pasta>`, `--git-dir`, `GIT_DIR=` e `cd <abs> && git merge|push` são julgados no repositório daquela pasta (a pasta seguida por `cd` é julgada ali e na pasta da sessão, vale a resposta mais severa); o que vai dentro de outro shell é lido nas duas ferramentas (`cmd /c`, `powershell -Command` e `pwsh -c` pelo Bash; `bash -c`, `sh -c` e a forma posicional do `Start-Process` pelo PowerShell); `git -c alias.*` é negado, porque pode esconder o subcomando e pular o `pre-commit`; `git --attr-source <v>` é lido como opção com valor; um script só conta quando roda (`cat ledger.py start` deixa de perguntar), inclusive `python -m` e os lançadores `uv`, `poetry`, `pipenv`, `hatch` e `pdm run`. O que ainda falta está no [roadmap](../../docs/roadmap.md).
- **A suíte completa roda uma vez por entrega, só no passo 6, depois do PASS do `reviewer`** (melhoria, decisão do dono): qualquer commit depois do `qa` completo faz o gate pedi-lo de novo (`after_full_qa`), e numa entrega de vários ciclos a suíte rodava duas vezes por desenho: no `--full` do último ciclo e de novo no passo 6, porque o commit de versão, a `fix-N` de acabamento e o `cleanup` vêm depois dele (1h46 de `qa` num site, 2 × 53 min). O último ciclo passa a ter um `qa` comum de ciclo; o `qa` completo roda uma vez, no head final, depois do commit de versão, da `fix-N` de acabamento, do `cleanup` e do PASS do `reviewer` sobre o último commit, e captura cada tela nova ou alterada da entrega em todos os formatos, para a revisão visual do passo 7 e a revisão de design antes do `add`. Em toda entrega, não só na de um ciclo, o `ledger.py` recusa `add --full` enquanto faltar algo (o PASS do `reviewer` depois da última run do `dev` e sem commit depois dele fora do que a checagem Reviewed do gate isenta, a versão, o `cleanup` e os itens adiados sem decisão), e o `status` lista isso em `full_qa_blockers` quando o plano não tem mais tarefa (a linha impressa deixa de fora os itens adiados, que o `status` já lista). Risco aceito: um defeito visível só num formato fora dos formatos do ciclo pode aparecer só no fim. Número: suítes cheias por entrega (meta 1).
- **`qa` de captura no passo 6** (melhoria, decisão do dono): numa entrega com telas e sem `qa` completo (o gate roda a suíte de interface, ou não há linha "Verificação de interface"), a revisão visual do passo 7 não tinha de onde tirar as capturas em todos os formatos. O passo 6 despacha então um `qa` de captura no head final, depois do PASS do `reviewer`: só as telas novas ou alteradas da entrega, em todos os formatos e temas, e a gravação do fluxo principal, com a revisão de design antes do `add`, registrado sem `--full` e sem a suíte de interface inteira. Número: revisões visuais sem capturas em todos os formatos (meta 0).
- **O `dev` roda os fluxos de interface que escreveu** (melhoria, decisão do dono): num app, quatro falhas do `qa` de um ciclo (4,8 h, relatado pelo app) eram fluxos de interface nunca rodados. O relatório do `dev` ganha `Interface run:` com o resultado citado de cada teste ou fluxo de interface novo ou alterado, rodado nos caminhos que ele toca, ou `not run here: <motivo>` (DONE_WITH_CONCERNS, como numa máquina sem navegador); sem a linha o manager devolve a tarefa, como faz sem `Mutation evidence:`. Número: falhas do `qa` num fluxo que nunca rodou (meta 0).
- **Formatos do ciclo** (melhoria, decisão do dono): o `qa` de cada ciclo repetia todos os formatos de tela. A linha opcional "Formatos do ciclo" do `CLAUDE.md` do projeto lista os formatos (e ajustes, como uma fonte maior) que o `qa` do ciclo usa; sem ela, vale o primeiro de "Formatos de tela". A matriz completa, com todos os formatos e temas, roda só no `qa` completo do passo 6 (`--full`); a rodada de design e a revisão visual do passo 7 mantêm todos os formatos. Número: tempo do `qa` por ciclo em projetos com vários formatos. As mudanças de verificação desta versão crescem os prompts em palavras líquidas: manager +95, `dev` +29, `qa` +27, `references/screens.md` +17 e o molde do `CLAUDE.md` +59 (a linha opcional nova); cada uma é comportamento novo, e as orações que ficaram redundantes saíram, e o tempo de verificação é o que mais pesa no relógio da entrega.
- **Laço de testes** (decisão do dono): `plugins/foreman/skills/*/tests/test_*.py` no lugar da pasta do manager, em `CLAUDE.md`, `CONTRIBUTING.md` e na permissão de `.claude/settings.json`.

**Ao atualizar:** quem quer o hub instala o plugin na pasta-raiz dos projetos e chama `/foreman:hub`. No modo supervisionado ou sem ledger (inclusive o merge `--no-ff` de uma branch `docs/`), o merge na branch principal e o merge de PR passam a perguntar antes, como o push já perguntava. Em toda sessão, não só no hub: `git -C <pasta>`, `--git-dir`, `GIT_DIR=` e `cd <abs> && git merge|push` são julgados na pasta de destino; os comandos dentro de `cmd /c`, `powershell -Command`, `pwsh -c`, `bash -c`, `sh -c` e `Start-Process` são lidos; `git -c alias.*` é negado; e um script só é lido como comando quando roda. O último ciclo deixa de rodar `--full`: a suíte completa roda só no passo 6, e o ledger recusa `add --full`, em toda entrega, antes do PASS do `reviewer` sobre o último commit, da versão e do `cleanup`. Um `qa --full` de último ciclo da 1.11 que ainda roda na hora da atualização tem o `add --full` recusado: registre-o sem `--full`, como o `qa` do ciclo. Numa entrega em curso que já rodou o `--full` no último ciclo, o manager não o refaz por isso: o gate aceita esse `qa` enquanto nada fora de `docs/` mudar depois dele; quando mudou (o commit de versão, por exemplo), o manager despacha o `qa` completo de novo no passo 6, assim que o `status` não listar `full_qa_blockers`. O relatório do `dev` pede `Interface run:` (tarefas em curso sem a linha voltam ao `dev`). Projetos com vários formatos de tela podem preencher "Formatos do ciclo" no `CLAUDE.md`; sem a linha, o `qa` de cada ciclo usa só o primeiro formato. Uma entrega com telas cujo gate já roda a suíte de interface ganha uma rodada nova de `qa` no passo 6, a de captura, sem `--full`. O `status` lista `full_qa_blockers` só quando não resta ciclo no plano. Na pasta do hub, o hook do início da sessão não mostra mais o `hub.py status`: a skill `hub` o roda no primeiro passo.

## 1.11.0 — dependência declarada no lugar da família

Da lista de termos da 1.10.0 e da linha `familia` da 1.10.1.

- **Dependência declarada no repositório** (melhoria, decisão do dono): depender de outro projeto é legítimo e pode ser citado; citar o que não faz sentido para o projeto, não. A regra barrava pelo nome os projetos do dono, com a exceção `familia` morando no arquivo privado de termos, invisível para quem clona: o leitor não via de que o projeto dependia. Os defeitos reais eram um teste que lia `../<repositório vizinho>`, uma seção que só servia a outro projeto e caminhos para dentro de outro repositório; o nome era o sintoma, e foram duas exceções em duas versões (a ferramenta de desenvolvimento e a família). Agora o molde do `CLAUDE.md` ganha em "Comandos" a linha "Depende de" (cada sistema externo, o que se usa dele e a versão ou o contrato), que o kickoff preenche pelos arquivos do projeto; o scanner ignora, naquele repositório, o termo da lista que aparece nessa linha (a do `CLAUDE.md` da árvore no `--pre-commit` e a do HEAD no `--range`), e a linha `familia` deixa de liberar e vira um aviso; o gate avisa quando a linha muda contra a base, para declarar tudo não virar brecha silenciosa, e a nova checagem Standalone barra o `../` que sai do repositório nos arquivos de teste declarados e nos comandos de "Comandos" (`../_temp/`, a pasta das worktrees do plugin, continua de fora), que segue como aviso no resto; a `anonimizar` mantém a dependência declarada e tira a menção não declarada. Número: entradas de nomes de projeto no `.foreman-secrets-allow`; gates NOT READY por um termo de projeto; menções achadas pela `anonimizar` continuam 0 (se subirem em duas entregas, a regra do nome volta).

**Ao atualizar:** acrescente a linha "Depende de" ao `CLAUDE.md` de cada projeto (o kickoff a acrescenta como as outras linhas do molde) e passe cada linha `familia` do `~/.foreman-terms` para o "Depende de" dos projetos dela; nesta versão a linha `familia` ainda é reconhecida, sem efeito e com um aviso; na seguinte, o reconhecimento e o aviso saem. Um `../` que sai do repositório num arquivo de teste declarado ou num comando de "Comandos" passa a reprovar o gate.

## 1.10.1 — projetos do mesmo produto se citam

Da lista de termos da 1.10.0, montada para os projetos do autor.

- **Projetos do mesmo produto barrados um pelo outro** (defeito, pedido do dono): a lista `foreman.terms` só ignorava o termo igual ao nome da própria pasta, e o app de um produto cita o web dele dezenas de vezes (83 num projeto do autor), porque é a dependência e o nome do produto. Com o nome do web na lista, todo commit do app que o citasse seria barrado; sem ele, nenhum outro projeto era barrado ao citá-lo. A regra não tinha como ser seguida. Agora uma linha `familia <pasta> <pasta>...` junta as pastas de um produto: dentro de qualquer uma delas, os nomes da família são ignorados, e fora delas continuam barrados. Número: termos tirados da lista porque barravam um projeto do mesmo produto (meta 0).

**Ao atualizar:** nada muda; quem tem projetos do mesmo produto acrescenta a linha `familia` à lista.

## 1.10.0 — de projeto de casa a entrega para cliente

Os projetos começaram como projetos de casa; o foreman passa a trabalhar como numa entrega para cliente: cada entrega já sai anônima, limpa, com README e documentação no padrão e sem depender de outro repositório, em vez de uma limpeza no fim. Da auditoria de quatro projetos do autor, todos "razoáveis": a limpeza tardia custou reescrita de histórico, force push e várias rodadas de documentação.

- **Termos do dono e caminhos de home barrados a cada commit** (melhoria, pedido do dono): o nome do dono, e-mails e caminhos `C:\Users\<nome>\` só apareceram na `anonimizar`, depois do push. Agora os termos moram num arquivo fora de qualquer repositório, apontado por `git config --global foreman.terms` (o kickoff pergunta uma vez por máquina); o `pre-commit` barra a linha adicionada com um termo ou com um caminho absoluto de home, sem mostrar o termo, e libera pela mesma allowlist dos segredos; sem a lista, só o caminho de home vale. Número: termos do dono achados pela `anonimizar` num projeto criado com a lista (meta 0).
- **Autor e mensagem dos commits conferidos** (melhoria, pedido do dono): um e-mail de autor antigo exigiu `git filter-repo` e force push. Com linhas `autor <e-mail>` na lista, o `pre-commit` recusa outro autor e o gate (pelo `--range` do scanner) recusa autor, committer ou mensagem com termo na branch. Número: reescritas de histórico por autor ou mensagem (meta 0).
- **README no padrão** (melhoria, pedido do dono): os READMEs estavam fora do padrão. O molde ganha, nesta ordem, descrição, imagem (num produto com tela), Estado, Começo rápido, Como usar, Como funciona, Vocabulário (só os termos do README), O que sai da máquina, Documentação (com as novidades e o contato ou "sem suporte"), Para onde vai e Licença. O gate barra o README da raiz com marcador `_(...)_` quando já há módulo, sem uma seção do molde (lida do próprio molde), com a versão que a base tinha ou, num produto com tela, sem imagem de um arquivo versionado. Número: entregas NOT READY por README (meta 0 a partir da segunda entrega de cada projeto).
- **Status do módulo é o que existe hoje** (melhoria, pedido do dono): o **Status** virou log de tarefas. O molde diz uma frase do que existe hoje, e o gate barra id de tarefa, data ou mais de 200 caracteres; o doc do módulo deixa de pedir "classes e funções principais". Número: Status barrados pelo gate por entrega.
- **Uma fonte por assunto entre README, `CLAUDE.md` e operação** (melhoria, pedido do dono): o gate barra uma linha longa repetida entre eles. Número: linhas copiadas barradas por entrega.
- **Projeto que precisa de outro repositório** (melhoria, pedido do dono): uma suíte de testes dependia de um repositório privado vizinho. O gate avisa cada caminho relativo `../` que sai do repositório, e o `reviewer` cobra testes que não precisam de nada fora dele. Número: avisos de caminho para fora por entrega (meta 0).
- **Novidades para quem usa** (melhoria, pedido do dono): `docs/novidades.md`, uma linha por mudança visível, escrita pelo manager no commit da versão; o gate barra um minor ou major sem a entrada. Número: versões minor ou major sem nota para quem usa (meta 0).
- **`newcomer` no fechamento** (melhoria, pedido do dono): a leitura de quem nunca viu o repositório só vinha na `anonimizar`. Agora roda em paralelo com o `reviewer` final quando a versão sobe minor ou major ou a entrega muda o README ou "Preparar uma máquina"; o relatório dele traz `Verdict:`, o ledger o aceita e o gate cobra a leitura e, num FAIL, a correção depois dela. Número: achados `blocking` do `newcomer` por entrega.
- **A `anonimizar` fica para o legado** (melhoria, pedido do dono): com a lista de termos ela completa a lista em vez de perguntar do zero e cuida dos arquivos antigos e do histórico; o molde do `docs/operacao.md` só a pede antes do primeiro push numa máquina sem a lista ou num projeto anterior a ela.
- **Primeiro uso sem dados** (melhoria, pedido do dono): o spec checklist pergunta o que uma pessoa nova vê sem dados e onde aprende os termos do produto.
- **`qa` de ciclo intermediário sem a suíte de interface inteira** (melhoria, decisão do dono): num projeto do autor o `qa --full` somou 957 min contra 1051 min de `dev`, com mediana de 53 min por suíte inteira, e entregas pequenas pagaram duas suítes inteiras (troca-de-senha: 15 min de `dev` e 77 min de suíte inteira). Agora o `qa` de um ciclo roda a linha Testes inteira e a interface das telas que o ciclo tocou; o do último ciclo de várias e o do head final rodam a suíte inteira, e a checagem Full suite do gate não muda. Em troca, a tarefa que o plano marca `Global:` (escala, tema, token, componente compartilhado, helper de teste) roda a suíte de interface inteira na própria tarefa, e o `reviewer` confere a marca no plano; isso entrega o item "Mudança de escala global roda a suíte de interface inteira na própria tarefa" do backlog. Número: `qa --full` por entrega (meta 1, mais 1 por correção bloqueante) e minutos de `qa` sobre minutos de `dev`. Sai se as rodadas de correção no último ciclo subirem em duas entregas.
- **A suíte inteira roda uma vez numa entrega de um ciclo** (melhoria, decisão do dono): o `status` lista em `full_qa_blockers` o que falta antes dela (a versão como o gate a quer, a limpeza feita ou anotada como pulada, os itens adiados decididos) e o `add --full` é recusado enquanto falta algo. Número: suítes inteiras por entrega de um ciclo (meta 1).

**Ao atualizar:** os projetos existentes reprovam no gate, na próxima entrega, até o README e a documentação estarem no padrão: reordene o README, acrescente "Como usar" e, com tela, a imagem; tire tarefas e datas do **Status** dos módulos; e crie `docs/novidades.md` na próxima versão minor. Crie a lista de termos do dono (o kickoff pergunta) e rode o kickoff para acrescentar as linhas novas dos moldes.

## 1.9.0 — cada projeto se sustenta sozinho

Da rodada da `anonimizar` num projeto do autor.

- **A `anonimizar` tira as menções a outros projetos do dono** (melhoria, pedido do dono): o passo 3 trocava cada termo por um nome genérico, e um outro projeto do dono, citado 18 vezes, virou "o app de dados do carro", com uma seção inteira que só servia a ele e um caminho para dentro do repositório dele, que o leitor de fora não segue. Agora a menção sai e a frase é reescrita para se sustentar sozinha (o fato fica, a origem sai), o que só serve ao outro projeto sai com o sim do usuário, e o passo 5 enxuga tudo o que o projeto não precisa. O molde do `CLAUDE.md` ganha a regra em "Documentação": documento, plano e relatório não citam outros projetos do dono, e o que só serve a outro projeto mora lá. Número: menções a outros projetos do dono que sobram depois de uma rodada da `anonimizar` (meta 0).

**Ao atualizar:** nada muda; o kickoff traz a linha nova do molde.

## 1.8.0 — a correção espera o `qa` que roda na mesma árvore

Da noite autônoma da entrega obd-bluetooth de um projeto do autor.

- **Correção despachada com o `qa` ainda rodando** (defeito): o passo 4.3 mandava despachar o `fix-N` assim que o `reviewer` ou o `qa` desse FAIL, sem esperar o outro; num projeto sem worktree por cópia, o `dev` commitaria por baixo do build e do emulador do `qa`, contra a premissa "nenhum agente parado", que exclui o recurso que não se isola. Agora a correção espera o relatório do `qa` que verifica na árvore em que ela commitaria. Número: `fix-N` commitado com um `qa` em voo na mesma árvore (meta 0).
- **Revisão de design registrada sem reescrever o relatório do `qa`** (defeito): o `references/screens.md` mandava anexar os achados ao relatório do `qa` antes do `add`, mas o arquivo só nascia no `add --from-agent`, com o `Verdict:` do agente, e o `ledger.py` recusava `--report` junto de `--from-agent`; o manager transcreveu à mão o relatório com `Verdict: FAIL` e perdeu o texto original e a medição pelo transcript. Agora os dois vão juntos: a revisão de design fica num arquivo do manager ao lado do relatório do `qa`, que o run guarda, e o relatório do agente continua salvo e medido pelo transcript. Número: relatórios do `qa` reescritos à mão pela revisão de design (meta 0).
- **Rótulos literais no relatório do `qa`** (melhoria): o `add` recusou quatro relatórios em que o `qa` traduziu um rótulo ou escreveu uma frase depois de `ports:`. O `agents/qa.md` diz agora que os rótulos ficam literais e que `ports:` traz os números ou `none` antes de qualquer explicação. Número: relatórios do `qa` recusados pelo formato de um rótulo (meta 0).
- **Escrita reenviada no pré-mortem** (melhoria): uma fila de nova tentativa gravou em dobro e custou uma segunda rodada de correção. A pergunta "Each failure" do `templates/spec-checklist.md` pergunta agora se a operação, reenviada depois de uma falha ou de um reinício, grava uma vez só. Número: rodadas de correção por escrita duplicada em nova tentativa.
- **Verificação de interface por tela enquanto o `dev` ajusta** (melhoria, decisão do dono): um `fix-N` de revisão de design levou 107 min, contra 40 a 74 das tarefas, porque cada ajuste visual rodava a verificação de interface inteira (cerca de 13 min). O `agents/dev.md` diz agora que, ao ajustar, roda só as cenas das telas tocadas, e a verificação inteira uma vez antes do relatório. Os Minors continuam no mesmo `fix-N`. Número: minutos do `fix-N` de revisão de design acima da mediana das tarefas.
- **`anonimizar` antes do primeiro push para qualquer remoto** (melhoria, pedido do dono): o molde do `docs/operacao.md` lembrava a skill só antes de tornar o repositório público; um repositório criado privado ficava sem o lembrete, e um privado pode virar público com o histórico junto. Agora a linha vale para o primeiro push a qualquer remoto. Número: repositórios com remoto sem rodada da `anonimizar` antes do primeiro push.

**Ao atualizar:** nada muda.

## 1.7.0 — documentação depois do `qa` da suíte inteira não pede a suíte de novo

Das entregas barra-faixa-no-meio e cartao-segue-a-fonte de um projeto do autor.

- **Documentação depois do `qa --full`** (melhoria, decisão do dono): um commit só em `docs/` depois do último `qa --full` pedia a suíte inteira de novo na checagem Full suite do gate, e o `status` o apontava; foram três `qa --full` a mais em duas entregas, um deles com o emulador. Agora o que muda em `docs/` depois dele não conta. O gate continua rodando a linha Testes por conta própria. Número: `qa --full` repetidos só por documentação (meta 0).

- **Push barrado com a aprovação permanente** (defeito): em modo autônomo, com `approve --until 0.8.0` e o gate READY em v0.8.0, o `bash-guard.py` recusou o `git push origin main` porque a sessão estava numa subpasta do repositório: os caminhos de `docs/quality-reports/` eram lidos a partir dela, e o relatório não era achado. O merge local passa pela mesma conferência e caía no mesmo erro numa subpasta. Agora a conferência da aprovação roda a partir da raiz do repositório. Número: publicações cobertas pela aprovação permanente e barradas pelo hook (meta 0).
- **Tarefas que só dividem o doc de módulo** (defeito): o `references/parallel.md` despacha juntas as tarefas cujo `Touches:` só se cruza em docs de módulo, mas o `claim` as recusava; a T3 e a T4 esperaram a T2 por `docs/modulos/02-*.md`. Agora um doc de módulo (`docs/modulos/NN-*.md`) não cruza com nada no `claim`, na lista das tarefas que podem rodar juntas e na preparação da próxima entrega; o manager junta o doc na integração, como o `parallel.md` já diz. Número: tarefas serializadas só por um doc de módulo (meta 0).

**Ao atualizar:** nada muda.

## 1.6.2 — `Touches:` com a lista em sub-itens

Da entrega barra-faixa-no-meio de um projeto do autor.

- **`Touches:` em negrito com os caminhos em sub-itens** (defeito): `- **Touches:**` seguido de um sub-item por arquivo era lido como `*`, o asterisco que fecha o negrito, e o `claim` via colisão com tudo; duas tarefas independentes rodaram uma depois da outra. Agora um rótulo sem valor na própria linha (`Touches:`, `Depends on:`, `Goal:`) toma os sub-itens recuados logo abaixo dele: os caminhos entre crases de cada um, ou o sub-item inteiro quando ele não tem nenhum. Número: tarefas serializadas por um `Touches:` mal lido (meta 0).

**Ao atualizar:** nada muda.

## 1.6.1 — juntar ciclos do plano solta as execuções já retidas

Da entrega app-f1b de um projeto do autor.

- **Ciclos juntados no `scope`** (defeito): com o aval do dono para juntar os Ciclos 2 a 4 num QA só, o manager regravou o `scope` do Ciclo 2 com as tarefas dos três e removeu os outros dois, mas as execuções de `dev` já gravadas como retidas para os Ciclos 3 e 4 continuavam "held for plan cycle", porque o `ledger.py` lia o ciclo gravado em cada execução, não o `scope` atual. Agora o `scope` atual decide: uma execução retida cujo ciclo foi juntado ao aberto entra nele. Número: execuções retidas para um ciclo que não existe mais no `scope` (meta 0).

**Ao atualizar:** nada muda.

## 1.6.0 — a revisão de design confere primeiro as escalas globais

Da entrega app-f1b de um projeto do autor (PR #7).

- **Escalas globais antes das telas** (melhoria): a escala de texto do app ficou menor que a do mock (base 14 contra 16) desde a primeira entrega com tela, passou pela revisão de design do Ciclo 1 e só apareceu no Ciclo 2, quando todas as telas já entregues tinham de ser corrigidas e recapturadas. Agora cada revisão de design (`references/screens.md`) mede primeiro, numa captura, o tamanho do texto base, a unidade de espaçamento e a densidade contra o mock, e só então compara as telas. Número: achados de escala global depois do primeiro ciclo com tela, por projeto (meta 0).

**Ao atualizar:** nada muda.

## 1.5.0 — a conferência do relatório roda a suíte inteira, e o `claim` recusa o mesmo arquivo em paralelo

Da entrega app-f1b de um projeto do autor (PR #6).

- **A conferência do relatório roda a linha "Testes"** (melhoria): antes de integrar, o manager rodava os "Testes afetados", na prática os testes que o `dev` nomeou. Numa entrega, três tipos de teste quebraram sem ninguém ver (o de outra tela que a tarefa tocou, os que leem o repositório inteiro e os de telas que só a árvore de rotas carrega), e um deles custou a rodada de correção fix-2. O projeto empilhou três regras próprias para escolher os testes. Agora a conferência roda a suíte rápida inteira, a linha "Testes"; o `dev` continua com os "Testes afetados" enquanto trabalha. Número: testes quebrados que chegam ao `qa` por tarefa integrada (meta 0).
- **O `claim` recusa uma tarefa cujo `Touches:` cruza com o de uma tarefa em andamento** (melhoria; estava em espera, voltou na segunda ocorrência): o manager despachou duas vezes, de propósito, duas tarefas que mudam o mesmo arquivo, contra a regra de `references/parallel.md`. Agora o `claim` recusa e nomeia o cruzamento; sem plano ou sem `Touches:` de um dos lados (uma tarefa `fix-N`, ou um `Touches:` que só a Errata muda), passa como antes. Número: tarefas com arquivo em comum rodando juntas, por entrega (meta 0).

**Ao atualizar:** nada muda.

## 1.4.0 — itens adiados sem cópias, e a ação aprovada que o modo auto bloqueia espera o dono

Das entregas de um projeto do autor (PR #5).

- **Cópias de um item adiado entram uma vez** (melhoria): quatro itens chegavam em três cópias iguais a cada `start` (D1=D9=D15, D2=D10=D16, D3=D11=D20, D6=D13=D22), em cinco entregas seguidas, e cada cópia pedia uma decisão antes do gate. Agora o `start` junta os itens movidos com o mesmo texto, sem o "(moved here by ...)", e fica com o primeiro. Número: itens adiados repetidos por entrega (meta 0).
- **Ação aprovada que o modo de permissão recusa** (melhoria, decisão do dono): merge, push, deploy ou atualização do plugin aprovados e recusados pelo modo auto não são repetidos nem reformulados. O manager grava `note --text <para quê> --blocked <comando exato>`, um item VALIDAR com o comando e a recomendação "the user runs it", manda o aviso com o comando e segue no que não depende dele. O `ledger.py` recusa o mesmo comando de novo enquanto o item espera, e o relatório de qualidade mostra o comando junto do item. O heartbeat continua pedindo só o `status`, sem nomear a ação. Número: ações bloqueadas repetidas por entrega (meta 0).

**Ao atualizar:** nada muda.

## 1.3.1 — `--criteria` acha os critérios de uma tarefa com hífen no id

Da entrega app-f1b de um projeto do autor (PR #4).

- **`gate.py --criteria <tarefa>` com hífen no id da tarefa** (defeito): para uma tarefa `F1B-3`, o plano escreve `AC-F1B-3-1`, como o manager manda (`AC-<task>-<n>`), mas o `--criteria` só casava a forma junta (`AC-F1B3-1`) e respondia "no criterion of F1B-3" com saída 0: um PASS sem conferir nada, na entrega inteira anterior do mesmo projeto. Agora casa também os segmentos do id da tarefa em sequência, com mais um depois deles; `AC-F1B-31-1` continua fora. O gate completo já traçava todos os ids, então nada chegou ao merge sem teste. Número: tarefas do passo 4.1 conferidas à mão por falha do `--criteria`, por entrega.

**Ao atualizar:** nada muda.

## 1.3.0 — a preparação da próxima entrega não vira sobra, e nenhuma suíte morre por `timeout`

Do feedback da entrega app-f1a de um projeto do autor (PR #3).

- **A worktree da preparação `--next` não aparece como sobra** (defeito): uma worktree recém-criada para a spec e o plano da próxima entrega, ainda sem nada escrito, aparecia no `status` da entrega atual como sobra, com a ordem de removê-la e de apagar a branch. Agora `start --slug <próxima> --next --worktree <caminho>` registra a worktree, também numa preparação já aberta. Essa worktree, as das tarefas que a preparação reservou e as branches delas deixam de ser sobra. Número: pendências de sobra apontadas em trabalho vivo, por entrega.
- **O `bash-guard.py` nega um comando de "Comandos" dentro de `timeout`** (melhoria): um `qa` rodou a suíte de interface dentro de `timeout 590`, e a execução morreu depois do primeiro fluxo. A negação manda rodar em background, com log próprio. Número: execuções de `qa` perdidas por ambiente, por entrega.

**Ao atualizar:** nada muda nos ledgers. Numa preparação já aberta, dê `start --slug <próxima> --next --worktree <caminho>` uma vez para registrar a worktree dela.

## 1.2.0 — a noite autônoma não para por rodadas, e menos retrabalho no fim

Do feedback de uma entrega de um projeto do autor (PR #2).

- **No modo autônomo, as rodadas de correção não têm teto** (melhoria, decisão do dono): antes, três rodadas reprovadas paravam a entrega até a volta do usuário; uma noite parou três horas antes por três falhas de ambiente diferentes, cada uma já corrigida. Agora as rodadas seguem; o uso da conta e o fim da noite (`--until`) continuam pausando. O modo supervisionado não muda: uma rodada, depois a pergunta ao usuário, e o `extend`. As revisões de spec, plano e segurança mantêm o limite: um Critical aberto depois de três rodadas ainda para a entrega. Para que algo sempre limite a noite, o `mode autonomous` sem `--until` é recusado quando o mod não registra o uso da conta. Número: horas de noite perdidas por parada.
- **O `status` avisa quando há commit depois do `qa --full`** (melhoria): lista os arquivos que mudaram, antes de o gate pedir a suíte inteira de novo, e o passo 6 manda fazer `defer` dos Minors do `qa` final, nunca corrigi-los depois dele. Aconteceu duas vezes numa entrega, cerca de 45 min cada. Número: execuções de `qa --full` por entrega.
- **O `bash-guard.py` nega `git checkout` e `git restore` que sobrescrevem trabalho não commitado** (melhoria): numa entrega com ledger, quando o `git status` lista como alterado um arquivo que o comando restauraria. Um `dev` perdeu trabalho assim duas vezes numa entrega, contra uma lição que nenhum teste do projeto confere. Troca de branch, `restore --staged`, `--ours`, `--theirs` e `-p` passam.
- **O molde do `CLAUDE.md` pergunta se a pasta de saída da verificação e a `.superpowers/` ficam fora do watcher do servidor de dev e do linter** (melhoria): um watcher que varria 37 mil arquivos travou o app e custou uma rodada.
- **O `add` do `qa` aceita pontuação depois do veredicto** (defeito): "Verdict: FAIL." era recusado, e o manager editava o relatório à mão.
- **Sem aviso de heartbeat com a entrega pausada** (defeito): depois do fim da noite, que apaga o heartbeat, o `status` mandava criá-lo de novo.

**Ao atualizar:** nada muda nos ledgers. Uma entrega já em modo autônomo segue sem teto de rodadas; sem o uso da conta registrado, dê `mode autonomous --until <HH:MM>` na próxima vez que ligar o modo. O kickoff não mexe num `CLAUDE.md` que já existe: copie para a linha "O que a verificação grava…" de "Execução em paralelo" o trecho novo do molde e preencha como o servidor de dev e o linter deixam de varrer essas pastas.

## 1.1.0 — `anonimizar` lembrado antes de publicar

Pedido do dono: a limpeza antes da primeira publicação não pode depender de alguém lembrar de pedi-la.

- **O molde do `docs/operacao.md` lembra a skill `anonimizar`** (melhoria): a seção "Publicar" ganha uma linha para rodá-la antes de tornar o repositório público pela primeira vez, porque o dado pessoal costuma sobreviver só no histórico do git.

**Ao atualizar:** nada muda nos ledgers. O kickoff não mexe num `docs/operacao.md` que já existe: copie a linha nova do molde para a seção "Publicar" dele.

## 1.0.0 — primeira versão

Um time de desenvolvimento multiagente para o Claude Code, ligado por projeto:

- **`kickoff`** prepara um projeto novo ou existente: `CLAUDE.md`, `CLAUDE.local.md`, `docs/`, `.gitignore`, o hook de segredos e as permissões dos agentes.
- **`manager`** conduz a entrega do tamanho ao merge: spec nos pedidos grandes, plano revisado e aprovado pelo usuário, ciclos curtos com o `dev` por tarefa (as independentes em paralelo), o `reviewer` e o `qa` ao mesmo tempo e uma rodada de correção; modo autônomo, pausa pelo uso da conta, telas, várias sessões e varredura de segurança em `references/`.
- **Agentes** `discovery` (fatos das fontes brutas antes do design), `dev` (teste primeiro), `reviewer` (spec, plano e diff; só o que prova), `qa` (suíte e critérios de aceite, com a verificação de interface quando há tela) e `newcomer` (lê o repositório como quem nunca o viu).
- **`ledger.py`** registra cada execução de agente e diz o que falta; **`gate.py`** confere localmente ledger, critérios de aceite com teste, build, tipos, lint, suíte inteira, auditoria e segredos, e grava o relatório de qualidade.
- **`validar`** percorre as decisões tomadas em nome do usuário; **`atualizar`** leva o projeto a uma versão nova; **`feedback-plugin`** devolve as métricas e lições de cada entrega ao plugin; **`anonimizar`** tira dados pessoais dos arquivos e do histórico e revisa a documentação com o `newcomer` antes de publicar.
- **Hooks**: varredura de segredos, UTF-8 e caracteres invisíveis no `pre-commit`; retomada da entrega ao abrir a sessão; guarda dos comandos (pular o hook, a branch principal, `cd` relativo, servidor de dev solto, entrega fora do modo `auto`); e o mod de andamento, com a linha sob o prompt e o painel `/andamento`.
- **Checklists** de qualidade independentes de stack (`general.md` e as fatias de acesso e dados, autenticação e sessões, web e interface) e o que toda spec e todo plano respondem (`spec-checklist.md`).

**Ao atualizar:** nada muda.
