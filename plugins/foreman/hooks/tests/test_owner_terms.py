import json, os, re, subprocess, sys, tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pre-commit-secret-scan.py")
os.environ["CLAUDE_FOREMAN_HOME"] = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
base = tempfile.mkdtemp(prefix="terms_")
repo = os.path.join(base, "acme-app")
os.makedirs(repo)
GLOBAL = os.path.join(base, "global.gitconfig")
TERMS = os.path.join(base, "terms.txt")
os.environ["GIT_CONFIG_GLOBAL"] = GLOBAL
open(GLOBAL, "w").close()
results = []
# the owner terms and home paths are split so this file's own lines do not trip the scanner
NAME = "Zeb" "ulon"
MAIL = "zeb" "@corp-x.example"
HOME_WIN = "C:" + "\\Users\\" + "zeb" "ulon\\proj"
HOME_UNIX = "/ho" "me/" + "zeb" "ulon/proj"


def sh(*a, check=True, env=None):
    return subprocess.run(list(a), cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          check=check, env=env)


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("PASS" if ok else "FAIL", name, "" if ok else f"| {detail[-400:]}")


def write(name, text):
    with open(os.path.join(repo, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def staged(name, text):
    write(name, text)
    sh("git", "add", name)
    r = sh(sys.executable, HOOK, "--pre-commit", check=False)
    return r.returncode, r.stderr


def reset():
    sh("git", "reset", "-q", "--hard")


sh("git", "init", "-q", "-b", "main")
for k, v in (("user.email", "t@t.com"), ("user.name", "t"), ("core.autocrlf", "false")):
    sh("git", "config", k, v)
write("a.txt", "base\n")
sh("git", "add", "-A")
sh("git", "commit", "-q", "-m", "base")

code, err = staged("notes.md", f"see {HOME_WIN} for the file\n")
check("without a terms list, a Windows home path in an added line blocks", code == 1 and "home path" in err, err)
check("the message names file and line and never the path itself",
      "notes.md:1" in err and "zeb" not in err.lower() and re.search(r"fingerprint [0-9a-f]{64}", err), err)
reset()
code, err = staged("notes.md", f"cd {HOME_UNIX}\n")
check("a /home/<name>/ path blocks", code == 1 and "notes.md:1" in err, err)
reset()
code, err = staged("notes.md", "C:" + "\\Users\\<user>\\x, " + "/ho" "me/runner/work/, " + "/Us" "ers/you/x, "
                   "%USERPROFILE%, C:" + "/Users/$USER/x, https://example.com/home/about/x\n")
check("placeholders, the CI runner and a URL path are no home path", code == 0, err)
check("without a terms list the scanner prints nothing extra", err == "", err)
reset()

with open(TERMS, "w", encoding="utf-8") as handle:
    handle.write(f"# the owner's terms\n{NAME}\n{MAIL}\nacme-app\nautor t@t.com\n")
sh("git", "config", "--global", "foreman.terms", TERMS.replace("\\", "/"))
code, err = staged("doc.md", "intro\n\nWritten by " + NAME.lower() + " for the team.\n")
check("an owner term blocks, case-insensitive, naming file and line", code == 1 and "doc.md:3" in err, err)
check("the block message never prints the term", NAME.lower() not in err.lower(), err)
mark = re.search(r"doc\.md:3 \(fingerprint ([0-9a-f]{64})\)", err)
reset()
code, err = staged("doc.md", f"{NAME}s and x{MAIL} are other words\n")
check("a term matches only as a whole word", code == 0, err)
reset()
code, err = staged("doc.md", "the acme-app project\n")
check("a term equal to the repository's own folder name is ignored", code == 0, err)
reset()
with open(TERMS, "a", encoding="utf-8") as handle:
    handle.write("acme-web\n")
code, err = staged("doc.md", "the app reads the acme-web API\n")
check("a sibling project still blocks without a Depende de line in CLAUDE.md", code == 1 and "doc.md:1" in err, err)
reset()
write("CLAUDE.md", "# acme-app\n\nThe app reads acme-web.\n\n- Depende de (each external system): _(acme-web)_\n")
code, err = staged("doc.md", "the app reads the acme-web API\n")
check("a term elsewhere in CLAUDE.md, or in a placeholder of the Depende de line, still blocks",
      code == 1 and "doc.md:1" in err, err)
reset()
write("CLAUDE.md", "# acme-app\n\n- Depende de (each external system): the ACME-WEB API, tag v2\n")
code, err = staged("doc.md", "the app reads the acme-web API\n")
check("a term the CLAUDE.md Depende de line declares is ignored in that repository, in any case", code == 0, err)
reset()
os.remove(os.path.join(repo, "CLAUDE.md"))
with open(TERMS, "a", encoding="utf-8") as handle:
    handle.write("familia acme-web acme-app\n")
code, err = staged("doc.md", "the app reads the acme-web API\n")
check("a familia line frees nothing: without the Depende de line the sibling still blocks",
      code == 1 and "doc.md:1" in err, err)
check("a familia line warns once to declare the dependency in CLAUDE.md",
      err.count("familia") == 1 and "Depende de" in err, err)
reset()
code, err = staged("doc.md", "the familia line is no term: familia\n")
check("a familia line is no term itself", code == 0, err)
reset()
code, err = staged("doc.md", "intro\n\nWritten by " + NAME.lower() + " for the team.\n")
write(".foreman-secrets-allow", f"{mark.group(1) if mark else '-'}  # the owner's own credit line\n")
sh("git", "add", "-A")
r = sh(sys.executable, HOOK, "--pre-commit", check=False)
check("the line is freed by its fingerprint in the staged allowlist, as a secret is", r.returncode == 0, r.stderr)
reset()

write("x.txt", "x\n")
sh("git", "add", "x.txt")
env = dict(os.environ, GIT_AUTHOR_EMAIL="other@x.example")
r = subprocess.run([sys.executable, HOOK, "--pre-commit"], cwd=repo, capture_output=True, text=True, env=env)
check("pre-commit refuses an author e-mail outside the autor lines, without printing it",
      r.returncode == 1 and "autor" in r.stderr and "other@x" not in r.stderr, r.stderr)
r = sh(sys.executable, HOOK, "--pre-commit", check=False)
check("an author e-mail of the autor lines commits", r.returncode == 0, r.stderr)
reset()

sh("git", "switch", "-q", "-c", "feat/x")
write("y.txt", "y\n")
sh("git", "add", "y.txt")
sh("git", "-c", "user.email=other@x.example", "commit", "-q", "--no-verify", "-m", f"feat: y for {NAME}")
r = sh(sys.executable, HOOK, "--range", "main..HEAD", check=False)
check("--range flags an author or committer outside the autor lines", r.returncode == 1 and "author" in r.stdout,
      r.stdout + r.stderr)
check("--range flags a term in a commit message, without printing it",
      "message" in r.stdout and NAME.lower() not in r.stdout.lower(), r.stdout)
write("doc2.md", "the app reads the acme-web API\n")
sh("git", "add", "doc2.md")
sh("git", "commit", "-q", "--no-verify", "-m", "docs: api")
r = sh(sys.executable, HOOK, "--range", "main..HEAD", check=False)
check("--range blocks an undeclared term in a file of the range", "doc2.md:1" in r.stdout, r.stdout)
write("CLAUDE.md", "# acme-app\n\n- Depende de: acme-web, tag v2\n")
sh("git", "add", "CLAUDE.md")
sh("git", "commit", "-q", "--no-verify", "-m", "docs: declare the dependency")
r = sh(sys.executable, HOOK, "--range", "main..HEAD", check=False)
check("--range reads the Depende de line of CLAUDE.md at HEAD", "doc2.md" not in r.stdout
      and "CLAUDE.md" not in r.stdout, r.stdout)
with open(TERMS, "w", encoding="utf-8") as handle:
    handle.write(f"{NAME}\n")
r = sh(sys.executable, HOOK, "--range", "main..HEAD", check=False)
check("with no autor line, any author passes and the message term still counts",
      "author" not in r.stdout and "message" in r.stdout, r.stdout)


# bash-guard: the text a gh command publishes (title, body, comment, notes) is held to the same terms list
GUARD = os.path.join(os.path.dirname(HOOK), "bash-guard.py")
with open(TERMS, "w", encoding="utf-8") as handle:
    handle.write(NAME + chr(10))


def published(command):
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": repo, "tool_input": {"command": command}}
    done = subprocess.run([sys.executable, GUARD], cwd=repo, input=json.dumps(payload), capture_output=True,
                          text=True, encoding="utf-8")
    out = json.loads(done.stdout)["hookSpecificOutput"] if done.stdout.strip() else {}
    return out.get("permissionDecision"), out.get("permissionDecisionReason") or ""


decision, why = published(f'gh pr create --title "x" --body "measured in {NAME.lower()} last night"')
check("gh pr create with an owner term in --body is denied, without printing the term",
      decision == "deny" and NAME.lower() not in why.lower() and "publish" in why, why)
decision, _ = published(f"gh pr comment 3 -b 'see {NAME}'")
check("gh pr comment -b with a term is denied", decision == "deny")
decision, _ = published(f"gh issue create -t 'bug from {NAME}' -b ok")
check("gh issue create with a term in the title is denied", decision == "deny")
decision, _ = published(f"gh api -X PATCH repos/o/r/issues/comments/1 -f body='{NAME} numbers'")
check("gh api with a term in a body field is denied", decision == "deny")
write("pr.md", f"Numbers from {NAME}." + chr(10))
decision, _ = published("gh pr create --title x --body-file pr.md")
check("a term inside the --body-file is denied", decision == "deny")
decision, _ = published(chr(10).join(["cat > new.md <<'X'", f"by {NAME}", "X",
                                      "gh pr create --title x --body-file new.md"]))
check("a body file written in the same command is read from the command", decision == "deny")
decision, _ = published("gh pr comment 3 --body 'see " + "C:" + chr(92) + "Users" + chr(92) + "zeb" "ulon" + chr(92)
                        + "x'")
check("a home path in a published body is denied", decision == "deny")
decision, _ = published("gh pr create --title 'qa enxuto' --body 'um projeto do autor: 1 h 40 min'")
check("a clean body publishes", decision is None)
decision, _ = published(f"gh pr view 3 -R {NAME.lower()}/repo")
check("a term outside the published text (a read, the repo flag) passes", decision is None)
decision, _ = published(f"echo {NAME}")
check("a command that publishes nothing is not this check's", decision is None)

print("ALL PASS" if all(results) else "SOME FAILED", f"({sum(results)}/{len(results)})")
sys.exit(0 if all(results) else 1)
