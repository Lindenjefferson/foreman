import json, os, subprocess, sys, tempfile

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCRIPT = os.path.join(HOOKS, "session-start.py")
LEDGER = os.path.join(HOOKS, "..", "skills", "manager", "ledger.py")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("PASS" if ok else "FAIL", name, "" if ok else f"| {detail[-300:]}")


def run(cwd, payload=None):
    stdin = json.dumps(payload if payload is not None else {"hook_event_name": "SessionStart", "cwd": cwd})
    return subprocess.run([sys.executable, SCRIPT], cwd=tempfile.gettempdir(), input=stdin, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


project = tempfile.mkdtemp(prefix="sessionstart_")
r = run(project)
check("no ledger: prints nothing and exits 0", r.returncode == 0 and r.stdout == "" and r.stderr == "",
      r.stdout + r.stderr)

for cmd in (["init", "-q"], ["-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base"]):
    subprocess.run(["git"] + cmd, cwd=project, check=True)
subprocess.run([sys.executable, LEDGER, "start", "--slug", "retomada"], cwd=project, check=True,
               capture_output=True)
status = subprocess.run([sys.executable, LEDGER, "status"], cwd=project, capture_output=True, text=True,
                        encoding="utf-8").stdout
r = run(project)
check("with a ledger: prints the ledger status", r.returncode == 0 and status.strip() != "" and status in r.stdout,
      r.stdout + r.stderr)
check("with a ledger: says what the output is", "ledger" in r.stdout.lower().splitlines()[0], r.stdout)

r = run(project, payload={})
check("payload without cwd: falls back to the process directory and stays silent", r.returncode == 0
      and r.stdout == "", r.stdout + r.stderr)

r = subprocess.run([sys.executable, SCRIPT], cwd=tempfile.gettempdir(), input="not json", capture_output=True,
                   text=True)
check("garbage on stdin never blocks the session", r.returncode == 0 and r.stdout == "", r.stdout + r.stderr)

r = run(project, payload={"hook_event_name": "SessionStart", "source": "startup", "cwd": project})
check("a new session does not print the ledger status", r.returncode == 0 and r.stdout == "", r.stdout + r.stderr)
r = run(project, payload={"hook_event_name": "SessionStart", "source": "compact", "cwd": project})
check("after a compaction it prints the ledger status", status in r.stdout, r.stdout + r.stderr)

# The native pre-commit hook finds the scanner through foreman.home: each session points it at the running plugin.
ROOT = os.path.abspath(os.path.join(HOOKS, "..")).replace("\\", "/")
SCANNER = os.path.join(HOOKS, "pre-commit-secret-scan.py")


def home(repo):
    return subprocess.run(["git", "config", "--local", "--get", "foreman.home"], cwd=repo, capture_output=True,
                          text=True).stdout.strip()


subprocess.run([sys.executable, SCANNER, "--install-pre-commit"], cwd=project, check=True, capture_output=True)
subprocess.run(["git", "config", "--local", "foreman.home", "/no/such/older/version"], cwd=project, check=True)
r = run(project, payload={"hook_event_name": "SessionStart", "source": "startup", "cwd": project})
check("with the secret-scan hook, a session points foreman.home at the running plugin", home(project) == ROOT
      and r.returncode == 0 and r.stdout == "", home(project) + r.stdout + r.stderr)
sub = os.path.join(project, "src")
os.makedirs(sub)
subprocess.run(["git", "config", "--local", "foreman.home", "/no/such/older/version"], cwd=project, check=True)
run(sub, payload={"hook_event_name": "SessionStart", "source": "resume", "cwd": sub})
check("from a subfolder too", home(project) == ROOT, home(project))
plain = tempfile.mkdtemp(prefix="sessionstart_plain_")
subprocess.run(["git", "init", "-q"], cwd=plain, check=True)
run(plain, payload={"hook_event_name": "SessionStart", "source": "startup", "cwd": plain})
check("without the secret-scan hook, foreman.home is left alone", home(plain) == "", home(plain))
outside = tempfile.mkdtemp(prefix="sessionstart_nogit_")
r = run(outside, payload={"hook_event_name": "SessionStart", "source": "startup", "cwd": outside})
check("outside a git repo: nothing and exit 0", r.returncode == 0 and r.stdout == "", r.stdout + r.stderr)

# An update started by the atualizar skill leaves .superpowers/atualizar.json; the new session is reminded to finish it.
VERSION = json.load(open(os.path.join(HOOKS, "..", ".claude-plugin", "plugin.json"), encoding="utf-8"))["version"]
upd_dir = tempfile.mkdtemp(prefix="sessionstart_upd_")
subprocess.run(["git", "init", "-q"], cwd=upd_dir, check=True)
os.makedirs(os.path.join(upd_dir, ".superpowers"))
UPD = os.path.join(upd_dir, ".superpowers", "atualizar.json")


def write_upd(text):
    with open(UPD, "w", encoding="utf-8") as handle:
        handle.write(text)


def start(cwd, source="startup"):
    return run(cwd, payload={"hook_event_name": "SessionStart", "source": source, "cwd": cwd})


r = start(upd_dir)
check("atualizar: no file prints nothing", r.returncode == 0 and r.stdout == "", r.stdout + r.stderr)
write_upd(json.dumps({"from": "0.0.1", "to": VERSION}))
want = (f"foreman: the plugin was updated from 0.0.1 to {VERSION}; finish the update with the atualizar skill "
        "(kickoff and the upgrade notes).")
for source in ("startup", "resume", "clear", "compact"):
    r = start(upd_dir, source)
    check(f"atualizar: `to` is the running version, on {source}", r.returncode == 0 and r.stdout.strip() == want,
          r.stdout + r.stderr)
sub_upd = os.path.join(upd_dir, "src")
os.makedirs(sub_upd)
r = start(sub_upd)
check("atualizar: from a subfolder too", r.stdout.strip() == want, r.stdout + r.stderr)
write_upd(json.dumps({"from": "0.0.1", "to": "99.0.0"}))
r = start(upd_dir)
check("atualizar: `to` differs from the running version", r.returncode == 0 and r.stdout.strip() == (
    f"foreman: an update to 99.0.0 was started but this session runs {VERSION}; run /reload-plugins or restart, "
    "then the atualizar skill."), r.stdout + r.stderr)
for bad in ("{not json", "[]", json.dumps({"from": "1"}), json.dumps({"to": VERSION}), json.dumps({"from": 1, "to": 2}),
            ""):
    write_upd(bad)
    r = start(upd_dir)
    check(f"atualizar: unusable file {bad!r} says nothing and never fails", r.returncode == 0 and r.stdout == ""
          and r.stderr == "", r.stdout + r.stderr)
write_upd(json.dumps({"from": "0.0.1", "to": VERSION}))
subprocess.run(["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base"],
               cwd=upd_dir, check=True)
subprocess.run([sys.executable, LEDGER, "start", "--slug", "retomada"], cwd=upd_dir, check=True, capture_output=True)
upd_status = subprocess.run([sys.executable, LEDGER, "status"], cwd=upd_dir, capture_output=True, text=True,
                            encoding="utf-8").stdout
r = start(upd_dir, "compact")
check("atualizar: with a ledger, the ledger output comes first and unchanged, then the notice",
      r.stdout == "Delivery ledger (resumed session), `ledger.py status`:\n" + upd_status + want + "\n",
      r.stdout + r.stderr)

# A folder with .superpowers/hub.json is a foreman hub: the hook claims it and prints one hub line, not the status
# (the hub skill runs hub.py status in its first step).
hubdir = tempfile.mkdtemp(prefix="sessionstart_hub_")
REG = os.path.join(hubdir, ".superpowers", "hub.json")
os.makedirs(os.path.dirname(REG))
EMPTY = json.dumps({"abrir": None, "bg": None, "projetos": {}})


def reg(text=EMPTY):
    with open(REG, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def hub(source, sid="s1", cwd=None):
    payload = {"hook_event_name": "SessionStart", "source": source, "cwd": cwd or hubdir}
    if sid:
        payload["session_id"] = sid
    return run(hubdir, payload=payload)


def read_reg():
    with open(REG, encoding="utf-8") as handle:
        return json.load(handle)


reg()
r = hub("startup")
first = r.stdout.splitlines()[0] if r.stdout else ""
check("hub: startup prints the hub line and not the hub status", r.returncode == 0 and "hub" in first
      and "kickoff" in first and "No projects with the plugin" not in r.stdout and r.stderr == "", r.stdout + r.stderr)
check("hub: startup makes the session the owner", read_reg().get("dono") == "s1", str(read_reg()))
r = hub("compact", "s9")
check("hub: compact prints the hub line and keeps the owner", "foreman hub" in r.stdout
      and read_reg()["dono"] == "s1", r.stdout + str(read_reg()))
hub("resume", "s2")
check("hub: resume takes over", read_reg()["dono"] == "s2" and read_reg()["sessoes"] == ["s1", "s2"], str(read_reg()))
for n in range(3, 8):
    hub("startup", f"s{n}")
check("hub: seven sessions keep the last five", read_reg()["sessoes"] == ["s3", "s4", "s5", "s6", "s7"], str(read_reg()))
before = open(REG, "rb").read()
r = hub("startup", sid=None)
check("hub: no session_id leaves the file alone and still prints", r.returncode == 0 and open(REG, "rb").read() == before
      and "foreman hub" in r.stdout, r.stdout + r.stderr)
reg("{broken")
r = hub("startup", "s8")
check("hub: invalid hub.json exits 0, untouched, no traceback", r.returncode == 0 and open(REG, "rb").read() == b"{broken"
      and "Traceback" not in r.stdout + r.stderr, r.stdout + r.stderr)
sub_hub = os.path.join(hubdir, "sub")
os.makedirs(sub_hub)
reg()
r = hub("startup", "s1", cwd=sub_hub)
check("hub: a subfolder is not the hub", r.stdout == "" and "dono" not in read_reg(), r.stdout)


# T4 fix round 1
import time
reg()
open(os.path.join(hubdir, ".superpowers", "hub.lock"), "w").close()
t0 = time.time()
r = hub("startup", "s20")
check("hub: a held lock keeps the hook under its 10 s and prints the hub line", time.time() - t0 < 8
      and r.returncode == 0 and "foreman hub" in r.stdout, f"{time.time() - t0} {r.stdout}{r.stderr}")
check("hub: a failed claim is named after the hub line", r.stdout.splitlines()[1].startswith("busy"), r.stdout)
os.remove(os.path.join(hubdir, ".superpowers", "hub.lock"))
reg()
hub("clear", "s30")
check("hub: clear claims", read_reg().get("dono") == "s30", str(read_reg()))
hub("compact", "s31")
check("hub: compact does not claim", read_reg().get("dono") == "s30", str(read_reg()))
hub("startup", "-x")
check("hub: an id starting with - is the id, not an option", read_reg().get("dono") == "-x", str(read_reg()))
rel = subprocess.run([sys.executable, SCRIPT], cwd=os.path.dirname(hubdir), input=json.dumps(
    {"source": "startup", "cwd": os.path.basename(hubdir), "session_id": "rel1"}), capture_output=True, text=True,
    encoding="utf-8")
check("hub: a relative cwd works", read_reg().get("dono") == "rel1" and "foreman hub" in rel.stdout, rel.stdout + rel.stderr)
reg()
SLOW_CLAIM = f"""
import importlib.util, subprocess
spec = importlib.util.spec_from_file_location("session_start", {SCRIPT!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
real = subprocess.run
def slow(args, **kw):
    if "claim" in args:
        raise subprocess.TimeoutExpired(args, kw.get("timeout"))
    return real(args, **kw)
subprocess.run = slow
module.main()
"""
r = subprocess.run([sys.executable, "-c", SLOW_CLAIM], input=json.dumps({"source": "startup", "cwd": hubdir,
                   "session_id": "slow1"}), capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = r.stdout.splitlines()
check("hub: a claim that times out says so in one line, and nothing follows", len(lines) == 2
      and "claim" in lines[1] and "did not finish" in lines[1], r.stdout + r.stderr)
proj_hub = tempfile.mkdtemp(prefix="sessionstart_projhub_")
os.makedirs(os.path.join(proj_hub, ".superpowers"))
open(os.path.join(proj_hub, ".superpowers", "hub.json"), "w").write(EMPTY)
for cmd in (["init", "-q"], ["-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "b"]):
    subprocess.run(["git"] + cmd, cwd=proj_hub, check=True)
subprocess.run([sys.executable, LEDGER, "start", "--slug", "x"], cwd=proj_hub, check=True, capture_output=True)
r = run(proj_hub, payload={"source": "resume", "cwd": proj_hub, "session_id": "p1"})
check("hub: a ledger wins; hub.json is ignored with one line and the project output follows",
      "ignored" in r.stdout and "kickoff does not run" not in r.stdout and "Delivery ledger" in r.stdout
      and "dono" not in open(os.path.join(proj_hub, ".superpowers", "hub.json")).read(), r.stdout + r.stderr)

config = json.load(open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8"))
groups = config["hooks"]["SessionStart"]
check("hooks.json registers session-start.py for every session start", len(groups) == 1
      and set(groups[0]["matcher"].split("|")) == {"startup", "resume", "clear", "compact"}
      and "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.py" in groups[0]["hooks"][0]["command"]
      and groups[0]["hooks"][0]["type"] == "command", json.dumps(config))

print("ALL PASS" if all(results) else "SOME FAILED", f"({sum(results)}/{len(results)})")
sys.exit(0 if all(results) else 1)
