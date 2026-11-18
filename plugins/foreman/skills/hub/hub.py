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

Every command takes --raiz <folder> (default: the current directory), --agora <UTC ISO> and
--sistema nt|posix (default: os.name; the tests pass the last two), and rescans the root first (a write in a folder with a ledger is refused, the root must exist).
A relative --pasta resolves against the current directory. Exit 0 ok; 1 refusal, the error code first on the message; 2 bad-registry.

Rules
-----

- Project marker: a direct subfolder of the root whose .claude/settings.local.json or .claude/settings.json has,
  in "enabledPlugins", a key "foreman@<marketplace>" with the value true. A settings file that is not JSON
  never marks a project and is named in "avisos". A missing CLAUDE.md only says "no kickoff".
- Project name = folder name, [A-Za-z0-9][A-Za-z0-9._-]* (whole name), compared with casefold(). Another name is ignored, with a warning.
  A registered name wins over the scan; add refuses a name the registry or the scan already has.
- Registry: <root>/.superpowers/hub.json, written only by this script, atomically (temp file, os.replace).
  {"abrir": null, "bg": false, "projetos": {"<name>": {"pasta": "<absolute>", "conta": null, "abrir": null}}}
  "abrir" is a command with {pasta}, {nome} and {conta}; "conta" is a free label. set on a scanned project
  keeps it "varredura" and stores only what it sets. A registry that is not a JSON object: exit 2, untouched.
- Never writes inside a project folder; the only file written is the registry.

Errors (code, exit): unknown-project 1 (lists the names), missing-folder 1, is-project 1 (init on a folder with
.superpowers/ledger.jsonl), exists 1 (name taken, or the folder is the root or already named), bad-name 1, usage 1 (also a bad
argument or a --raiz that is not a folder), bad-registry 2 (nothing was overwritten).
"""
import argparse, json, os, re, subprocess, sys, tempfile

NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
INSTALL = "claude plugin install foreman@foreman --scope local"


class Refuse(Exception):
    def __init__(self, code, msg, exit=1):
        super().__init__(f"{code}: {msg}")
        self.exit = exit


def reg_path(raiz):
    return os.path.join(raiz, ".superpowers", "hub.json")


def load(raiz):
    p = reg_path(raiz)
    if not os.path.exists(p):
        return {"abrir": None, "bg": False, "projetos": {}}
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        pr = d.get("projetos", {}) if isinstance(d, dict) else None
        if not isinstance(pr, dict) or not all(isinstance(e, dict) and all(
                isinstance(e[k], str) for k in ("pasta", "conta", "abrir") if e.get(k) is not None)
                for e in pr.values()):
            raise ValueError("wrong shape")
    except (ValueError, OSError):
        raise Refuse("bad-registry", f"{p} is not a valid hub registry; nothing was overwritten", 2)
    d.setdefault("abrir", None), d.setdefault("bg", False), d.setdefault("projetos", {})
    return d


def save(raiz, dados):
    p = reg_path(raiz)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="hub.", suffix=".tmp", dir=os.path.dirname(p))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


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


def resolve(nome, todos):
    n = find(nome or "", todos)
    if n is None:
        raise Refuse("unknown-project", f"{nome!r} is not a project; known: {', '.join(sorted(todos)) or '(none)'}")
    return n


def listing(raiz, dados):
    todos, avisos = known(raiz, dados)
    projetos = []
    for n in sorted(todos, key=str.casefold):
        pasta, origem = todos[n]
        e = dados["projetos"].get(find(n, dados["projetos"]) or n, {})
        av = []
        if not os.path.isdir(pasta):
            av.append("missing-folder")
        elif os.path.exists(os.path.join(pasta, ".superpowers", "atualizar.json")):
            av.append("half-update")
        projetos.append({"nome": n, "pasta": pasta, "conta": e.get("conta"), "bg": e.get("bg", dados["bg"]),
                         "origem": origem, "kickoff": os.path.isfile(os.path.join(pasta, "CLAUDE.md")),
                         "avisos": av, "entrega": None, "pedido": e.get("pedido"), "estado": e.get("estado"),
                         "minutos": None})
    for n, e in sorted(dados["projetos"].items(), key=lambda kv: kv[0].casefold()):
        if not find(n, todos):  # a stub of a scanned project whose folder is gone
            projetos.append({"nome": n, "pasta": None, "conta": e.get("conta"), "bg": e.get("bg", dados["bg"]),
                             "origem": "varredura", "kickoff": False, "avisos": ["missing-folder"], "entrega": None,
                             "pedido": e.get("pedido"), "estado": e.get("estado"), "minutos": None})
    return {"raiz": raiz, "dono": dados.get("dono"), "avisos": avisos, "projetos": projetos}


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
    lst = listing(raiz, dados)
    if a.json:
        print(json.dumps(lst, ensure_ascii=False, indent=2))
        return
    for w in lst["avisos"]:
        print(f"warning: {w}")
    if not lst["projetos"]:
        print(f"No projects with the plugin under {raiz}. In a project folder, run: {INSTALL}")
    for p in lst["projetos"]:
        extra = [f"conta {p['conta']}"] if p["conta"] else []
        print(f"{p['nome']} [{p['origem']}] {p['pasta']}" + "".join(f" | {x}" for x in extra + p["avisos"]
              + ([] if p["kickoff"] else ["no kickoff"])))


def cmd_add(a, raiz, dados):
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


def cmd_set(a, raiz, dados):
    if a.projeto is None:
        if a.conta is not None:
            raise Refuse("usage", "--conta needs --projeto")
        if a.abrir is not None:
            dados["abrir"] = a.abrir or None
        if a.bg:
            dados["bg"] = a.bg == "on"
    else:
        todos, _ = known(raiz, dados)
        n = resolve(a.projeto, todos)
        e = dados["projetos"].setdefault(find(n, dados["projetos"]) or n, {})  # a scanned project gets no "pasta"
        if a.conta is not None:
            e["conta"] = a.conta or None
        if a.abrir is not None:
            e["abrir"] = a.abrir or None
        if a.bg:
            e["bg"] = a.bg == "on"
    save(raiz, dados)


def cmd_remove(a, raiz, dados):
    todos, _ = known(raiz, dados)
    n = find(a.projeto, dados["projetos"])
    if n is None:
        resolve(a.projeto, todos)  # unknown-project, or a scanned one that has no entry to drop
        raise Refuse("usage", f"{a.projeto!r} comes from the scan; there is no registry entry to remove")
    del dados["projetos"][n]
    save(raiz, dados)


class Parser(argparse.ArgumentParser):
    def error(self, message):  # exit 2 is reserved for bad-registry
        self.print_usage(sys.stderr)
        raise Refuse("usage", message)


def main(argv=None):
    com = argparse.ArgumentParser(add_help=False)
    com.add_argument("--raiz", default=os.getcwd())
    com.add_argument("--agora")
    com.add_argument("--sistema", choices=["nt", "posix"], default=os.name)
    ap = Parser(description=__doc__.split(chr(10))[1])
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
    p.set_defaults(fn=cmd_set)
    p = sub.add_parser("remove", parents=[com])
    p.add_argument("--projeto", required=True)
    p.set_defaults(fn=cmd_remove)
    try:
        a = ap.parse_args(argv)
        raiz = os.path.abspath(a.raiz)
        if not os.path.isdir(raiz):
            raise Refuse("usage", f"the hub root {raiz} must be an existing folder")
        if a.cmd != "status" and os.path.exists(os.path.join(raiz, ".superpowers", "ledger.jsonl")):
            raise Refuse("is-project", "this folder is a project (it has a ledger); open the hub in the root folder")
        a.fn(a, raiz, load(raiz))
    except Refuse as e:
        print(e, file=sys.stderr)
        return e.exit
    return 0


if __name__ == "__main__":
    sys.exit(main())
