#!/usr/bin/env python3
"""SessionStart hook (every session start, see hooks.json): hands the manager its place back, and keeps the native
secret-scan hook pointed at the running plugin, and reminds a new session to finish a plugin update.

After a compaction or a resumed session the manager has lost the thread of the delivery. When the project has
.superpowers/ledger.jsonl, this prints `ledger.py status` (plain stdout from SessionStart goes into Claude's
context); a new or cleared session prints nothing.

The native pre-commit hook finds the scanner through `git config foreman.home`, and an installed plugin lives in a
folder per version: in a repository whose pre-commit hook is the plugin's, each session start sets the repository's
foreman.home to the running plugin's folder when it names another one, so no clone of the plugin is needed and an
update never leaves every commit blocked.

The atualizar skill leaves .superpowers/atualizar.json, {"from", "to"}, at the project root (the current worktree
root, or the main worktree's). When it exists, every event adds one line after the rest of the output: the running
version (plugin.json) equal to `to` says to finish the update with the atualizar skill; a different one says to run
/reload-plugins or restart first. A missing or unusable file (not JSON, missing or non-string field) adds nothing.
A folder with .superpowers/hub.json (the payload's cwd itself) is a foreman hub, not a project, unless it also has
.superpowers/ledger.jsonl: then the project wins, one line says that hub.json is ignored and the output is the normal one.
In a hub the hook prints at once one line saying that the folder is a hub and that kickoff does not run in it. On
startup, resume and clear (not compact) with a session_id it runs `hub.py claim` (this plugin's own; 3 s, lock wait 1.5 s),
which makes the session the owner of the hub, and prints claim's first error line if it fails. Then it prints
`hub.py status` (5 s; on a timeout, one line saying so), all well inside the 10 s the hook has. A broken hub.json, a
missing session_id, a failing or slow hub.py leave the file untouched and print at most those lines.
Without a ledger or a git repository it does nothing; any failure exits 0,
so a session never breaks."""
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LEDGER = os.path.join(ROOT, "skills", "manager", "ledger.py")
HUB = os.path.join(ROOT, "skills", "hub", "hub.py")
MARKER = "secretscan-managed"


def git(project, *args):
    done = subprocess.run(["git", *args], cwd=project, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    return done.stdout.strip() if done.returncode == 0 else ""


def point_home(project):
    hook = git(project, "rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-commit")
    try:
        with open(hook, encoding="utf-8", errors="replace") as handle:
            if MARKER not in handle.read():
                return
    except OSError:
        return
    root = ROOT.replace("\\", "/")
    current = git(project, "config", "--get", "foreman.home").replace("\\", "/").rstrip("/")
    if os.path.normcase(current) != os.path.normcase(root):
        git(project, "config", "--local", "foreman.home", root)


def update_notice(project):
    """The line about a started plugin update, or "" with no usable atualizar.json."""
    roots = [project, git(project, "rev-parse", "--show-toplevel")]
    common = git(project, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common:
        roots.append(os.path.dirname(common))
    for root in filter(None, roots):
        path = os.path.join(root, ".superpowers", "atualizar.json")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
        old, new = data["from"], data["to"]
        if not isinstance(old, str) or not isinstance(new, str) or not old or not new:
            return ""
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
            running = json.load(handle)["version"]
        if running == new:
            return (f"foreman: the plugin was updated from {old} to {new}; finish the update with the atualizar "
                    "skill (kickoff and the upgrade notes).")
        return (f"foreman: an update to {new} was started but this session runs {running}; run /reload-plugins "
                "or restart, then the atualizar skill.")
    return ""


def notice(project):
    try:
        text = update_notice(project)
    except Exception:
        return
    if text:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        payload = {}
    payload = payload if isinstance(payload, dict) else {}
    project = payload.get("cwd") or os.getcwd()
    point_home(project)
    try:
        hub_status(payload, project)
        ledger_status(payload, project)
    finally:
        notice(project)


def hub_status(payload, project):
    project = os.path.abspath(project)
    if not os.path.isfile(os.path.join(project, ".superpowers", "hub.json")):
        return
    sys.stdout.reconfigure(encoding="utf-8")
    if os.path.isfile(os.path.join(project, ".superpowers", "ledger.jsonl")):  # a project with a ledger is no hub
        print("foreman: .superpowers/hub.json here is ignored, this folder is a project (it has a ledger).", flush=True)
        return
    print("This folder is a foreman hub (.superpowers/hub.json), not a project: kickoff does not run in it.", flush=True)

    def hub(*args, timeout):
        return subprocess.run([sys.executable, HUB, *args, "--raiz", project], cwd=project, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout)

    sid = payload.get("session_id")
    try:
        if payload.get("source") in ("startup", "resume", "clear") and isinstance(sid, str) and sid:
            done = hub("claim", f"--sessao={sid}", "--espera", "1.5", timeout=3)
            if done.returncode != 0 and done.stderr.strip():
                print(done.stderr.splitlines()[0][:300], flush=True)
    except Exception:  # claim is best effort: the session just is not the owner
        pass
    try:
        done = hub("status", timeout=5)
        text = done.stdout if done.returncode == 0 else " ".join(done.stderr.splitlines()[:1])[:300]
    except subprocess.TimeoutExpired:
        text = "The hub status did not answer in time; run `hub.py status` in this folder."
    except Exception:
        text = ""
    if text.strip():
        print(text, end="" if text.endswith(chr(10)) else chr(10))


def ledger_status(payload, project):
    if payload.get("source") in ("startup", "clear"):
        return
    if not os.path.isfile(os.path.join(project, ".superpowers", "ledger.jsonl")):
        return
    done = subprocess.run([sys.executable, LEDGER, "status"], cwd=project, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode == 0 and done.stdout.strip():
        sys.stdout.reconfigure(encoding="utf-8")
        print("Delivery ledger (resumed session), `ledger.py status`:\n" + done.stdout, end="")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
