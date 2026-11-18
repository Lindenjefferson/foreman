import json, os, subprocess, sys, tempfile

HUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hub.py")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("PASS" if ok else "FAIL", name, "" if ok else f"| {str(detail)[-300:]}")


def run(raiz, *args, stdin=""):
    return subprocess.run([sys.executable, HUB, *args, "--raiz", raiz, "--agora", "2030-01-01T00:00:00Z",
                           "--sistema", "posix"], input=stdin, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=tempfile.gettempdir())


def status(raiz):
    r = run(raiz, "status", "--json")
    return r, (json.loads(r.stdout) if r.stdout.strip().startswith("{") else {})


def root():
    return os.path.realpath(tempfile.mkdtemp(prefix="hub raiz "))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def marker(raiz, nome, settings="settings.local.json", body=None):
    write(os.path.join(raiz, nome, ".claude", settings),
          json.dumps(body if body is not None else {"enabledPlugins": {"foreman@foreman": True}}))


def names(d):
    return [p["nome"] for p in d.get("projetos", [])]


def proj(d, nome):
    return [p for p in d["projetos"] if p["nome"] == nome][0]


def tree(*dirs):
    snap = {}
    for d in dirs:
        for base, _, files in os.walk(d):
            for f in files:
                with open(os.path.join(base, f), "rb") as fh:
                    snap[os.path.join(base, f)] = fh.read()
            snap[base] = None
    return snap


def out(r):
    return r.stdout + r.stderr


# AC-T1-1
r0 = root()
marker(r0, "a")
os.makedirs(os.path.join(r0, "b"))
r, d = status(r0)
check("AC_T1_1 scan finds only the marked folder", r.returncode == 0 and names(d) == ["a"]
      and d["projetos"][0]["origem"] == "varredura" and d["projetos"][0]["entrega"] is None, out(r))
r1 = root()
marker(r1, "c", "settings.json")
check("AC_T1_1 settings.json counts too", names(status(r1)[1]) == ["c"])

# AC-T1-2
r2 = root()
marker(r2, "f", body={"enabledPlugins": {"foreman@foreman": False}})
marker(r2, "p", body={"permissions": {"allow": ["Bash(foreman:*)"]}})
marker(r2, "x", body={"enabledPlugins": {"other@foreman": True}})
write(os.path.join(r2, "bad", ".claude", "settings.local.json"), "{nope")
r, d = status(r2)
check("AC_T1_2 false, permissions only, other plugin and bad JSON are not projects", r.returncode == 0
      and names(d) == [], out(r))
check("AC_T1_2 the invalid JSON is named in avisos", any("bad" in a for a in d["avisos"]), d)

# AC-T1-3
r3 = root()
outside = os.path.realpath(tempfile.mkdtemp(prefix="hub fora "))
r = run(r3, "add", "--nome", "x", "--pasta", outside, "--conta", "c1")
r_, d = status(r3)
check("AC_T1_3 add registers a project outside the root", r.returncode == 0 and names(d) == ["x"]
      and d["projetos"][0]["origem"] == "registro" and d["projetos"][0]["conta"] == "c1", out(r))
r = run(r3, "add", "--nome", "X", "--pasta", outside)
check("AC_T1_3 a duplicate name in another case exits 1", r.returncode == 1, out(r))
r = run(r3, "add", "--nome", "bad name", "--pasta", outside)
check("AC_T1_3 an invalid name exits 1", r.returncode == 1, out(r))
r = run(r3, "add", "--nome", "y", "--pasta", os.path.join(outside, "nao"))
check("AC_T1_3 a missing folder exits 1 with missing-folder", r.returncode == 1 and out(r).startswith("missing-folder"),
      out(r))
marker(r3, "s")
r = run(r3, "add", "--nome", "S", "--pasta", outside)
check("AC_T1_3 a name taken by the scan exits 1", r.returncode == 1, out(r))

# set
r = run(r3, "set", "--projeto", "x", "--conta", "c2", "--abrir", "open {pasta}", "--bg", "on")
r_, d = status(r3)
check("set persists conta, abrir and bg", r.returncode == 0 and proj(d, "x")["conta"] == "c2"
      and proj(d, "x")["bg"] is True, out(r))
r = run(r3, "set", "--projeto", "X", "--bg", "off")
check("set matches the name ignoring case", r.returncode == 0 and proj(status(r3)[1], "x")["bg"] is False, out(r))
r = run(r3, "set", "--projeto", "x", "--conta", "")
check("set --conta empty clears it", r.returncode == 0 and proj(status(r3)[1], "x")["conta"] is None, out(r))
r = run(r3, "set", "--abrir", "wt -d {pasta} claude")
with open(os.path.join(r3, ".superpowers", "hub.json"), encoding="utf-8") as f:
    reg = json.load(f)
check("set without --projeto sets the global abrir", r.returncode == 0 and reg["abrir"] == "wt -d {pasta} claude", reg)
r = run(r3, "set", "--projeto", "s", "--conta", "k")
ps = proj(status(r3)[1], "s")
check("set on a scanned project keeps origem varredura", r.returncode == 0 and ps["conta"] == "k"
      and ps["origem"] == "varredura", out(r))
r = run(r3, "set", "--projeto", "nope", "--conta", "k")
check("set on an unknown project exits 1 with unknown-project and the names", r.returncode == 1
      and out(r).startswith("unknown-project") and "x" in out(r), out(r))
r = run(r3, "set", "--conta", "k")
check("set --conta without --projeto exits 1", r.returncode == 1, out(r))

# AC-T1-4
r4 = root()
gone = os.path.realpath(tempfile.mkdtemp(prefix="hub gone "))
run(r4, "add", "--nome", "x", "--pasta", gone)
os.rmdir(gone)
r, d = status(r4)
check("AC_T1_4 a missing folder stays listed with missing-folder", names(d) == ["x"]
      and "missing-folder" in d["projetos"][0]["avisos"], out(r))
r = run(r4, "remove", "--projeto", "X")
check("AC_T1_4 remove drops it", r.returncode == 0 and names(status(r4)[1]) == [], out(r))
r = run(r4, "remove", "--projeto", "x")
check("AC_T1_4 removing again exits 1", r.returncode == 1 and "unknown-project" in out(r), out(r))

# AC-T1-5
r5 = root()
write(os.path.join(r5, ".superpowers", "ledger.jsonl"), "")
r = run(r5, "init")
check("AC_T1_5 init in a project exits 1 with is-project and creates nothing", r.returncode == 1
      and "is-project" in out(r) and not os.path.exists(os.path.join(r5, ".superpowers", "hub.json")), out(r))
r6 = root()
subprocess.run(["git", "init", "-q"], cwd=r6, check=True)
r = run(r6, "init")
check("AC_T1_5 init in a git root without the ignore warns and creates the registry", r.returncode == 0
      and os.path.exists(os.path.join(r6, ".superpowers", "hub.json")) and "not ignored" in r.stdout.lower(), out(r))
r7 = root()
subprocess.run(["git", "init", "-q"], cwd=r7, check=True)
write(os.path.join(r7, ".gitignore"), ".superpowers/\n")
r = run(r7, "init")
check("AC_T1_5 no warning when ignored", r.returncode == 0 and "not ignored" not in r.stdout.lower(), out(r))
check("init twice is harmless", run(r7, "init").returncode == 0)

# AC-T1-6
r8 = root()
garbage = b'{"abrir": \xff nope'
os.makedirs(os.path.join(r8, ".superpowers"))
with open(os.path.join(r8, ".superpowers", "hub.json"), "wb") as f:
    f.write(garbage)
outside8 = os.path.realpath(tempfile.mkdtemp(prefix="hub o "))
ok = True
for args in (["init"], ["status"], ["status", "--json"], ["add", "--nome", "q", "--pasta", outside8],
             ["set", "--abrir", "x"], ["remove", "--projeto", "q"]):
    r = run(r8, *args)
    with open(os.path.join(r8, ".superpowers", "hub.json"), "rb") as f:
        same = f.read() == garbage
    good = r.returncode == 2 and "bad-registry" in out(r) and same
    ok = ok and good
    if not good:
        print("   ", args, r.returncode, out(r))
check("AC_T1_6 every subcommand exits 2 and leaves hub.json untouched", ok)

# AC-T1-7
r9 = root()
marker(r9, "my proj")
r, d = status(r9)
check("AC_T1_7 a folder with a space is not a project and is named", names(d) == []
      and any("my proj" in a for a in d["avisos"]), out(r))

# AC-T1-8
r10 = root()
r = run(r10, "status")
check("AC_T1_8 empty root exits 0 and says how to install", r.returncode == 0
      and "claude plugin install foreman@foreman --scope local" in r.stdout, out(r))

# half-update and kickoff flags
r11 = root()
marker(r11, "k")
write(os.path.join(r11, "k", "CLAUDE.md"), "x")
write(os.path.join(r11, "k", ".superpowers", "atualizar.json"), "{}")
marker(r11, "n")
d = status(r11)[1]
check("kickoff flag and half-update warning", proj(d, "k")["kickoff"] is True
      and "half-update" in proj(d, "k")["avisos"] and proj(d, "n")["kickoff"] is False
      and proj(d, "n")["avisos"] == [], d)
r = run(r11, "status")
check("text status lists each project", r.returncode == 0 and "half-update" in r.stdout, out(r))

# AC-T1-9
r12 = root()
marker(r12, "p1")
write(os.path.join(r12, "p1", "CLAUDE.md"), "a b")
marker(r12, "p2")
out12 = os.path.realpath(tempfile.mkdtemp(prefix="hub out "))
before = tree(os.path.join(r12, "p1"), os.path.join(r12, "p2"), out12)
for args in (["init"], ["status"], ["status", "--json"], ["add", "--nome", "o", "--pasta", out12],
             ["set", "--projeto", "p1", "--conta", "c", "--bg", "on"], ["set", "--abrir", "z"],
             ["remove", "--projeto", "o"]):
    run(r12, *args)
check("AC_T1_9 project folders are unchanged by every subcommand",
      tree(os.path.join(r12, "p1"), os.path.join(r12, "p2"), out12) == before)
check("AC_T1_9 the only file written in the root is hub.json",
      sorted(os.listdir(os.path.join(r12, ".superpowers"))) == ["hub.json"], os.listdir(os.path.join(r12, ".superpowers")))

# fix round 1
def reg_bytes(raiz, text):
    os.makedirs(os.path.join(raiz, ".superpowers"), exist_ok=True)
    with open(os.path.join(raiz, ".superpowers", "hub.json"), "wb") as f:
        f.write(text)


f1 = root()
write(os.path.join(f1, ".superpowers", "ledger.jsonl"), "")
o1 = os.path.realpath(tempfile.mkdtemp(prefix="hub o "))
ra = run(f1, "add", "--nome", "o", "--pasta", o1)
rs = run(f1, "set", "--bg", "on")
rr = run(f1, "remove", "--projeto", "o")
check("FIX1 add, set and remove in a project folder are refused and write nothing",
      all(x.returncode == 1 and "is-project" in out(x) for x in (ra, rs, rr))
      and not os.path.exists(os.path.join(f1, ".superpowers", "hub.json")), out(ra) + out(rs))
check("FIX1 status still works in a project folder", run(f1, "status").returncode == 0)

ok = True
for i, body in enumerate((b'{"projetos":{"x":"oops"}}', b'{"projetos":{"x":{"pasta":5}}}',
                          b'{"projetos":{"x":{"pasta":["l"]}}}', b'{"projetos":{"x":{"conta":3}}}',
                          b'{"projetos":{"x":{"abrir":[]}}}', b'{"projetos":[]}', b'[]')):
    f2 = root()
    reg_bytes(f2, body)
    r = run(f2, "status")
    with open(os.path.join(f2, ".superpowers", "hub.json"), "rb") as fh:
        same = fh.read() == body
    good = r.returncode == 2 and "bad-registry" in out(r) and "Traceback" not in out(r) and same
    ok = ok and good
    if not good:
        print("   ", body, r.returncode, out(r))
check("FIX2 a registry with the wrong shape exits 2 and stays untouched", ok)

f3 = root()
marker(f3, "S")
run(f3, "set", "--projeto", "S", "--conta", "old")
import shutil
shutil.rmtree(os.path.join(f3, "S"))
o3 = os.path.realpath(tempfile.mkdtemp(prefix="hub o "))
r = run(f3, "add", "--nome", "s", "--pasta", o3, "--conta", "new")
check("FIX3 add refuses a name held by a registry entry without pasta", r.returncode == 1 and "exists" in out(r), out(r))
d = status(f3)[1]
check("FIX9 an entry without pasta whose folder vanished is listed with missing-folder", names(d) == ["S"]
      and "missing-folder" in d["projetos"][0]["avisos"] and d["projetos"][0]["conta"] == "old", d)
check("FIX9 and remove drops it", run(f3, "remove", "--projeto", "s").returncode == 0 and names(status(f3)[1]) == [])

f4 = root()
o4 = os.path.realpath(tempfile.mkdtemp(prefix="hub o "))
ok = True
for bad in ("x\n", "-n", "..", ".", "_x", ""):
    r = run(f4, "add", "--nome=" + bad, "--pasta", o4)
    ok = ok and r.returncode == 1 and "bad-name" in out(r)
check("FIX4 names with a trailing newline, a leading dash or dot are refused", ok)
check("FIX4 a normal name with dots and dashes is accepted", run(f4, "add", "--nome", "a.b-c_d", "--pasta", o4).returncode == 0)

f5 = root()
marker(f5, "p")
o5 = os.path.realpath(tempfile.mkdtemp(prefix="hub o "))
run(f5, "add", "--nome", "one", "--pasta", o5)
ok = True
for pasta in (o5, os.path.join(o5, "..", os.path.basename(o5)), os.path.join(f5, "p"), f5):
    r = run(f5, "add", "--nome", "two", "--pasta", pasta)
    ok = ok and r.returncode == 1 and "exists" in out(r)
check("FIX5 one folder does not get two names, and the root is not a project", ok)

r = run(f5, "status", "--bogus")
check("FIX6 an argparse error exits 1 with the usage code", r.returncode == 1 and out(r).startswith("usage"), out(r))

nr = os.path.join(root(), "nope")
r1_, r2_ = run(nr, "status"), run(nr, "init")
check("FIX7 a missing --raiz is refused for status and init and nothing is created",
      r1_.returncode == 1 and r2_.returncode == 1 and "usage" in out(r1_) + out(r2_)
      and "Traceback" not in out(r1_) + out(r2_) and not os.path.exists(nr), out(r1_) + out(r2_))

f8 = root()
os.makedirs(os.path.join(f8, "b", ".claude"))
with open(os.path.join(f8, "b", ".claude", "settings.local.json"), "wb") as fh:
    fh.write(bytes([0xEF, 0xBB, 0xBF]) + json.dumps({"enabledPlugins": {"foreman@foreman": True}}).encode())
check("FIX8 a settings file with a BOM is accepted", names(status(f8)[1]) == ["b"])


failed = results.count(False)
print(("ALL PASS" if not failed else "FAILED") + f" ({len(results) - failed}/{len(results)})")
sys.exit(1 if failed else 0)
