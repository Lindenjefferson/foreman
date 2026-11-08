# Histórico do plugin `foreman`

O que cada versão entregou e o que muda para quem atualiza. O arquivo vai junto com cada versão instalada: a skill `atualizar` lê o **Ao atualizar** de cada versão pulada, da mais antiga para a mais nova. Termine a entrega em andamento, ou pause-a, antes de atualizar o plugin (a skill `atualizar` confere). As ideias que ainda não viraram versão estão no [roadmap](../../docs/roadmap.md); o que é major, minor e patch, no [`CLAUDE.md`](../../CLAUDE.md#versão-e-release).

O fluxo nasceu inspirado no [ECC](https://github.com/affaan-m/ecc) (o pipeline `orch-*`, o `code-reviewer` e o `verification-loop`), em versão enxuta.

## 1.2.0 — a noite autônoma não para por rodadas, e menos retrabalho no fim

Do feedback de uma entrega de um projeto do autor.

- **No modo autônomo, as rodadas de correção não têm teto** (melhoria, decisão do dono): antes, três rodadas reprovadas paravam a entrega até a volta do usuário; uma noite parou três horas antes por três falhas de ambiente diferentes, cada uma já corrigida. Agora as rodadas seguem; o uso da conta e o fim da noite (`--until`) continuam pausando. O modo supervisionado não muda: uma rodada, depois a pergunta ao usuário, e o `extend`. As revisões de spec, plano e segurança mantêm o limite: um Critical aberto depois de três rodadas ainda para a entrega. Número: horas de noite perdidas por parada.
- **O `status` avisa quando há commit depois do `qa --full`** (melhoria): lista os arquivos que mudaram, antes de o gate pedir a suíte inteira de novo, e o passo 6 manda fazer `defer` dos Minors do `qa` final, nunca corrigi-los depois dele. Aconteceu duas vezes numa entrega, cerca de 45 min cada. Número: execuções de `qa --full` por entrega.
- **O `bash-guard.py` nega `git checkout` e `git restore` que sobrescrevem trabalho não commitado** (melhoria): numa entrega com ledger, quando o `git status` lista como alterado um arquivo que o comando restauraria. Um `dev` perdeu trabalho assim duas vezes numa entrega, contra uma lição que nenhum teste do projeto confere. Troca de branch, `restore --staged`, `--ours`, `--theirs` e `-p` passam.
- **O molde do `CLAUDE.md` pergunta se a pasta de saída da verificação e a `.superpowers/` ficam fora do watcher do servidor de dev e do linter** (melhoria): um watcher que varria 37 mil arquivos travou o app e custou uma rodada.
- **O `add` do `qa` aceita pontuação depois do veredicto** (defeito): "Verdict: FAIL." era recusado, e o manager editava o relatório à mão.
- **Sem aviso de heartbeat com a entrega pausada** (defeito): depois do fim da noite, que apaga o heartbeat, o `status` mandava criá-lo de novo.

**Ao atualizar:** nada muda nos ledgers. O kickoff não mexe num `CLAUDE.md` que já existe: copie para a linha "O que a verificação grava…" de "Execução em paralelo" o trecho novo do molde e preencha como o servidor de dev e o linter deixam de varrer essas pastas.

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
