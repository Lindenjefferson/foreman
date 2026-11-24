# Mediador de memória — plano de implementação

> **Para quem executa:** use `superpowers:executing-plans`, tarefa por tarefa. Os passos usam caixas (`- [ ]`).

**Meta:** projetos na mesma máquina reservam o pico de memória antes do trabalho pesado, quem chega depois espera a vez pela prioridade que o hub define, e nenhuma suíte cai porque outro projeto subiu a dele.

**Arquitetura:** um módulo novo, `skills/manager/memoria.py`, é a fonte única do arquivo da máquina (caminho, trava, leitura com expiração, gravação atômica, reservar, liberar, renovar, prioridade). O `ledger.py` o usa no `capacity --reservar`, no `add`, no `release`, no `liberar` novo e na renovação de cada comando; o `hub.py` o usa no `status`, no `set --prioridade` e no `liberar` novo. A trava genérica sai do `hub.py` para o módulo, e o `hub.lock` passa a usá-la.

**Stack:** Python 3 da biblioteca padrão; testes no molde dos outros (`check(...)`, `ALL PASS`).

**Spec:** [`docs/specs/mediador-de-memoria.md`](../specs/mediador-de-memoria.md).

## Restrições globais

- Teste primeiro: cada teste novo falha antes da mudança.
- Arquivo: `~/.foreman/memoria.json` e `memoria.lock`; `FOREMAN_MEMORIA` troca o caminho do JSON (a trava fica ao lado). `FOREMAN_MEMORIA_AGORA` (ISO UTC) fixa o relógio nos testes.
- Expiração: reserva sem renovação há 2 h, pedido há 5 min.
- `--esperar`: tenta a cada `FOREMAN_MEMORIA_INTERVALO` s (padrão 30), desiste em `FOREMAN_MEMORIA_TETO` s (padrão 7200), saindo com 1 e tirando o pedido.
- Projeto = `os.path.normcase(os.path.realpath(<raiz do ledger>))`; nome = nome da pasta.
- Rótulos: id da tarefa (`dev`), `qa` (qualquer `qa`, um por vez por projeto), `manager:<tarefa>` (a suíte do manager).
- Mensagens dos scripts em inglês; documentos em português; prompts em inglês. Versão 1.16.0 (minor).
- Nenhum formato de ledger muda: ledgers antigos seguem legíveis.

## Foco de revisão

1. Arquivo de memória ausente, vazio ou corrompido: o `capacity` segue como hoje e o corrompido não é sobrescrito sem aviso (T1).
2. Trava presa por um processo que morreu: tomada depois de 30 s (T1, herdado do `hub.lock`).
3. Renovação a cada comando sem arquivo nenhum: não cria o arquivo nem a pasta (T1).
4. Projeto em preparação ou sem entrega: `capacity --reservar` funciona sem `start` (T2).
5. Hub com projeto fora da raiz: prioridade só por nome registrado (T3).

---

### T1: módulo `memoria.py`

**Arquivos:** criar `skills/manager/memoria.py`; criar `skills/manager/tests/test_memoria.py`; mudar `skills/hub/hub.py` (`locked` e `drop` passam a usar o módulo).

**Interfaces (produz):**
- `key(root) -> str`, `path() -> str`, `now() -> datetime`
- `lock(path, wait=10, stale=30)` (contextmanager; levanta `Busy`)
- `load() -> dict` com `reservas`, `pedidos`, `prioridades`, já sem os expirados; `save(data)`
- `others(data, projeto) -> float` (GB reservados pelos outros)
- `reserve(projeto, rotulos, gb, free, floor, peak_fit, esperando) -> (granted, reason)` sob a trava
- `release(projeto, rotulo=None) -> int`, `renew(projeto)` (sem arquivo, não faz nada), `set_priority(projeto, nome, n)`

- [ ] Testes: expiração de reserva (2 h) e pedido (5 min); `renew` sem arquivo não cria nada; `release` só do rótulo; JSON corrompido não é sobrescrito; trava velha tomada.
- [ ] Implementar e rodar `test_memoria.py` e `test_hub.py` até `ALL PASS`.

### T2: `ledger.py` reserva, libera e renova

**Arquivos:** `skills/manager/ledger.py` (docstring, `capacity`, `add`, `release`, `main`, comando `liberar`); `skills/manager/tests/test_ledger.py`.

- [ ] Testes (dois projetos num `FOREMAN_MEMORIA` temporário, memória fixa por `FOREMAN_CAPACITY_MEMORY_GB`): A reserva e B, sem caber, sai com 1 e nomeia A; reserva parcial de 2 de 3 rótulos; pedido de prioridade maior faz o outro esperar mesmo cabendo; pedido impossível recusado sem fila; `add --agent dev --task T` e `release --task T` liberam `T`; `add --agent qa` libera `qa`; `liberar --rotulo manager:T`; `--esperar` sai com 0 quando o outro libera; qualquer comando renova.
- [ ] Implementar e rodar `test_ledger.py` até `ALL PASS`.

### T3: `hub.py` mostra, prioriza e libera

**Arquivos:** `skills/hub/hub.py` (docstring, `status`, `set --prioridade`, `liberar`); `skills/hub/tests/test_hub.py`; `hooks/bash-guard.py` (`liberar` entre os comandos de escrita do hub) e o teste dele; `skills/hub/SKILL.md`.

- [ ] Testes: `status --json` traz `memoria` com reservas e pedidos; `set --projeto n --prioridade 2` grava pela raiz do projeto; `liberar --projeto n [--rotulo r]`; projeto desconhecido recusado; o guard nega `liberar` a uma sessão de hub que não é a dona.
- [ ] Implementar e rodar os testes do hub e dos hooks até `ALL PASS`.

### T4: documentos e versão

**Arquivos:** `skills/manager/SKILL.md` (4.1, a frase do `capacity`), `CLAUDE.md` (mapa), `UPGRADING.md` (1.16.0), `.claude-plugin/plugin.json`, `docs/roadmap.md` (item sai).

- [ ] Editar; rodar os cinco comandos de "Testar e validar" do `CLAUDE.md`.
