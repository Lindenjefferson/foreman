# Histórico do plugin `foreman`

O que cada versão entregou e o que muda para quem atualiza. O arquivo vai junto com cada versão instalada: a skill `atualizar` lê o **Ao atualizar** de cada versão pulada, da mais antiga para a mais nova. Termine a entrega em andamento, ou pause-a, antes de atualizar o plugin (a skill `atualizar` confere). As ideias que ainda não viraram versão estão no [roadmap](../../docs/roadmap.md); o que é major, minor e patch, no [`CLAUDE.md`](../../CLAUDE.md#versão-e-release).

O fluxo nasceu inspirado no [ECC](https://github.com/affaan-m/ecc) (o pipeline `orch-*`, o `code-reviewer` e o `verification-loop`), em versão enxuta.

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
