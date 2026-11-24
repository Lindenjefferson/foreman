#!/usr/bin/env python3
"""Foreman hub: lists the projects that have the plugin, keeps the account and the open command of each.

Commands
--------

  init                                                        creates <root>/.superpowers/hub.json
  status  [--json]                                            the projects, from the scan and the registry
  add     --nome <n> --pasta <p> [--conta <c>] [--abrir <cmd>]   registers a project outside the root
  set     [--projeto <n>] [--conta <c>] [--abrir <cmd>] [--bg on|off]
                                                              without --projeto: the global abrir and bg
  remove  --projeto <n>                                       drops a registry entry
  set     --projeto <n> --prioridade <N>                      the project's memory priority (higher goes first)
  liberar --projeto <n> [--rotulo <r>]                        frees a memory reservation that a dead session left
  set     --projeto <n> --estado respondido                   the owner saw the project answer
  delegate --projeto <n> [--nao-entregue]                     stores the request (text on stdin, first 200 chars)
  abrir   --projeto <n> [--mostrar]                           opens the project's session; --mostrar only prints
  claim   --sessao <id> [--espera <s>]                        makes the session the owner (dono) of the hub; only
                                                              session-start.py calls it. sessoes keeps the last five;
                                                              the id matches [A-Za-z0-9._-]{1,100}, --espera is the lock wait
                                                              in seconds, clamped to 0..10

Every command takes --raiz <folder> (default: the current directory), --agora <UTC ISO> and
--sistema nt|posix (default: os.name; the tests pass the last two). Every command except init and a global set
rescans the root first, and the root must be an existing folder. A relative --pasta resolves against the current directory.
Exit 0 ok; 1 refusal, the error code first on the message; 2 bad-registry.

status runs `ledger.py status --json` (this plugin's own, 30 s timeout) in each project folder that has a ledger:
"entrega" has the slug, autonomo, pausada, the text of each `ask` step (espera), the open VALIDAR count and what
is left (tarefas, ciclos). A ledger that fails or is not JSON gives the warning "ledger unreadable" and
"entrega": null; the other projects are unaffected. A project that waits for the owner comes first. Warnings:
half-update (.superpowers/atualizar.json), "version X (hub Y)" when the project's `git config foreman.home` holds
another plugin version than this hub's plugin.json (none without foreman.home or a .git of its own), missing-folder.
ledger.py runs with --ledger on the project's own file and FOREMAN_CAPACITY_DISK_GB=unknown, so it never writes in the
project (its disk watch would). The timeout kills only ledger.py; a grandchild holding the pipe can delay it. Text from
a project (slug, ask sentences, names) is collapsed to one line of at most 200 characters.

Rules
-----

- Project marker: a direct subfolder of the root whose .claude/settings.local.json or .claude/settings.json has,
  in "enabledPlugins", a key "foreman@<marketplace>" with the value true. A settings file that is not JSON
  never marks a project and is named in "avisos". A missing CLAUDE.md only says "no kickoff".
- Project name = folder name, [A-Za-z0-9][A-Za-z0-9._-]* (whole name), compared with casefold(). Another name is ignored, with a warning.
  A registered name wins over the scan; add refuses a name the registry or the scan already has.
- Registry: <root>/.superpowers/hub.json, written only by this script, atomically (temp file, os.replace).
  {"abrir": null, "bg": null, "projetos": {"<name>": {"pasta": "<absolute>", "conta": null, "abrir": null}}}
  "abrir" is a command with {pasta}, {nome} and {conta}; "conta" is a free label. "bg" null means unset. set on a scanned project
  keeps it "varredura" and stores only what it sets. A registry that is not a JSON object: exit 2, untouched.
- Never writes inside a project folder; the only files written are the registry and, by set --prioridade and
  liberar, the machine's memory file (memoria.py, beside ledger.py, owns its format, lock and expiry).

Memory: status reads the memory file and lists, under "memoria", its live reservations and waiting requests, and the
priorities ("memory:" lines in the text); a file that cannot be read is the warning "memoria unreadable: <path>".
set --prioridade and liberar address a project by name and write it by its folder, as ledger.py keys it (memoria.key),
so a project outside the root needs add first. ledger.py status runs with FOREMAN_MEMORIA_LEITURA=1, so the hub's read
never renews a reservation: one that a dead session left expires after 2 h, or the owner frees it with liberar.

delegate refuses an unknown project, a missing folder and a half update, then stores {"texto", "em"} and the estado
"enviado" ("nao-entregue" with the flag); the text is only stored, never run. status derives "sem-resposta" (and
"minutos") from "enviado" when the project's ledger.jsonl was not modified after "em", from one minute on.
abrir runs, in the project folder with the CLAUDE* variables (except CLAUDE_CONFIG_DIR), NO_COLOR and
GIT_TERMINAL_PROMPT removed (unless defined at User or Machine level on Windows), within 60 s: the project's
"abrir", else the global one, by `sh -c` with {pasta}, {nome} and {conta} shlex-quoted ({conta} empty without one);
else, as an argument list without a shell, `wt.exe -w new -d <pasta> claude --permission-mode auto -n <nome>` on nt
(PowerShell Start-Process when wt.exe is not in PATH) or `claude --bg --permission-mode auto -n <nome>` when bg is on
(project, else global) and, on posix with no abrir, as a fallback with a warning. A non-zero exit, a command that is
not found or the timeout is open-failed, with the command and its output. With bg off and no abrir, posix refuses.
Never quote a placeholder in an abrir template ('{pasta}' breaks): hub.py already quotes it, and set/add refuse it.
A placeholder inside a longer quoted string breaks the same way and is not detected ('cd {pasta}/sub'). Under
Git for Windows sh, a value starting with / is rewritten as an MSYS path. wt.exe has `;` as its own separator, so a ;
in the folder is escaped. Writing commands hold <root>/.superpowers/hub.lock, which holds its owner's token (a lock older than 30 s is taken
over; a lock is only ever removed by the token that wrote or read it). "bg" in status is that effective value.

Errors (code, exit): unknown-project 1 (lists the names), missing-folder 1, is-project 1 (any command but status, in a
folder with .superpowers/ledger.jsonl), exists 1 (name taken, or the folder is the root or already named), bad-name 1, usage 1 (also a bad
argument or a --raiz that is not a folder), open-failed 1, half-update 1, busy 1 (hub.lock stayed held for 10 s; the message names the file,
which can be deleted when no hub command is running), bad-memory 1 (the memory file is not valid; nothing was overwritten), bad-registry 2 (nothing was overwritten).
"""
import argparse, contextlib, datetime, json, math, os, re, shlex, shutil, subprocess, sys, tempfile, time

NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
PLUGIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
LEDGER = os.path.join(PLUGIN, "skills", "manager", "ledger.py")
OPEN_TIMEOUT = 60  # seconds for an opener to return the terminal
TIMEOUT = 30  # seconds per ledger.py call, so one slow project cannot hang the status
INSTALL = "claude plugin install foreman@foreman --scope local"
sys.path.insert(0, os.path.join(PLUGIN, "skills", "manager"))
import memoria  # noqa: E402  the machine's memory reservations, shared with ledger.py


class Refuse(Exception):
    def __init__(self, code, msg, exit=1):
        super().__init__(f"{code}: {msg}")
        self.exit = exit


def reg_path(raiz):
    return os.path.join(raiz, ".superpowers", "hub.json")


def valid(d):
    """The shape of hub.json: abrir a string, bg a bool, projetos a dict of dicts with string pasta, conta, abrir."""
    if not isinstance(d, dict) or not isinstance(d.get("projetos", {}), dict):
        return False
    if not (d.get("abrir") is None or isinstance(d["abrir"], str)):
        return False
    if not (d.get("dono") is None or isinstance(d["dono"], str)):
        return False
    if not isinstance(d.get("sessoes", []), list) or not all(isinstance(x, str) for x in d.get("sessoes", [])):
        return False
    if not (d.get("bg") is None or isinstance(d["bg"], bool)):
        return False
    for e in d.get("projetos", {}).values():
        if not isinstance(e, dict) or not (e.get("bg") is None or isinstance(e["bg"], bool)):
            return False
        if not all(isinstance(e[k], str) for k in ("pasta", "conta", "abrir", "estado") if e.get(k) is not None):
            return False
        ped = e.get("pedido")
        if not (ped is None or isinstance(ped, dict) and isinstance(ped.get("texto"), str)
                and isinstance(ped.get("em"), str)):
            return False
    return True


def clean(x, cap=200):
    """Text that comes from a project, safe for the hub's context: one printable line, at most cap characters."""
    text = " ".join("".join(c if c.isprintable() else " " for c in str(x)).split())
    return text[:cap] if cap else text


def load(raiz):
    p = reg_path(raiz)
    if not os.path.exists(p):
        return {"abrir": None, "bg": None, "projetos": {}}
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if not valid(d):
            raise ValueError("wrong shape")
    except (ValueError, OSError):
        raise Refuse("bad-registry", f"{p} is not a valid hub registry; nothing was overwritten", 2)
    d.setdefault("abrir", None), d.setdefault("bg", None), d.setdefault("projetos", {})
    return d


def save(raiz, dados):
    p = reg_path(raiz)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="hub.", suffix=".tmp", dir=os.path.dirname(p))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.write("\n")
        for attempt in range(20):  # on Windows a reader holding the file makes the replace fail for a moment
            try:
                os.replace(tmp, p)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.05)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


drop = memoria.drop  # removes a lock file only while it still holds its owner's token


@contextlib.contextmanager
def locked(raiz, wait=10, stale=30):
    """One writer at a time: <root>/.superpowers/hub.lock, memoria.lock's scheme, retried for ~10 s, removed after."""
    path = os.path.join(raiz, ".superpowers", "hub.lock")
    held = memoria.lock(path, wait=wait, stale=stale)
    try:  # only taking the lock is translated; an error of the command itself goes up as it is
        held.__enter__()
    except memoria.Busy:
        raise Refuse("busy", f"another hub command holds {path}; if no hub command is running, delete that file")
    except PermissionError as x:
        raise Refuse("usage", f"cannot create {path}: {x}")
    try:
        yield
    finally:
        held.__exit__(None, None, None)


def marked(path, avisos, nome):
    for fn in ("settings.local.json", "settings.json"):
        f = os.path.join(path, ".claude", fn)
        if not os.path.isfile(f):
            continue
        try:
            with open(f, encoding="utf-8-sig") as fh:
                ep = json.load(fh).get("enabledPlugins")
        except (ValueError, OSError, AttributeError):
            avisos.append(f"{nome}: .claude/{fn} is not valid JSON")
            continue
        if isinstance(ep, dict) and any(k.startswith("foreman@") and v is True for k, v in ep.items()):
            return True
    return False


def scan(raiz):
    """{"projetos": {name: absolute folder}, "avisos": [...]} for the direct subfolders marked with the plugin."""
    achados, avisos = {}, []
    for nome in sorted(os.listdir(raiz)):
        path = os.path.join(raiz, nome)
        if nome.startswith(".") or not os.path.isdir(path) or not marked(path, avisos, nome):
            continue
        if NAME.fullmatch(nome):
            achados[nome] = path
        else:
            avisos.append(f"{nome}: ignored, the name must match [A-Za-z0-9][A-Za-z0-9._-]*")
    return {"projetos": achados, "avisos": avisos}


def find(nome, names):
    return next((n for n in names if n.casefold() == nome.casefold()), None)


def known(raiz, dados):
    """name -> (folder, origem) from the scan and the registry; the registry entry wins."""
    s = scan(raiz)
    todos = {n: (p, "varredura") for n, p in s["projetos"].items()}
    for n, e in dados["projetos"].items():
        if e.get("pasta"):
            todos.pop(find(n, todos) or n, None)
            todos[n] = (e["pasta"], "registro")
    return todos, s["avisos"]


def resolve(nome, todos, dados=None):
    n = find(nome or "", todos)
    if n is None and dados and find(nome or "", dados["projetos"]):
        raise Refuse("missing-folder", f"the folder of {nome!r} is gone; remove it with remove --projeto")
    if n is None:
        raise Refuse("unknown-project", f"{nome!r} is not a project; known: {', '.join(sorted(todos)) or '(none)'}")
    return n


def entrega_de(pasta):
    """The delivery from `ledger.py status --json` run in the project: None without a ledger, False if unreadable."""
    if not os.path.isfile(os.path.join(pasta, ".superpowers", "ledger.jsonl")):
        return None
    # FOREMAN_CAPACITY_DISK_GB=unknown: ledger.py then skips its disk watch, which would write disk.json here
    env = {**os.environ, "FOREMAN_CAPACITY_DISK_GB": "unknown", "FOREMAN_MEMORIA_LEITURA": "1"}
    own = os.path.join(pasta, ".superpowers", "ledger.jsonl")  # never a parent repo's ledger
    try:
        r = subprocess.run([sys.executable, LEDGER, "--ledger", own, "status", "--json"], cwd=pasta, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)
        d = json.loads(r.stdout)
        if r.returncode != 0 or not isinstance(d, dict):
            return False
        sc = d.get("scope") or {}
        asks = [clean(t) for t in d.get("pending", []) if str(t).endswith(": ask the user")]
        waits = any(x.get("step") == "ask" for x in d.get("steps", []))
        return {"slug": clean(d["slug"]), "autonomo": bool(d.get("autonomous")), "pausada": bool(d.get("paused")),
                "espera": (asks or ["ask the user"]) if waits else [],
                "validar": sum(1 for v in d.get("validar", []) if v.get("decision") is None),
                "faltam": {"tarefas": sc.get("tasks_left", 0), "ciclos": sc.get("cycles_left", 0)}}
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        return False


def versao(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)["version"]
    except (ValueError, KeyError, TypeError, OSError):
        return None


def versao_aviso(pasta):
    """["version X (hub Y)"] when the project's foreman.home holds another plugin version, else []."""
    home = ""
    if os.path.exists(os.path.join(pasta, ".git")):  # a project inside another repo has no foreman.home of its own
        try:
            home = subprocess.run(["git", "-C", pasta, "config", "--local", "--get", "foreman.home"],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  timeout=TIMEOUT).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            home = ""
    theirs = versao(os.path.join(home, ".claude-plugin", "plugin.json")) if home else None
    mine = versao(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"))
    if theirs and mine and theirs != mine:
        return [clean(f"version {theirs} (hub {mine})")]
    return []


def efetivo_bg(e, dados, sistema):
    """Explicit bg of the project, else the global one, else True on posix, where no window opener exists."""
    for v in (e.get("bg"), dados.get("bg")):
        if v is not None:
            return bool(v)
    return sistema == "posix"


def utc(t):
    try:
        d = datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)  # a naive time is UTC


def estado_de(e, pasta, agora):
    """(estado, minutos): enviado becomes sem-resposta when the ledger was not touched after the request."""
    estado, ped = e.get("estado"), e.get("pedido")
    if estado != "enviado" or not ped:
        return estado, None
    em, now = utc(ped["em"]), utc(agora)
    if em is None or now is None:
        return estado, None
    try:
        mod = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(pasta, ".superpowers", "ledger.jsonl")),
                                              datetime.timezone.utc)
    except OSError:
        mod = None
    if mod is not None and mod > em:
        return estado, None
    minutos = int((now - em).total_seconds() // 60)
    return ("sem-resposta", minutos) if minutos >= 1 else (estado, None)  # a request just sent is not yet unanswered


def listing(raiz, dados, agora, sistema):
    todos, avisos = known(raiz, dados)
    projetos = []
    for n in sorted(todos, key=str.casefold):
        pasta, origem = todos[n]
        e = dados["projetos"].get(find(n, dados["projetos"]) or n, {})
        av, entrega, estado, minutos = ["missing-folder"], None, e.get("estado"), None
        if os.path.isdir(pasta):
            av = ["half-update"] if os.path.exists(os.path.join(pasta, ".superpowers", "atualizar.json")) else []
            try:
                av.extend(versao_aviso(pasta))
            except Exception as x:  # whatever one project does, the others are still listed
                av.append(f"check failed: {type(x).__name__}")
            try:
                entrega = entrega_de(pasta)
            except Exception as x:
                av.append(f"check failed: {type(x).__name__}")
                entrega = None
            if entrega is False:
                av, entrega = av + ["ledger unreadable"], None
            try:
                estado, minutos = estado_de(e, pasta, agora)
            except Exception as x:
                av.append(f"check failed: {type(x).__name__}")
        projetos.append({"nome": clean(n), "pasta": pasta, "conta": e.get("conta"),
                         "bg": efetivo_bg(e, dados, sistema), "origem": origem,
                         "kickoff": os.path.isfile(os.path.join(pasta, "CLAUDE.md")), "avisos": av,
                         "entrega": entrega, "pedido": e.get("pedido"), "estado": estado, "minutos": minutos})
    for n, e in sorted(dados["projetos"].items(), key=lambda kv: kv[0].casefold()):
        if not find(n, todos):  # a stub of a scanned project whose folder is gone
            projetos.append({"nome": clean(n), "pasta": None, "conta": e.get("conta"),
                             "bg": efetivo_bg(e, dados, sistema), "origem": "varredura", "kickoff": False,
                             "avisos": ["missing-folder"], "entrega": None, "pedido": e.get("pedido"),
                             "estado": e.get("estado"), "minutos": None})

    def rank(p):  # the owner's turn first, then what got no answer, then the rest (stable)
        return 0 if (p["entrega"] or {}).get("espera") else 1 if p["estado"] == "sem-resposta" else 2

    projetos.sort(key=rank)
    try:
        mem = memoria.load()
    except (memoria.Corrupt, OSError):
        mem = None
        avisos.append(f"memoria unreadable: {memoria.path()}")
    return {"raiz": raiz, "dono": dados.get("dono"), "avisos": [clean(w) for w in avisos], "projetos": projetos,
            "memoria": mem}


def cmd_init(a, raiz, dados):
    if not os.path.exists(reg_path(raiz)):
        save(raiz, dados)
    if os.path.exists(os.path.join(raiz, ".git")):
        try:
            ign = subprocess.run(["git", "check-ignore", "-q", ".superpowers/hub.json"], cwd=raiz,
                                 capture_output=True).returncode
        except OSError:
            ign = 0
        if ign == 1:
            print("warning: .superpowers/ is not ignored by git; the registry holds account labels")
    print(f"hub registry at {reg_path(raiz)}")


def cmd_status(a, raiz, dados):
    lst = listing(raiz, dados, a.agora or now(), a.sistema)
    if a.json:
        print(json.dumps(lst, ensure_ascii=False, indent=2))
        return
    for w in lst["avisos"]:
        print(f"warning: {w}")
    if not lst["projetos"]:
        print(f"No projects with the plugin under {raiz}. In a project folder, run: {INSTALL}")
    mem = lst["memoria"] or {"reservas": [], "pedidos": [], "prioridades": {}}
    for r in mem["reservas"]:
        print(f"memory: {clean(r.get('nome'))} {r.get('gb')} GB ({clean(r.get('rotulo'))}) since {clean(r.get('desde'))}")
    for r in mem["pedidos"]:
        print(f"memory waits: {clean(r.get('nome'))} {r.get('copias')} x {r.get('gb')} GB, priority "
              f"{memoria.priority(mem, r.get('projeto')):g}, since {clean(r.get('desde'))}")
    for p in lst["projetos"]:
        en = p["entrega"]
        extra = [f"conta {clean(p['conta'])}"] if p["conta"] else []
        if p["pedido"]:
            extra += [f"request {p['estado']}: {clean(p['pedido']['texto'])}"]
        if p["estado"] == "sem-resposta":
            extra += [f"no answer for {p['minutos']} min: the message may be held in the project's window; approve "
                      "there or send it again"]
        if en:
            extra += [f"delivery {en['slug']}"] + [f"waits: {t}" for t in en["espera"]]
            extra += (["autonomous"] if en["autonomo"] else []) + (["paused"] if en["pausada"] else [])
            extra += [f"{en['validar']} VALIDAR open"] if en["validar"] else []
            extra += [f"{en['faltam']['tarefas']} tasks, {en['faltam']['ciclos']} cycles left"]
        print(f"{p['nome']} [{p['origem']}] {clean(p['pasta'], None) if p['pasta'] else '(gone)'}"
              + "".join(f" | {x}" for x in extra + p["avisos"] + ([] if p["kickoff"] else ["no kickoff"])))


def template(abrir):
    if abrir and re.search(r"['\"]\{(pasta|nome|conta)\}", abrir):
        raise Refuse("usage", "do not quote the placeholders in abrir: hub.py quotes {pasta}, {nome} and {conta}")


def cmd_add(a, raiz, dados):
    template(a.abrir)
    if not NAME.fullmatch(a.nome):
        raise Refuse("bad-name", "the name must match [A-Za-z0-9][A-Za-z0-9._-]*")
    todos, _ = known(raiz, dados)
    if find(a.nome, todos) or find(a.nome, dados["projetos"]):
        raise Refuse("exists", f"{a.nome!r} is already a project")
    pasta = os.path.abspath(a.pasta)
    if not os.path.isdir(pasta):
        raise Refuse("missing-folder", f"{pasta} does not exist")
    norm = (lambda x: os.path.realpath(x).casefold()) if a.sistema == "nt" else os.path.realpath
    if norm(pasta) in [norm(raiz)] + [norm(p) for p, _ in todos.values()]:
        raise Refuse("exists", f"{pasta} is the hub root or already has a name")
    dados["projetos"][a.nome] = {"pasta": pasta, "conta": a.conta or None, "abrir": a.abrir or None}
    save(raiz, dados)


def pasta_de(raiz, dados, nome):
    todos, _ = known(raiz, dados)
    n = resolve(nome, todos, dados)
    return n, todos[n][0]


def memory_write(fn, *args):
    try:
        return fn(*args)
    except memoria.Busy as x:
        raise Refuse("busy", f"another command holds {x}; if none is running, delete that file")
    except memoria.Corrupt as x:
        raise Refuse("bad-memory", f"{x} is not a valid memory file; nothing was overwritten")


def cmd_liberar(a, raiz, dados):
    n, pasta = pasta_de(raiz, dados, a.projeto)
    count = memory_write(memoria.release, memoria.key(pasta), a.rotulo)
    print(f"released {count} reservation{'' if count == 1 else 's'} of {n}")


def cmd_set(a, raiz, dados):
    template(a.abrir)
    if a.prioridade is not None:
        if a.projeto is None:
            raise Refuse("usage", "--prioridade needs --projeto")
        n, pasta = pasta_de(raiz, dados, a.projeto)
        memory_write(memoria.set_priority, memoria.key(pasta), n, a.prioridade)
    if a.projeto is None:
        if a.conta is not None:
            raise Refuse("usage", "--conta needs --projeto")
        if a.estado:
            raise Refuse("usage", "--estado needs --projeto")
        if a.abrir is not None:
            dados["abrir"] = a.abrir or None
        if a.bg:
            dados["bg"] = a.bg == "on"
    else:
        todos, _ = known(raiz, dados)
        n = resolve(a.projeto, todos, dados)
        e = dados["projetos"].setdefault(find(n, dados["projetos"]) or n, {})  # a scanned project gets no "pasta"
        if a.conta is not None:
            e["conta"] = a.conta or None
        if a.abrir is not None:
            e["abrir"] = a.abrir or None
        if a.bg:
            e["bg"] = a.bg == "on"
        if a.estado:
            e["estado"] = a.estado
    save(raiz, dados)


def cmd_claim(a, raiz, dados):
    dados["dono"] = a.sessao
    dados["sessoes"] = ([x for x in dados.get("sessoes", []) if x != a.sessao] + [a.sessao])[-5:]
    save(raiz, dados)


def cmd_remove(a, raiz, dados):
    todos, _ = known(raiz, dados)
    n = find(a.projeto, dados["projetos"])
    if n is None:
        resolve(a.projeto, todos)  # unknown-project, or a scanned one that has no entry to drop
        raise Refuse("usage", f"{a.projeto!r} comes from the scan; there is no registry entry to remove")
    del dados["projetos"][n]
    save(raiz, dados)


def pronto(raiz, dados, nome):
    """(name, folder, entry) of a project that can take a request: known, with its folder and no half update."""
    todos, _ = known(raiz, dados)
    n = resolve(nome, todos, dados)
    pasta = todos[n][0]
    if not os.path.isdir(pasta):
        raise Refuse("missing-folder", f"{pasta} does not exist; remove the entry with remove --projeto {n}")
    if os.path.exists(os.path.join(pasta, ".superpowers", "atualizar.json")):
        raise Refuse("half-update", "finish the update in the project's own session first")
    return n, pasta, dados["projetos"].get(find(n, dados["projetos"]) or n, {})


def cmd_delegate(a, raiz, dados):
    n = pronto(raiz, dados, a.projeto)[0]
    e = dados["projetos"].setdefault(find(n, dados["projetos"]) or n, {})
    e["pedido"] = {"texto": a.texto[:200], "em": a.agora or now()}
    e["estado"] = "nao-entregue" if a.nao_entregue else "enviado"
    save(raiz, dados)  # the text is only stored, never run


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def persistent_env(sistema):
    """Upper-case names defined at User or Machine level on Windows (kept by clean_env); none elsewhere."""
    names = set()
    if sistema == "nt" and os.name == "nt":
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, "Environment"), (winreg.HKEY_LOCAL_MACHINE,
                          r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    i = 0
                    while True:
                        names.add(winreg.EnumValue(k, i)[0].upper())
                        i += 1
            except OSError:
                pass
    return names


def clean_env(environ, persistent):
    """Without this a window opened from this session is a CLAUDE_CODE_CHILD_SESSION child, with no transcript or color."""
    drop = lambda k: (k.upper().startswith("CLAUDE") and k.upper() != "CLAUDE_CONFIG_DIR"
                      or k.upper() in ("NO_COLOR", "GIT_TERMINAL_PROMPT")) and k.upper() not in persistent
    return {k: v for k, v in environ.items() if not drop(k)}


def comando(a, n, pasta, e, dados):
    """(argv, text shown, warning): a registered abrir by sh -c with quoted values, else a default as an argument list."""
    abrir = e.get("abrir") or dados.get("abrir")
    conta = e.get("conta") or ""
    if abrir:
        vals = {"pasta": pasta, "nome": n, "conta": conta}
        cmd = re.sub(r"\{(pasta|nome|conta)\}", lambda m: shlex.quote(vals[m.group(1)]), abrir)
        return ["sh", "-c", cmd], cmd, None
    flags = ["claude", "--permission-mode", "auto", "-n", n]
    explicit = next((v for v in (e.get("bg"), dados.get("bg")) if v is not None), None)
    if explicit is True or (a.sistema != "nt" and explicit is None):
        warn = None if explicit else ("warning: no abrir is registered on this system, so the session starts with "
                                      "claude --bg in autonomous mode and nobody sees it; register a window opener "
                                      "with set --abrir")
        return ["claude", "--bg"] + flags[1:], None, warn
    if a.sistema != "nt":
        raise Refuse("open-failed", "no abrir is registered and bg is off, so there is nothing to open the window "
                                    "with; register one with set --abrir")
    if shutil.which("wt.exe"):
        return ["wt.exe", "-w", "new", "-d", pasta.replace(";", "\\;")] + flags, None, None  # ; separates wt commands
    q = lambda t: re.sub("['\u2018\u2019\u201a\u201b]", lambda m: m.group(0) * 2, t)  # all four are quotes to PowerShell
    ps = (f"Start-Process -FilePath claude -ArgumentList '--permission-mode','auto','-n','{q(n)}' "
          f"-WorkingDirectory '{q(pasta)}'")
    return ["powershell", "-NoProfile", "-Command", ps], None, None


def cmd_abrir(a, raiz, dados):
    n, pasta, e = pronto(raiz, dados, a.projeto)
    argv, shown, warn = comando(a, n, pasta, e, dados)
    shown = shown or " ".join(argv)
    if warn:
        print(warn)
    if a.mostrar:
        print(shown)
        return
    env = clean_env(os.environ, persistent_env(a.sistema))
    if argv[0] == "sh" and not shutil.which("sh", path=env.get("PATH")):
        raise Refuse("open-failed", f"{shown}\nsh was not found")
    with tempfile.TemporaryFile() as sink:  # a file, not a pipe: a window that keeps the handle cannot hold us
        try:
            r = subprocess.run(argv, cwd=pasta, env=env, stdin=subprocess.DEVNULL, stdout=sink,
                               stderr=subprocess.STDOUT, timeout=OPEN_TIMEOUT)
            code = r.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
        except OSError as x:
            raise Refuse("open-failed", f"{shown}\n{x}")
        sink.seek(0)
        texto = sink.read().decode("utf-8", "replace")
    if code == "timeout":
        raise Refuse("open-failed", f"{shown}\nthe command did not return the terminal within {OPEN_TIMEOUT} s; "
                                     "whatever it started may still open a window")
    if code != 0:
        raise Refuse("open-failed", f"{shown}\nexit {code}: {clean(texto, 500)}")
    print(f"opened {n}: {shown}")


class Parser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):  # an abbreviation is refused, so --rai is never read as --raiz
        super().__init__(*args, allow_abbrev=False, **kwargs)

    def error(self, message):  # exit 2 is reserved for bad-registry
        self.print_usage(sys.stderr)
        raise Refuse("usage", message)


def main(argv=None):
    com = argparse.ArgumentParser(add_help=False)
    com.add_argument("--raiz", default=os.getcwd())
    com.add_argument("--agora")
    com.add_argument("--sistema", choices=["nt", "posix"], default=os.name)
    ap = Parser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=Parser)
    sub.add_parser("init", parents=[com]).set_defaults(fn=cmd_init)
    p = sub.add_parser("status", parents=[com])
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("add", parents=[com])
    p.add_argument("--nome", required=True)
    p.add_argument("--pasta", required=True)
    p.add_argument("--conta")
    p.add_argument("--abrir")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("set", parents=[com])
    p.add_argument("--projeto")
    p.add_argument("--conta")
    p.add_argument("--abrir")
    p.add_argument("--bg", choices=["on", "off"])
    p.add_argument("--estado", choices=["respondido"])
    p.add_argument("--prioridade", type=int)
    p.set_defaults(fn=cmd_set)
    p = sub.add_parser("liberar", parents=[com])
    p.add_argument("--projeto", required=True)
    p.add_argument("--rotulo")
    p.set_defaults(fn=cmd_liberar)
    p = sub.add_parser("delegate", parents=[com])
    p.add_argument("--projeto", required=True)
    p.add_argument("--nao-entregue", action="store_true")
    p.set_defaults(fn=cmd_delegate)
    p = sub.add_parser("abrir", parents=[com])
    p.add_argument("--projeto", required=True)
    p.add_argument("--mostrar", action="store_true")
    p.set_defaults(fn=cmd_abrir)
    p = sub.add_parser("claim", parents=[com])
    p.add_argument("--sessao", required=True)
    p.add_argument("--espera", type=float, default=10)  # seconds to wait for hub.lock; the hook passes a short one
    p.set_defaults(fn=cmd_claim)
    p = sub.add_parser("remove", parents=[com])
    p.add_argument("--projeto", required=True)
    p.set_defaults(fn=cmd_remove)
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        a = ap.parse_args(argv)
        raiz = os.path.abspath(a.raiz)
        if not os.path.isdir(raiz):
            raise Refuse("usage", f"the hub root {raiz} must be an existing folder")
        if a.cmd != "status" and os.path.exists(os.path.join(raiz, ".superpowers", "ledger.jsonl")):
            raise Refuse("is-project", "this folder is a project (it has a ledger); open the hub in the root folder")
        if a.agora and utc(a.agora) is None:
            raise Refuse("usage", f"--agora {a.agora!r} is not an ISO time")
        if a.cmd == "claim":  # checked before the lock is waited for
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", a.sessao):
                raise Refuse("usage", "--sessao must match [A-Za-z0-9._-]{1,100}")
            if not math.isfinite(a.espera):
                raise Refuse("usage", "--espera must be a number of seconds")
            a.espera = min(max(a.espera, 0), 10)
        if a.cmd == "delegate":  # read before taking the lock, so a slow writer of stdin never holds it
            if sys.stdin.isatty():
                raise Refuse("usage", "the request text comes on stdin, not from a terminal")
            a.texto = sys.stdin.read(4096)
            if not a.texto.strip():
                raise Refuse("usage", "the request text comes on stdin and is empty")
        if a.cmd in ("init", "add", "set", "remove", "delegate", "claim", "liberar"):
            with locked(raiz, wait=getattr(a, "espera", 10)):  # load, change and save as one step
                a.fn(a, raiz, load(raiz))
        else:
            a.fn(a, raiz, load(raiz))
    except Refuse as e:
        print(e, file=sys.stderr)
        return e.exit
    return 0


if __name__ == "__main__":
    sys.exit(main())
