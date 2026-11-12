# Histórico do plugin `foreman`

O que cada versão entregou e o que muda para quem atualiza. O arquivo vai junto com cada versão instalada: a skill `atualizar` lê o **Ao atualizar** de cada versão pulada, da mais antiga para a mais nova. Termine a entrega em andamento, ou pause-a, antes de atualizar o plugin (a skill `atualizar` confere). As ideias que ainda não viraram versão estão no [roadmap](../../docs/roadmap.md); o que é major, minor e patch, no [`CLAUDE.md`](../../CLAUDE.md#versão-e-release).

O fluxo nasceu inspirado no [ECC](https://github.com/affaan-m/ecc) (o pipeline `orch-*`, o `code-reviewer` e o `verification-loop`), em versão enxuta.

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
