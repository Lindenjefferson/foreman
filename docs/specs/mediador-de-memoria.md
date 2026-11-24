# Mediador de memória entre projetos

## Por quê

Duas entregas na mesma máquina não se enxergam. O `ledger.py capacity` lê a memória livre só no instante do despacho, e um projeto que passa na conta com 15,8 GB livres derruba a suíte do outro minutos depois, quando sobe três builds. No mesmo dia, um app do autor teve a suíte inteira parada duas vezes por falta de memória enquanto outro projeto rodava a dele, com workers órfãos de até 8 GB e a entrega pausada à espera do dono (roadmap, "Pico de memória de outro projeto na mesma máquina").

Meta (número do ledger): paradas por memória com outro projeto rodando, por entrega, vão a 0, contadas pelas `note` e pelos `pause` que citam memória; o `feedback-plugin` das duas entregas seguintes traz esse número.

## Objetivos

- Antes de um trabalho pesado (preparar ou verificar: instalar, build, suíte, emulador), o projeto reserva o pico dele num arquivo da máquina, e a conta de capacidade de qualquer projeto desconta as reservas dos outros.
- Quando não cabe, quem chegou depois espera a vez. Entre os que esperam, passa primeiro o de maior prioridade, que o dono define pelo hub; com prioridades iguais, a ordem de chegada.
- A reserva vale também para o comando pesado que o próprio manager roda (a suíte do passo 4.1), não só para o despacho de agente.
- O hub mostra as reservas e os pedidos em espera, define a prioridade de cada projeto e libera, a pedido do dono, uma reserva presa.

## Fora do escopo

- Interromper ou matar trabalho que já está rodando para dar lugar a um projeto de prioridade maior. A prioridade só ordena a fila.
- Medir a memória real de cada projeto por processo (seria regra de stack).
- Limpar processos órfãos de uma suíte parada.

## O que não pode acontecer

- Uma reserva de uma sessão que caiu travar a máquina para sempre.
- O manager encerrar a vez esperando um relógio enquanto aguarda memória.
- A mediação depender de uma sessão do hub aberta.

## Restrições

- Sem stack: a reserva é o pico declarado no `CLAUDE.local.md` do projeto (a linha que o `capacity` já lê), não uma contagem de processos.
- Sem sessão viva: tudo é arquivo e trava, como o `hub.lock`.
- Projetos de uma versão anterior do plugin não reservam; o `hub.py status` já avisa a versão diferente.
- Ledgers de versões anteriores continuam legíveis (nada muda no formato do ledger, só entradas novas).

## Abordagens

- **A. Arquivo da máquina, o hub mostra e decide a prioridade (escolhida pelo dono).** As reservas ficam num arquivo por máquina, na pasta do usuário; o `ledger.py` de cada projeto lê e grava com trava. Funciona com ou sem hub montado e com projetos fora da raiz do hub, porque a memória é da máquina.
- **B. Arquivo na pasta do hub.** O hub seria o dono literal das reservas, mas um projeto fora da raiz, ou uma máquina sem hub, fica sem mediação. Descartada.
- **C. Uma sessão do hub viva arbitrando.** Para tudo quando a sessão cai, como caiu a do app. Descartada.

## Desenho decidido

- **Arquivo.** `~/.foreman/memoria.json`, com `memoria.lock` ao lado (o mesmo esquema de token do `hub.lock`: travado por até 10 s, tomado quando tem mais de 30 s). `FOREMAN_MEMORIA` troca o caminho (testes). Guarda `reservas` (projeto: a raiz do repositório, rótulo, GB, desde, renovada), `pedidos` em espera (projeto, GB, desde, renovado) e `prioridades` (projeto: número).
- **Reservar.** `ledger.py capacity` desconta da memória livre as reservas dos outros projetos, por inteiro; as do próprio projeto não, porque a conta de hoje já mede o que as cópias dele ocupam. Contar por inteiro a reserva de outro projeto cuja suíte já está rodando conta essa memória duas vezes: o custo é esperar mais, nunca uma parada, e fica como `shortcut:` no código (decisão da sessão do foreman), a trocar por um desconto do que já está em uso se a espera pesar no relógio das entregas. `--reservar --rotulo <r> [--rotulo <r2> ...]` grava uma reserva do pico do projeto por rótulo, na ordem dada, enquanto couberem, e diz quais rótulos ganharam a reserva; o manager despacha só esses. O rótulo é o id da tarefa para um `dev` (o mesmo da claim), `qa` para o `qa` (um por vez por projeto), e `manager:<tarefa>` para a suíte que o manager roda ao conferir um relatório. Um pedido em espera de outro projeto com prioridade maior, ou igual e mais antigo, faz este esperar mesmo quando a memória cabe, para que a prioridade valha; a exceção é a `manager:<tarefa>` de uma tarefa que o projeto já segura (a suíte que confere o relatório dela), senão a tarefa nunca liberaria o que o outro espera. Um trabalho novo de quem segura memória espera a vez como qualquer outro. Um pedido que não caberia nem com todas as reservas liberadas (memória livre mais o reservado, abaixo do pico mais o piso) é recusado na hora, sem entrar na fila, para não travar os outros.
- **Esperar sem relógio.** Só `--esperar` grava um pedido na fila: sem ele, o `--reservar` que não cabe sai com 1 e não deixa pedido. Com ele, o comando fica no ar até conseguir a reserva de pelo menos um rótulo, renovando o próprio pedido a cada tentativa, e sai com 0 dizendo quais rótulos ganharam. O manager o roda em segundo plano e despacha quando a notificação chega; enquanto isso segue o que não é pesado.
- **Liberar.** O `add` de um `dev` libera a reserva com o id da tarefa, o `release` da claim também, o `add` de um `qa` libera a `qa`, e `ledger.py liberar --rotulo <r>` libera a do comando que o próprio manager rodou. Cada liberação tira só a reserva daquele rótulo.
- **Expirar.** Qualquer comando do `ledger.py` no projeto, menos o `status --json` (a leitura do mod e do hub), renova as reservas dele (o manager roda vários por tarefa; no modo autônomo, o heartbeat de 15 min também); o pedido em espera é renovado pelo próprio `--esperar`. Reserva sem renovação há 2 h, ou pedido há 5 min, deixa de contar e é removido na próxima escrita. Uma sessão que caiu prende a memória por até 2 h, e o hub a libera antes, a pedido do dono.
- **Projeto no arquivo.** Cada reserva, pedido e prioridade é guardado pela raiz do repositório (a do worktree principal, achada pelo git, para que as cópias e as frentes de um projeto, cada uma com o seu ledger, sejam um projeto só), com o nome da pasta para exibir. O hub acha a raiz de cada nome pelo registro e pela varredura; um projeto fora da raiz do hub precisa de `hub.py add` para ganhar prioridade, e sem ela vale 0.
- **Hub.** `hub.py status` lista as reservas e os pedidos (projeto, GB, desde quando, prioridade). `hub.py set --projeto <n> --prioridade <N>` grava a prioridade (maior passa antes; sem prioridade, 0). `hub.py liberar --projeto <n> [--rotulo <r>]` remove uma reserva presa, só a pedido do dono. A regra "o único arquivo que o hub escreve é o registro" passa a incluir o arquivo de memória.
- **Manager.** O passo 4.1 ("Size each dispatch...") troca `capacity` por `capacity --reservar`, também antes da suíte que o manager roda ao conferir um relatório. A `reason` do `capacity` já nomeia o projeto que ocupa a memória, então o `pause.md` não muda.
- **Testes primeiro** no `ledger.py` e no `hub.py`, com `FOREMAN_MEMORIA` e `FOREMAN_CAPACITY_MEMORY_GB`: dois projetos que não cabem juntos, prioridade passando à frente na fila, reserva expirada, `add` liberando, `--esperar` saindo quando o outro libera.
- **Versão.** Minor. O item do roadmap sai para a seção da versão no `UPGRADING.md`; o "Ao atualizar" diz que cada projeto ganha a mediação ao atualizar e que um projeto ainda não atualizado não reserva.

## Para quem constrói decidir

- O intervalo das tentativas do `--esperar` e o teto dele (sugestão: 30 s e 2 h, saindo com 1 no teto).
- Como o `capacity` sem `--reservar`, que segue existindo, mostra as reservas dos outros na `reason`.
- A forma exata do JSON e das mensagens, nos termos que o `ledger.py` e o `hub.py` já usam.
- Onde o `status` do projeto mostra a reserva própria e o pedido em espera.
