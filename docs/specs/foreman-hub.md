# Foreman Hub — spec

Uma sessão que não é projeto de ninguém, de onde o dono lista os projetos com o Foreman, delega um pedido a cada um e vê num lugar só o que espera por ele. Cada projeto segue com o Foreman inteiro, como hoje; o hub só delega e repassa. Origem: decisão do dono (design aprovado, abordagem B: relay com painel de status). Plano: [`docs/plans/foreman-hub.md`](../plans/foreman-hub.md).

## Meta de sucesso

Definida antes de construir, como pede a premissa "critério objetivo":

- **Número de uso:** janelas de projeto que o dono precisa visitar por entrega delegada. Meta: 0 para começar e acompanhar a entrega; uma visita por aprovação (✋ 1 e ✋ 2), que se dá na janela do projeto. O dono conta nas duas primeiras entregas delegadas; o `hub.py status` mostra ao vivo cada `sem resposta`, que é uma visita forçada.
- **Número do ledger:** a espera nas aprovações, pelos horários que o ledger já grava (da última revisão do plano em PASS até o `plan --path`), com dois ou mais projetos ativos. Meta: não subir em relação às entregas sem hub. Rodadas por ciclo e achados por origem não podem mudar, porque o hub não entra no ciclo.
- A regra do filtro vale: se nenhum dos dois números mexer em duas entregas, o hub sai.

Versão: **minor** (1.12.0). Há comportamento novo e nenhum ledger deixa de ser legível; o hub só lê ledgers.

## O que já está decidido (não reaberto aqui)

Objetivos, não objetivos, anti-objetivos, restrições e os sete pontos de "como" do design: descoberta por varredura mais registro opcional; sessão achada por `ListAgents` ou aberta; pedido repassado como foi dito; o pedido de aprovação sobe ao dono pelo hub (o "sim" se dá na janela do projeto, decisão posterior do dono, abaixo); status pelo registro; o hub nunca roda kickoff sobre si; o kickoff não dispara só por abrir uma pasta. Fora de escopo: dependência entre tarefas de projetos diferentes, mudar o fluxo de um projeto, substituir o Account Switcher.

Respostas do dono, também decididas: (1) com o hub aberto, ele é o canal de todo comando seguinte àquela sessão de projeto, não só do primeiro pedido; (2) não há espera à parte pelo kickoff: o hub espera só a sessão aparecer em `ListAgents` e manda o pedido original como primeira mensagem, e é essa mensagem que faz a sessão rodar o kickoff antes de atender, como se o dono a tivesse digitado lá; (3) o hub varre ao abrir e de novo quando o dono cita um projeto que ele não conhece, antes de dizer que não existe; (4) com várias sessões para o mesmo projeto, o hub pergunta qual usar; (5) o hub só anuncia que uma aprovação está pendente, e o "sim" de verdade se dá na janela do projeto, que é visível; (6) abrir uma sessão é abrir uma janela visível, e o `claude --bg` é opção de quem o liga.

## Decisões dos itens deixados para quem constrói

| Item | Decisão | Por quê |
|---|---|---|
| Marcador da varredura | Subpasta direta da raiz cujo `.claude/settings.local.json` ou `.claude/settings.json` tem em `enabledPlugins` uma chave `foreman@<marketplace>` com valor `true`. | É o que `claude plugin install ... --scope local` grava (conferido em dois projetos). Não depende do kickoff ter rodado nem de arquivo interno do Claude Code. A falta de `CLAUDE.md` na pasta só marca "sem kickoff". |
| Registro | Um arquivo, `<raiz>/.superpowers/hub.json`, escrito só pelo `hub.py`. Guarda o comando de abrir e, por projeto, pasta, conta, último pedido e estado. | `.superpowers/` já é a área de trabalho do plugin e fica fora do git; conta é dado da máquina, como o `CLAUDE.local.md`. Um arquivo só evita config e estado divergirem. |
| Entrar no modo hub | Skill `foreman:hub` (`/foreman:hub`), com o plugin instalado na pasta-raiz (`--scope local`). A primeira chamada roda `hub.py init`. | Skill é como o plugin já entrega um modo (`manager`, `kickoff`). O `hub.json` criado pelo `init` é o próprio marcador de "isto é um hub": nenhuma flag a mais. |
| Como o status se atualiza | Puxando do disco: `hub.py status` roda o `ledger.py status --json` em cada projeto. Mensagem de projeto só acorda o hub, que relê. Sem polling. | O ledger é a fonte única do que falta e do que espera o dono. Uma mensagem retida ou expirada não perde nada, e o hub não espera notificação nem relógio. |
| Código para "sou hub, não projeto" | Sim, pouco: `session-start.py` e `bash-guard.py` leem o `hub.json`. | O filtro pede checagem antes de texto. Sem ledger nem `CLAUDE.md` o hook já não faz nada, mas isso não impede o modelo de rodar o kickoff ou um `git merge`; o hook impede. |

## Componentes e o que cada um reaproveita

| Peça | O que faz | Mecanismo existente que usa |
|---|---|---|
| `skills/hub/SKILL.md` (novo, em inglês) | Resolve a sessão, repassa pedidos, anuncia aprovações pendentes, mostra o status. | `ListAgents` e `SendMessage`; o procedimento de abrir sessão de [`references/sessions.md`](../../plugins/foreman/skills/manager/references/sessions.md), que passa a ter uma linha apontando para o `hub.py abrir`. |
| `skills/hub/hub.py` (novo) | `init`, `status`, `add`, `set`, `remove`, `delegate`, `abrir`. Varre, lê o registro, lê os ledgers, grava o pedido. | `ledger.py status --json`; `.superpowers/atualizar.json`; `git config foreman.home`; `hooks/python.sh`. |
| `hooks/session-start.py` | Numa pasta com `hub.json`: grava a sessão como dona do hub e imprime o `hub.py status`. | O mesmo hook que devolve o ledger ao manager; o matcher `compact` já existe. |
| `hooks/bash-guard.py` | Numa sessão de hub: nega kickoff, escrita em ledger, commit, merge e push; nega escrita no registro por um hub que não é o dono. | O mesmo `PreToolUse`; nenhum hook novo no `hooks.json`. |
| `skills/manager/SKILL.md` | Uma frase na regra do `PushNotification`: avisar também o hub, e mensagem de hub é repasse, nunca o usuário, e não carrega aprovação. | A regra que já manda avisar o usuário ao parar. |

Nada entra no `kickoff`, no `ledger.py` nem no `gate.py`.

## Como funciona

### Registro (`hub.json`)

```json
{
  "abrir": null,
  "bg": false,
  "dono": "<session_id>",
  "sessoes": ["<session_id>", "..."],
  "projetos": {
    "<nome>": {"pasta": "<absoluta>", "conta": null, "abrir": null,
               "pedido": {"texto": "<até 200 caracteres>", "em": "<UTC ISO>"}, "estado": "enviado"}
  }
}
```

- `abrir` é um comando genérico e opcional, global ou por projeto, com `{pasta}`, `{nome}` e `{conta}`. O plugin não conhece nenhuma ferramenta de contas. O Account Switcher aparece só como exemplo de valor: `powershell -NoProfile -ExecutionPolicy Bypass -File ~/.claude-contas/abrir-conta.ps1 {conta} {pasta}`. Outro exemplo: `wt -d {pasta} claude --permission-mode auto`.
- `conta` é um rótulo livre que só serve para preencher `{conta}`. O hub nunca escolhe uma conta: usa a registrada ou nenhuma.
- Projetos vêm da varredura (nome = nome da pasta) e do `add` (pasta fora da raiz). Nome fora de `[A-Za-z0-9._-]` é ignorado com um aviso; o nome registrado vence a varredura.
- `sessoes` guarda as últimas 5 sessões de hub desta raiz; `dono` é a mais recente.

### Abrir uma sessão

1. `ListAgents` mostra uma sessão na pasta do projeto: usa essa. Mais de uma: o hub pergunta ao dono qual usar e fica com ela enquanto durar a conversa.
2. Senão, `hub.py abrir --projeto <nome>` roda o `abrir` do projeto, ou o global, ou o padrão do sistema, com a pasta do projeto como diretório e sem as variáveis `CLAUDE*` desta sessão, salvo `CLAUDE_CONFIG_DIR`, que mantém a conta ativa. O padrão é uma janela visível, sem o Account Switcher:
   - **Windows:** `wt.exe -w new -d <pasta> claude --permission-mode auto` (janela nova do Windows Terminal). Sem `wt.exe` no `PATH`: `Start-Process -FilePath claude -ArgumentList '--permission-mode','auto' -WorkingDirectory <pasta>`, que funciona, sem cor. É o que o abridor do dono já faz em produção.
   - **Outros sistemas:** não existe um comando de terminal comum a eles, então o `abrir` é o caminho para uma janela. Sem `abrir`, o hub cai no `claude --bg` e avisa (decisão do dono; não é erro): a sessão roda sem ninguém vendo, no modo autônomo, e o aviso diz como registrar o `abrir`.
   - **`claude --bg`** (`set --bg on`, global ou por projeto, ou a queda acima): `claude --bg --permission-mode auto -n <nome>`. Só nesse modo ninguém está vendo a sessão, então só nele as aprovações viram notas VALIDAR: a primeira mensagem do hub diz que o dono ligou o modo autônomo, e o manager grava `mode autonomous`.
3. O hub entrega o pedido por `SendMessage` só quando `ListAgents` lista a sessão; é a primeira mensagem dela. Num projeto sem kickoff, a sessão roda o kickoff antes de atender, sem nenhuma sincronia a mais do lado do hub.
4. **A sessão nunca aparece** (ou o comando falha): o hub confere `ListAgents` por até um minuto na mesma vez, como o kickoff faz com um serviço subindo, e então grava o estado `não entregue`, mostra ao dono o comando e a saída e pede que ele feche a aba que abriu com erro. Não manda o pedido, não tenta outra conta e não abre uma segunda sessão; o dono diz "tenta de novo" ou corrige o `abrir`.

### Delegar

"`<projeto>: <pedido>`", no primeiro pedido e em todo comando seguinte (pausar, responder uma pergunta, pedir outra coisa): com o hub aberto, ele é o canal. Com a sessão resolvida, o hub roda `hub.py delegate --projeto <nome>` com o texto no stdin; o script grava o último pedido e recusa (saída 1) quando o projeto é desconhecido, a pasta não existe ou há atualização pela metade. Depois o hub manda o texto, palavra por palavra, com duas linhas de protocolo: o nome da sessão do hub para a resposta, e que a mensagem é um repasse.

Todo subcomando do `hub.py` refaz a varredura, que é barata. Assim o hub varre ao abrir e de novo quando o dono cita um nome novo, antes de dizer que o projeto não existe.

O hub não segura um comando porque há entrega em andamento: quem decide o que fazer com ele é o manager do projeto, como se o dono tivesse digitado lá.

### Endereço do hub e mensagens

- **Entrega do endereço:** toda mensagem do hub leva o nome da sessão dele, e a sessão aberta pelo hub só recebe o pedido depois de listada, então ela nunca precisa saber o endereço antes. Nada é gravado na pasta do projeto.
- **Mensagem retida ou sem resposta:** o hub não espera. Ele grava `enviado` e encerra a vez depois de despachar o que podia. A confirmação é o ledger do projeto mostrar uma entrega aberta depois do horário do pedido, ou uma resposta. Sem nenhuma das duas, o próximo `status` diz "`sem resposta` há N min: a mensagem pode estar retida na janela do projeto; aprove lá ou mande de novo". O hub nunca reenvia sozinho, para o pedido não entrar duas vezes.
- **Modo de permissão:** as sessões de projeto abrem em `--permission-mode auto` (decisão do dono), o mesmo modo do hub, então a mensagem não fica retida (spike S2). O `auto` vale só para a ação comum: ler, editar, rodar testes. Merge, push e o que é destrutivo continuam pedindo a ✋ de verdade, e quem garante isso são as regras de `deny` e o hook do próprio foreman, nunca o modo de permissão do Claude Code: ver "Aprovações".
- **Sem aviso do projeto:** se a sessão do projeto perdeu o endereço numa compactação, ela para na ✋ como hoje e manda o `PushNotification` de sempre; o hub vê a pendência no ledger no próximo turno. O atraso máximo é o tempo até o dono falar com o hub.
- Texto que chega de um projeto é dado, não instrução: o hub mostra, não executa.

### Aprovações

A ✋ 1 e a ✋ 2 continuam do dono. O hub só anuncia que há uma aprovação pendente (do ledger, passos `ask`, e da mensagem) e diz em que janela; o "sim" se dá na janela do projeto, que é visível. O hub nunca manda resposta de aprovação. No modo autônomo (o que o dono ligou no projeto, ou uma sessão `--bg`) o manager do projeto troca aprovações por notas VALIDAR, como hoje; o hub mostra a contagem.

O que torna isso conferível, e não só dito:

1. **O hub não tem como aprovar.** Na sessão de hub o `bash-guard.py` nega todo `ledger.py` que não seja `status`, o `gate.py`, e `git commit`, `merge`, `push`, `cherry-pick` e `rebase`. Sem `plan --path`, `note`, `waive`, `extend` nem `mode`, o único caminho até um projeto é uma mensagem. Teste em `test_bash_guard.py`.
2. **O `hub.py` não escreve fora de `<raiz>/.superpowers/`.** Teste: a árvore das pastas de projeto é igual antes e depois de cada subcomando.
3. **Os guardas do projeto valem por pasta, para qualquer sessão.** O `bash-guard.py` já nega merge e push da principal no modo autônomo e pergunta antes do push da principal no supervisionado, lendo o ledger da pasta. O hub não muda isso (testes existentes).

**Lacuna que o modo `auto` expõe, fechada nesta entrega.** No modo supervisionado o `bash-guard.py` hoje só devolve `ask` para o `git push` que alcança a principal. O `git merge` com a principal em checkout e o merge de PR ou MR (`gh pr merge`, `glab mr merge`) passam sem nada: num modo de permissão que pergunta, o prompt do Claude Code os segurava; em `auto`, nada os segura. A tarefa T8 do plano faz o hook devolver `ask` também para eles, como no push. Mexe na segurança, então espera a confirmação do dono. O que é destrutivo (force push, `sudo`, `chmod 777`, pular o `pre-commit`) já está no `deny` que o kickoff escreve, e `deny` vale em qualquer modo. Depende do spike S6: se um `ask` de hook não perguntar em `auto`, a T8 e o `ask` do push que já existe voltam ao dono com a alternativa de negar e liberar só pela aprovação registrada (`ledger.py approve`).
4. **O lado que recebe:** uma frase no manager diz que mensagem de hub é repasse, não carrega aprovação e pode ligar o modo autônomo, nunca desligar. Coincide com o que o Claude Code já diz a cada sessão: mensagem de agente não é consentimento do usuário.

### O hub nunca roda kickoff sobre si

Checagem, não texto: na sessão de hub o `bash-guard.py` nega `git init` e o `pre-commit-secret-scan.py --install-pre-commit`, os dois primeiros passos de escrita do kickoff. O `hub.py init` recusa uma pasta com `.superpowers/ledger.jsonl` (é um projeto). O `session-start.py` diz, na pasta do hub, que ela é um hub. Sem `CLAUDE.md` de projeto nada dispara sozinho, mas só a checagem impede.

## Casos de canto

| Caso | Comportamento decidido | Onde se confere |
|---|---|---|
| Dois pedidos ao mesmo projeto ao mesmo tempo (hub e janela do projeto, ou dois hubs) | As mensagens chegam à sessão do projeto uma depois da outra, e o manager as trata como digitadas. O árbitro de "duas entregas" é o `ledger.py start`, que já recusa a segunda sem `--archive` ou `--next`. O hub não duplica essa regra; só há um hub que escreve (linha "Dois hubs"). | testes existentes do `ledger.py`; `test_bash_guard.py` |
| Várias sessões abertas para o mesmo projeto | O hub pergunta qual usar. Não grava a escolha: depois de uma compactação pergunta de novo, e o caso é raro. | skill |
| Projeto criado depois de o hub abrir | Achado na próxima chamada, porque todo subcomando varre. | `test_hub.py` |
| Comando seguinte com o anterior ainda `sem resposta` | Manda, e avisa que o anterior não teve resposta há N min. | `test_hub.py` (estado); skill |
| Sessão do projeto morre ou é fechada | O `status` vem do ledger, então nada se perde. Pedido aberto ou entrega em andamento sem sessão em `ListAgents`: o hub mostra "sem sessão" e reabre uma vez; o pedido de retomada manda rodar o `ledger.py status`. | skill; spike S1 |
| Projeto achado com Foreman desatualizado ou quebrado | `.superpowers/atualizar.json` na pasta: "atualização pela metade", e o `delegate` recusa. Versão em `foreman.home` diferente da do hub: aviso, sem bloquear. `ledger.py status` falha ou devolve JSON inválido: "ledger ilegível", sem derrubar o `status` dos outros. Settings que não é JSON: projeto ignorado, com aviso. | `test_hub.py` |
| Registro aponta para pasta que sumiu | `status` mostra "pasta ausente"; `delegate` e `abrir` recusam; a entrada só sai com `remove`, a pedido do dono. | `test_hub.py` |
| Conta registrada foi removida do abridor | O comando falha ou a sessão não aparece: é o passo 4 de "Abrir uma sessão". O hub não troca de conta sozinho e oferece corrigir o registro. | `test_hub.py` (comando que falha) |
| Aprovação pendente quando o hub fecha e reabre | A pendência mora no ledger do projeto. O `session-start.py` imprime o `hub.py status` na abertura. | `test_session_start.py` |
| Dois hubs na mesma raiz | O mais novo vira `dono`. O antigo tem toda escrita no registro negada pelo `bash-guard.py` com "outro hub assumiu"; ler continua livre. Escrita do `hub.json` é atômica (arquivo temporário e troca). | `test_bash_guard.py` |
| Hub aberto dentro de um projeto | `init` recusa. | `test_hub.py` |
| `hub.json` corrompido | Todo subcomando sai com 2 e não sobrescreve o arquivo. | `test_hub.py` |
| Projeto desconhecido, ou nome que difere só na caixa | Saída 1 listando os nomes; a comparação ignora a caixa. | `test_hub.py` |
| Pedido com aspas, quebras de linha ou `$` | Vai pelo stdin ao script e por `SendMessage` ao projeto; nunca passa por uma linha de shell. `{pasta}` entra no comando com aspas. | `test_hub.py` |
| Sessão `--bg` com o dono de volta | `status` mostra "autônomo" e os VALIDAR abertos; o dono abre a sessão com `claude attach`, diz "voltei" e percorre os VALIDAR lá. | skill |
| Projeto em modo autônomo | `status` mostra "autônomo" e os VALIDAR abertos; o hub não manda resposta de aprovação. | `test_hub.py` (leitura); skill |
| Raiz sem nenhum projeto | `status` diz como instalar o plugin num projeto e sai com 0. | `test_hub.py` |
| Raiz é um repositório git e `.superpowers/` não está ignorada | `init` avisa: o registro tem rótulos de conta. | `test_hub.py` |

## Respostas à spec-checklist

**1. Pré-mortem por escrita.** As escritas são: o registro (`init`, `add`, `set`, `remove`, `delegate`), a posse do hub (`session-start.py`) e a abertura de uma sessão.
- Quem pode: só a sessão dona escreve o registro (guard). Não há contas nem papéis: n/a.
- Em que linhas: uma entrada de projeto por comando; `delegate` confere que a entrada existe.
- O que referencia: pasta e conta, tratadas em "Casos de canto".
- Dois ao mesmo tempo: troca atômica e um dono só.
- Valores derivados: `texto` do pedido cortado em 200 caracteres; `sessoes` em 5.
- Cada falha: tabela de erros abaixo. `delegate` repetido regrava o mesmo último pedido; o hub nunca reenvia a mensagem sozinho, então ela entra uma vez.
- Validar antes de escrever: o `delegate` valida tudo antes de gravar; o hub só manda a mensagem depois de o `delegate` sair com 0.
- O passado: nada; o registro guarda só o último pedido.

**2. Suposições técnicas**, cada uma provada num spike de minutos antes do código (tarefa S do plano); a que cair muda o desenho antes de seguir:
- S1: `ListAgents` lista sessões de outras pastas com o diretório; uma sessão aberta pelo padrão do Windows (`wt.exe -w new -d`, e o `Start-Process` sem `wt.exe`), sem as variáveis `CLAUDE*` salvo `CLAUDE_CONFIG_DIR`, aparece nele com a mesma conta, carrega o plugin de escopo local e recebe `SendMessage`. O mesmo para o `--bg`, só se alguém for ligá-lo.
- S2: a mensagem do hub (modo `auto`) a uma sessão aberta em `auto` chega direto, sem retenção.
- S6: o `permissionDecision` `ask` de um hook `PreToolUse` ainda pergunta ao usuário quando a sessão está em `--permission-mode auto`.
- S3: o payload de `SessionStart` e de `PreToolUse` traz `session_id`, o mesmo nos dois, e o `cwd` do `PreToolUse` depois de um `cd`.
- S5: instalar o plugin com `--scope local` numa pasta que não é repositório git funciona.

**3. Escritas sensíveis e trilha.** n/a: o hub não escreve papéis, credenciais nem dinheiro. As decisões seguem na trilha do ledger de cada projeto.

**4. Regras de domínio.** Tempo: horários em UTC ISO; "agora" entra no `hub.py` por `--agora` nos testes. Identidade: nome de projeto comparado sem diferença de caixa. Dinheiro: n/a.

**5. Invariantes.** Um dono por raiz; o hub escreve só em `<raiz>/.superpowers/`. Os dois têm teste. Não há trava entre processos além da troca atômica, porque só o dono escreve.

**6. Estados de tela.** Não há tela; a saída é texto. Estados do `status`: nenhum projeto, sem kickoff, sem entrega, em andamento (ciclo e tarefas que faltam), espera o dono (com a pergunta), autônomo, pausado, sem resposta, não entregue, sem sessão, pasta ausente, atualização pela metade, ledger ilegível. O que espera o dono vem primeiro.

**7. Auth.** n/a: sem contas nem sessões de usuário.

**8. Privilégios e padrões.** Tudo fechado por padrão: `bg` desligado, salvo a queda avisada fora do Windows; o hub não tem comando que aprove. Nenhuma regra nova em `permissions.allow` dos projetos.

**9. Erros** (o `hub.py` escreve em inglês, como os outros scripts; o hub fala com o dono na língua dele):

| Código | Quando | Saída | Mensagem |
|---|---|---|---|
| unknown-project | nome fora do registro e da varredura | 1 | lista os nomes |
| missing-folder | pasta registrada não existe | 1 | a pasta e `remove` |
| half-update | `atualizar.json` no projeto | 1 | terminar a atualização na sessão do projeto |
| is-project | comando que escreve o registro numa pasta com ledger | 1 | abrir o hub na pasta-raiz |
| exists | `add` de nome ou pasta que o hub já conhece | 1 | o nome que já usa a pasta |
| bad-name | nome fora de `[A-Za-z0-9][A-Za-z0-9._-]*` | 1 | o formato aceito |
| usage | argumento ausente, inválido ou `--raiz` que não existe | 1 | a linha de uso |
| busy | outro comando do hub segura o registro há mais de 10 s | 1 | tentar de novo |
| open-failed | o comando de abrir saiu com erro | 1 | o comando e a saída |
| bad-registry | `hub.json` não é JSON ou não tem a forma do registro | 2 | o caminho; nada foi sobrescrito |

Negações do guard: "hub session: <comando> belongs to the project's session" e "another hub session took over this root".

**10. Plano de testes.** Critérios em Given/When/Then com id no plano. Alvos de mutação: a recusa do não dono, cada negação do guard, a escrita atômica, a varredura (aceitar `false` ou outra chave). Vazio e nulo em cada argumento. O que não se automatiza e se confere à mão: os spikes e uma entrega delegada de ponta a ponta em dois projetos, com uma aprovação anunciada pelo hub e dada na janela do projeto.

**11. Stack.** n/a: Python 3 da biblioteca padrão, como os outros scripts.

**12. Dados pessoais.** O rótulo de conta pode ser um e-mail do dono. Fica em `<raiz>/.superpowers/hub.json`, fora do git, nesta máquina; o hub não o põe em mensagem, relatório nem arquivo de projeto; apagar é o `remove` ou apagar o arquivo. O `status` mostra o rótulo só ao dono.

## Conflitos com o design e com as premissas

Registrados, não resolvidos em silêncio:

1. **Resposta de aprovação.** O design dizia que a resposta volta pelo hub; o dono decidiu depois que o hub só anuncia e o "sim" se dá na janela do projeto. Deixou de ser conflito.
2. **Um ramo por sistema.** O padrão de abrir tem um ramo só para o Windows (`wt.exe`, com `Start-Process` de reserva), o mesmo que o abridor do dono já usa em produção; os outros sistemas usam o `abrir` ou caem no `--bg`. É a única parte do plugin que nomeia uma ferramenta de um sistema; fica num ponto só do `hub.py`, com teste.
3. **"Sem persistir nada mais que isso".** O registro ganha `dono` e `sessoes`, que o design não lista; são o que torna "um hub só" e "o hub não aprova" conferíveis por hook.
4. **O plugin é "habilitado por repositório".** A pasta-raiz do hub recebe o plugin sem ser projeto. O kickoff e o README dizem "por projeto"; o README ganha uma linha.
5. **Sessão `--bg` sem ninguém para aprovar.** Só para quem liga. O roadmap ("Sessão caída de madrugada") lembra que uma sessão que ninguém vê não tem quem aprove permissão; por isso ela roda no modo autônomo, e um prompt de permissão que apareça espera o `claude attach`, sem o hub enxergar. Limite conhecido.

## Contexto que o hub acrescenta a cada sessão

Conferido contra as práticas do dono (arquivo de contexto só com necessidade; regra que não pode falhar vai para hook):

- Em toda sessão com o plugin, projeto ou hub: a descrição de uma frase da skill `hub` na lista de skills. Nada mais.
- Só quando o manager é carregado: uma frase a mais na regra do `PushNotification`.
- Só na pasta do hub: a saída do `session-start.py` (uma linha e o status), também depois de uma compactação.
- Nenhum `CLAUDE.md`, arquivo de regras ou de memória novo; o molde do `CLAUDE.md` dos projetos não muda; o `CLAUDE.md` deste repositório ganha uma linha no mapa e segue abaixo de 200 linhas. As três regras que não podem falhar (não aprovar, não rodar kickoff, um hub só) estão no `PreToolUse`, não no texto da skill, que fica em até 40 linhas.

## Limites aceitos

- O guard reconhece a sessão de hub pelo `session_id` e acha o `hub.json` subindo a partir do `cwd`. Num projeto registrado fora da raiz, depois de um `cd` para lá, ele não acha o arquivo; valem então só os guardas do próprio projeto. Limite aceito pelo dono.
- Os arquivos seguem a convenção do foreman, `docs/specs/<slug>.md` e `docs/plans/<slug>.md` (aceito pelo dono).
- O `hub.py status` roda o `ledger.py status` de cada projeto marcado, e ele roda `git` na pasta do projeto, que respeita a configuração local dela (`core.fsmonitor`, por exemplo). É a mesma exposição que o `session-start.py` já tem em cada projeto; o hub só a repete em cada pasta marcada da raiz. Um clone não traz `.git/config`, então o risco é de uma pasta já adulterada na máquina.
- O `hub.json` é confiável como um script do dono: guarda o comando de abrir e o texto dos pedidos, que o hub lê na abertura. Uma pasta copiada de outra pessoa com `.superpowers/hub.json` dentro faria o mesmo; o hub só nasce de um `hub.py init` na pasta-raiz do próprio dono.
- O `bash-guard.py` vê só os comandos do Bash e do PowerShell, e nem todas as formas deles: uma sessão de hub que escrevesse direto no `hub.json`, num `ledger.jsonl` ou num `approval.json` com as ferramentas de edição ou com `touch`, `rm` e redirecionamento, ou que escondesse o comando em crases, `"$(...)"`, `nice`, `sudo`, `timeout`, `winpty`, `stdbuf` ou `find -exec`, passaria; o guard é uma rede contra o descuido, não uma barreira contra quem quer contornar (decisão a validar pelo dono; a alternativa é estender o hook às ferramentas de edição desses três arquivos).
- As ✋ 1 e ✋ 2 não aparecem no ledger como passo `ask`; o hub as conhece pela mensagem do manager. Sem a mensagem (sessão que perdeu o endereço), o dono as vê na janela do projeto.
- Sem polling: uma pendência aparece no hub quando o dono fala com ele ou quando chega uma mensagem.
- Só sessões da mesma máquina.

## Fora desta entrega

Fila de pedidos por projeto no hub, polling, dependência entre projetos, linha do hub no mod `andamento.js`, janela por padrão fora do Windows.
