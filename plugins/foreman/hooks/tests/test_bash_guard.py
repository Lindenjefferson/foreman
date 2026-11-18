import datetime, json, os, subprocess, sys, tempfile, time

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCRIPT = os.path.join(HOOKS, "bash-guard.py")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("PASS" if ok else "FAIL", name, "" if ok else f"| {detail[-300:]}")


def project(commands):
    folder = tempfile.mkdtemp(prefix="devserver_")
    with open(os.path.join(folder, "CLAUDE.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Projeto\n\n## Comandos\n\n" + commands + "\n## Outra seção\n\n- Rodar em desenvolvimento: `ignored run`\n")
    return folder


def run(folder, command, background=False, tool="Bash", cwd=None, mode=None, session=None):
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": cwd or folder,
               "tool_input": {"command": command, "run_in_background": background}}
    if mode:
        payload["permission_mode"] = mode
    if session:
        payload["session_id"] = session
    done = subprocess.run([sys.executable, SCRIPT], cwd=tempfile.gettempdir(), input=json.dumps(payload),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    reason = None
    if done.stdout.strip():
        out = json.loads(done.stdout)["hookSpecificOutput"]
        assert out["hookEventName"] == "PreToolUse"
        reason = (out["permissionDecision"], out["permissionDecisionReason"])
    return done.returncode, reason, done.stderr


configured = project("- Rodar em desenvolvimento: `npm run dev`\n- Testes: `npm test`\n")

code, reason, err = run(configured, "npm run dev")
check("the configured dev server in the foreground is denied", code == 0 and reason and reason[0] == "deny", err)
check("the message shows the right form", reason and "run_in_background" in reason[1] and "npm run dev" in reason[1],
      str(reason))
check("the same command in background passes", run(configured, "npm run dev", background=True) == (0, None, ""))
check("extra arguments are still the dev server", run(configured, "npm  run dev -- --port 3001")[1] is not None)
check("after cd and &&", run(configured, "cd app && npm run dev")[1] is not None)
check("after an env assignment", run(configured, "PORT=3001 npm run dev")[1] is not None)
check("piped", run(configured, "npm run dev | tee log.txt")[1] is not None)
check("shell backgrounding with & is still denied (orphan process)", run(configured, "npm run dev &")[1] is not None)
check("another command passes", run(configured, "npm test")[1] is None)
check("a longer script name is not the dev server", run(configured, "npm run dev:docs")[1] is None)
check("the command quoted in other text passes", run(configured, "grep 'npm run dev' README.md")[1] is None)
check("not a Bash call passes", run(configured, "npm run dev", tool="Read")[1] is None)
check("a heredoc body that only mentions the command passes",
      run(configured, "cat > README.md <<'EOF'\n## Como rodar\nnpm run dev\nEOF\ngit add README.md")[1] is None)
check("a quoted message that mentions the command passes",
      run(configured, 'git commit -m "docs: explain the dev server (npm run dev)"')[1] is None)
check("after a quoted argument, the command itself is still denied",
      run(configured, 'echo "starting; really" && npm run dev')[1] is not None)
check("a heredoc fed to a shell is still denied", run(configured, "bash <<'EOF'\nnpm run dev\nEOF")[1] is not None)
start = time.monotonic()
run(configured, "echo " + "x" * 80000)
check("a long one-line command is read quickly (well under the hook's 10s timeout)", time.monotonic() - start < 3)
check("a here-string is not a heredoc: the next line is still read",
      run(configured, 'cat <<< "x"\nnpm run dev')[1] is not None)
sub = os.path.join(configured, "app")
os.makedirs(sub)
check("cwd in a subfolder still finds the project's CLAUDE.md", run(configured, "npm run dev", cwd=sub)[1] is not None)

placeholder = project("- Rodar em desenvolvimento: _(comando)_\n")
check("a placeholder line does nothing", run(placeholder, "npm run dev") == (0, None, ""))
check("a command declared outside the Comandos section does nothing",
      run(placeholder, "ignored run") == (0, None, ""))
nolines = project("- Testes: `npm test`\n")
check("without the line the hook does nothing", run(nolines, "npm run dev") == (0, None, ""))
bare = tempfile.mkdtemp(prefix="devserver_")
check("without a CLAUDE.md the hook does nothing", run(bare, "npm run dev") == (0, None, ""))

# a project command run inside timeout is killed at the limit, the suite half run (a qa lost its interface run so)
suites = project("- Testes: `npm test`\n- Verificação de interface: `npm run e2e:android`\n")
denied = run(suites, "timeout 590 npm run e2e:android")[1]
check("a Comandos line inside timeout is denied, naming background mode and a log of its own",
      denied and denied[0] == "deny" and "run_in_background" in denied[1] and "log" in denied[1], str(denied))
check("timeout with its options, after cd and in background is still denied",
      run(suites, "cd app && timeout -k 5 --signal=KILL 10m npm test -- --runInBand", background=True)[1] is not None)
check("timeout around another command passes", run(suites, "timeout 5 curl -s localhost:3000")[1] is None)
check("the Comandos line alone passes", run(suites, "npm run e2e:android > e2e.log 2>&1", background=True)[1] is None)
check("timeout and the command only quoted in a message pass",
      run(suites, 'git commit -m "qa: no timeout npm test"')[1] is None)
check("without a CLAUDE.md, timeout passes", run(bare, "timeout 590 npm test")[1] is None)

garbage = subprocess.run([sys.executable, SCRIPT], input="not json", capture_output=True, text=True)
check("garbage on stdin never blocks", garbage.returncode == 0 and garbage.stdout == "", garbage.stderr)

def skips(command, background=False, folder=None):
    reason = run(folder or bare, command, background=background)[1]
    return reason is not None and reason[0] == "deny" and "pre-commit" in reason[1]


for command in ('git commit --no-verify -m "x"', 'git commit -m "x" --no-verify', 'git commit -nm "x"',
                "git commit -am wip -n", "git commit -an -m ''", "git commit --no-veri -m x",
                'git commit "--no-verify" -m x', "cd sub && git commit -n -m x", "git -C repo commit -n -m x",
                "git -c core.hooksPath=/dev/null commit -m x", "git -c CORE.HOOKSPATH=x commit -m x",
                "git --config-env=core.hooksPath=EMPTY commit -m x", "GIT_CONFIG_KEY_0=core.hooksPath git commit -m x",
                "git config core.hooksPath /tmp/none", "git config set --local core.hooksPath x",
                "echo ok; git commit -n -m x", "echo $(git commit -n -m x)", "bash -c 'git commit -n -m x'",
                "/usr/bin/git commit -n -m x", "git.exe commit --no-verify -m x",
                "git commit -n -m \"$(cat <<'EOF'\nmsg\nEOF\n)\"", "echo a#b; git commit -n -m x",
                'git commit -m "#12 fix" -n', "git commit -m x 2>&1 -n", "git commit -m x &>log -n",
                "env git commit -n -m x", "env -i PATH=/bin nohup git commit -n -m x",
                "env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/x git commit -m x",
                "export GIT_CONFIG_KEY_0=core.hooksPath; git commit -m x", "time git commit -n -m x",
                "command git commit -n -m x", "if true; then git commit -n -m x; fi", "{ git commit -n -m x; }",
                "! git commit -n -m x", "bash -lc 'git commit -n -m x'", "sh -ec 'git commit -n -m x'",
                "bash -o pipefail -c 'git commit -n -m x'", "bash -O extglob -c 'git commit -n -m x'",
                "bash --rcfile f -c 'git commit -n -m x'", "bash --init-file f -c 'git commit -n -m x'",
                "bash -euo pipefail -c 'git commit -n -m x'", "bash +o history -c 'git commit -n -m x'",
                "git config --unset core.hooksPath", "git commit -n -m x # don't",
                "git commit --no-verify -F - <<'MSG-END'\nit's done\nMSG-END"):
    check(f"skipping the pre-commit hook is denied: {command!r}", skips(command))
check("skipping the hook is denied in background too", skips("git commit -n -m x", background=True))
check("skipping the hook is denied where the dev server is configured", skips("git commit -n -m x", folder=configured))
for command in ('git commit -m "docs: never use --no-verify"', 'git commit -m "fix: grep -n finds it"',
                "git commit -m \"$(cat <<'EOF'\nfix: explain --no-verify and git commit -n\nEOF\n)\"",
                "git commit -F - <<'EOF'\nchore: -n --no-verify\nEOF", "git commit -uno -m x",
                "git commit --no-verbose -m x", "git commit --amend --no-edit", "git commit -m x -- -n",
                "git log -n 3", "echo git commit -n", "git config --get core.hooksPath", "git config core.hooksPath",
                "grep -n x file && git commit -m y", 'git commit --message "-n items"',
                "git commit --author 'A <a@x>' --date -n -m x", "cat > notes.md <<'MD-EOF'\ngit commit -n -m x\nMD-EOF",
                "cat > notes.md <<\\EOF\ngit commit -n -m x\nEOF", "env | grep GIT",
                'git commit -m "unbalanced'):
    check(f"a commit that keeps the hook passes: {command!r}", run(bare, command)[1] is None, str(run(bare, command)))

LEDGER_PY = os.path.join(HOOKS, "..", "skills", "manager", "ledger.py")
repo = tempfile.mkdtemp(prefix="guard_")


def sh(*args):
    subprocess.run(args, cwd=repo, check=True, capture_output=True)


for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@t.com"), ("config", "user.name", "t"),
             ("commit", "-q", "--allow-empty", "-m", "base")):
    sh("git", *args)
sh(sys.executable, LEDGER_PY, "start", "--slug", "x")


def reaches_main(command):
    reason = run(repo, command)[1]
    return reason is not None and reason[0] == "deny" and "autonomous" in reason[1]


main_pushes = ("git push origin main", "git push origin HEAD:main", "git push origin feat/x:main",
               "git push -u origin +main", "git push --all", "git push --mirror origin",
               "git push origin refs/heads/main", "gh pr merge 20 --merge", "cd . && git push origin main",
               "git push origin --delete main", "git -C . push origin main")


def asks(command, cwd=None):
    reason = run(cwd or repo, command)[1]
    return reason is not None and reason[0] == "ask" and "main" in reason[1]


for command in ("git push origin main", "git push", "git push origin HEAD:main", "git push --all",
                "git switch -q main && git push"):
    check(f"supervised: a push to the main branch asks the user {command!r}", asks(command), str(run(repo, command)))
pr_merges = ("gh pr merge 12", "gh pr merge --squash 12", "glab mr merge 3", "glab mr accept 3",
             "gh api repos/o/r/pulls/12/merge -X PUT")
for command in ("git merge feat/x", "git merge --no-ff feat/x", "git switch -q feat/y && git checkout main && "
                "git merge feat/x") + pr_merges:
    check(f"supervised: a merge into the main branch asks the user {command!r}", asks(command),
          str(run(repo, command)))
check("supervised: the merge ask names approval 2", "approval 2" in (run(repo, "git merge feat/x")[1] or ("", ""))[1])
check("supervised: in PowerShell too", (run(repo, "gh pr merge 12", tool="PowerShell")[1] or ("",))[0] == "ask")
check("supervised: in the background too", (run(repo, "git merge feat/x", background=True)[1] or ("",))[0] == "ask")
for command in ("git push origin feat/x", "git push -u origin feat/x:feat/x", "git push --tags", "gh pr view 12",
                "gh pr create --fill", "git merge --abort", "git merge --quit", "git switch -q feat/y && git merge feat/x"):
    check(f"supervised: passes {command!r}", run(repo, command)[1] is None, str(run(repo, command)))
loose = tempfile.mkdtemp(prefix="noledger_")
for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@t.com"), ("config", "user.name", "t"),
             ("commit", "-q", "--allow-empty", "-m", "base")):
    subprocess.run(["git", *args], cwd=loose, check=True, capture_output=True)
check("with no ledger, a push to the main branch asks too", asks("git push origin main", loose))
for command in ("git merge feat/x",) + pr_merges:
    check(f"with no ledger, a merge into the main branch asks too {command!r}", asks(command, loose))
check("with no ledger, a push of a work branch passes", run(loose, "git push origin feat/y")[1] is None)
with open(os.path.join(loose, "CLAUDE.md"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write("# P\n\n## Comandos\n\n- Rodar em desenvolvimento: `npm run dev`\n- Testes: `npm test`\n")
for command in ("git merge feat/x && timeout 10 npm test", "git merge feat/x && npm run dev",
                "git push origin main && npm run dev"):
    check(f"a denial wins over the main-branch ask {command!r}", (run(loose, command)[1] or ("",))[0] == "deny",
          str(run(loose, command)))
check("in the background, the main-branch ask still comes",
      (run(loose, "git merge feat/x && npm run dev", background=True)[1] or ("",))[0] == "ask")
os.remove(os.path.join(loose, "CLAUDE.md"))


def relative_cd(command, tool="Bash"):
    reason = run(repo, command, tool=tool)[1]
    return reason is not None and reason[0] == "deny" and "git -C" in reason[1]


for command in ("cd ../../proj; git merge --ff-only feat/t1", "cd ../proj && git worktree remove ../proj-t1",
                "cd sub; git commit -m x", "cd .. && git cherry-pick abc", "cd ../proj; git branch -d task-1",
                "pushd ../proj && git merge task-1", "cd - ; git branch -D task-1", "cd ../proj; git branch -fd t",
                "cd ../proj && git pull", "cd /c/p && cd ../q && git commit -m x"):
    check(f"a delivery: a relative cd before integrating, committing or removing a copy is denied {command!r}",
          relative_cd(command), str(run(repo, command)))
check("a delivery: in PowerShell too", relative_cd(r"Set-Location ..\proj; git merge task-1", "PowerShell"))
for command in ("cd /c/p/proj && git merge feat/x", "cd C:/p/proj; git commit -m x", r"cd C:\p\proj; git commit -m x",
                "cd ~/proj && git merge x", "git -C /c/p/proj merge task-1", "cd sub && git status",
                "git merge task-1; cd ..", 'git commit -m "cd .. first"', "cd $HOME && git commit -m x",
                'cd "$ROOT" && git merge x', "(cd sub && make); git commit -m x", "x=$(cd sub && pwd); git commit",
                "cd sub && cd /c/p && git commit -m x", "cd sub && git -C /c/p commit -m x"):
    # on the main branch here, a merge asks for approval 2: what this checks is that the cd is not denied
    check(f"a delivery: passes {command!r}", (run(repo, command)[1] or ("ask",))[0] == "ask", str(run(repo, command)))
check("with no ledger, a relative cd before a commit passes", run(loose, "cd .. && git commit -m x")[1] is None)


def discards(command, folder=None, tool="Bash"):
    reason = run(folder or repo, command, tool=tool)[1]
    return reason is not None and reason[0] == "deny" and "not committed" in reason[1]


for name in ("dirty.txt", "clean.txt"):
    with open(os.path.join(repo, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("one\n")
sh("git", "add", "dirty.txt", "clean.txt")
sh("git", "commit", "-q", "-m", "two files")
with open(os.path.join(repo, "dirty.txt"), "a", encoding="utf-8", newline="\n") as handle:
    handle.write("work in progress\n")
slashed = repo.replace(os.sep, "/")
for command in ("git checkout -- dirty.txt", "git checkout HEAD -- dirty.txt", "git checkout HEAD dirty.txt",
                "git checkout .", "git restore dirty.txt", "git restore --worktree dirty.txt", "git restore .",
                "git restore --source=HEAD dirty.txt", "git restore -s HEAD dirty.txt",
                "git restore --staged --worktree dirty.txt", f"git -C {slashed} checkout -- dirty.txt",
                f"cd {slashed} && git restore dirty.txt", "git stash list; git checkout -- clean.txt dirty.txt"):
    check(f"a delivery: undoing a file with work not committed is denied {command!r}", discards(command),
          str(run(repo, command)))
check("a delivery: in PowerShell too", discards("git checkout -- dirty.txt", tool="PowerShell"))
for command in ("git checkout -- clean.txt", "git restore clean.txt", "git restore --staged dirty.txt",
                "git checkout --theirs -- dirty.txt", "git checkout -p -- dirty.txt", "git checkout -b other",
                "git status", 'git commit -m "git checkout -- dirty.txt"'):
    check(f"a delivery: passes {command!r}", run(repo, command)[1] is None, str(run(repo, command)))
check("with no ledger, undoing a file with work not committed passes", run(loose, "git checkout -- x.txt")[1] is None)
sh("git", "checkout", "--", "dirty.txt")
sh(sys.executable, LEDGER_PY, "mode", "autonomous", "--until", (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).isoformat(timespec="seconds"))
for command in main_pushes + ("git push", "git merge feat/x", "git merge --no-ff feat/x"):
    check(f"autonomous, on the main branch: denied {command!r}", reaches_main(command))
check("autonomous, on the main branch: denied 'git push origin @'", reaches_main("git push origin @"))
with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as handle:
    handle.write("x\n")
for command in ("git checkout README.md && git push origin", "git checkout . && git push origin",
                "git checkout -- README.md && git push", "git checkout main -- README.md && git push origin",
                "git checkout HEAD README.md; git push"):
    check(f"autonomous, on the main branch: a checkout of a path is no branch change, denied {command!r}",
          reaches_main(command))
for command in ("git merge --abort", "git status", "git log -n 3", 'git commit -m "push to main later"',
                "git push --tags", "git push origin --tags"):
    check(f"autonomous, on the main branch: passes {command!r}", run(repo, command)[1] is None, str(run(repo, command)))
sh("git", "checkout", "-q", "-b", "feat/x")
for command in main_pushes:
    check(f"autonomous, on a work branch: denied {command!r}", reaches_main(command))
for command in ("git checkout main && git merge feat/x", "git switch main && git merge feat/x && git push",
                "git switch -q main; git push", "gh -R o/r pr merge 3", "gh api -X PUT repos/o/r/pulls/3/merge",
                "glab mr merge 3", "glab mr accept 3", "glab -R o/r mr merge 3", "glab api -X PUT projects/1/merge_requests/3/merge"):
    check(f"autonomous, on a work branch: denied {command!r}", reaches_main(command))
check("autonomous, on a work branch: a checkout of a file from main is no branch change, passes",
      run(repo, "git checkout main -- README.md && git push origin")[1] is None)
for command in ("git push", "git push -u origin feat/x", "git push origin HEAD", "git merge main",
                "git merge --no-ff task-1", "gh pr view 20", "git switch main && git switch feat/x && git push",
                "git switch -c main2 && git push", "gh api repos/o/r/pulls/3", "glab mr view 3",
                "glab api projects/1/merge_requests/3"):
    check(f"autonomous, on a work branch: passes {command!r}", run(repo, command)[1] is None, str(run(repo, command)))
sub = os.path.join(repo, "src")
os.makedirs(sub)
check("autonomous: the ledger is found from a subfolder", run(repo, "git push origin main", cwd=sub)[1] is not None)
check("outside a git repository, a push asks nothing (no main branch to read)",
      run(bare, "git push origin main")[1] is None)

def ps(folder, command, background=False):
    return run(folder, command, background=background, tool="PowerShell")[1]


check("PowerShell: the dev server in the foreground is denied", ps(configured, "npm run dev") is not None)
check("PowerShell: the same command in background passes", ps(configured, "npm run dev", background=True) is None)
for command in ("cd app; npm run dev", "& npm run dev", "npm run dev | Tee-Object log.txt",
                "$env:PORT = 3001; npm run dev", "npm run dev -- --port 3001", "npm run dev\nnpm test",
                "powershell -Command 'npm run dev'", "Invoke-Expression 'npm run dev'"):
    check(f"PowerShell: the dev server is denied: {command!r}", ps(configured, command) is not None)
for command in ("npm test", "npm run dev:docs", "Write-Output 'npm run dev'", 'Write-Output "npm run dev"',
                "git commit -m @'\nnpm run dev no texto\n'@"):
    check(f"PowerShell: not a run of the dev server, passes: {command!r}", ps(configured, command) is None)


def ps_skips(command):
    reason = run(bare, command, tool="PowerShell")[1]
    return reason is not None and reason[0] == "deny" and "pre-commit" in reason[1]


for command in ('git commit --no-verify -m "x"', "git commit -nm 'x'", "Write-Output ok; git commit -n -m x",
                "git config core.hooksPath C:/none", "$env:GIT_CONFIG_KEY_0 = 'core.hooksPath'; git commit -m x",
                "$env:GIT_CONFIG_KEY_0='core.hooksPath'; git commit -m x", "powershell -Command 'git commit -n -m x'",
                "iex 'git commit -n -m x'", "& git commit --no-verify -m x", "git commit --% --no-verify -m x",
                "git -C $env:TEMP commit -n -m x",
                "git -c core.hooksPath=C:/none commit -m x"):
    check(f"PowerShell: skipping the pre-commit hook is denied: {command!r}", ps_skips(command), command)
for command in ('git commit -m "docs: never use --no-verify"', "git commit -m 'fix: -n nao entra'",
                "git commit -m @'\nfix: explica --no-verify e git commit -n\n'@",
                'git commit -m @"\nfix: --no-verify no here-string\n"@', "git commit -m 'it''s -n'",
                'git commit -m "fix: `"-n`" no texto"', "git log -n 3", "Write-Output 'git commit -n'",
                "git commit -m x # -n", "Write-Output ok" + chr(10) + "# git commit -n -m x", "git commit -m 'x#y'",
                "git commit --no-verbose -m x", "git config --get core.hooksPath", "git commit -m 'unbalanced"):
    check(f"PowerShell: a commit that keeps the hook passes: {command!r}",
          run(bare, command, tool="PowerShell")[1] is None, command)
# Expressao e bloco: o que o PowerShell trata como argumento ou bloco nao e um comando novo sem o git
for command in ("$out = git commit -n -m x", "$null = git commit -n -m x 2>&1", "$out=git commit -n -m x",
                "if ($true) {git commit -n -m x}", "try {git commit -n -m x} catch {}",
                "1 | % { git commit -n -m x }", "Invoke-Command -ScriptBlock {git commit -n -m x}",
                "if ($true) { git commit -m x --no-verify}", "git commit ('-n') -m x", "git commit @('-n') -m x",
                "cmd /c git commit -n -m x", 'cmd /c "git commit -n -m x"',
                "Start-Process -Wait -NoNewWindow git -ArgumentList 'commit','-n','-m','x'",
                'powershell "git commit -n -m x"', 'powershell -NoProfile "git commit -n -m x"',
                "powershell -EncodedCommand ZwBpAHQAIABjAG8AbQBtAGkAdAAgAC0AbgAgAC0AbQAgAHgA",
                "${env:GIT_CONFIG_KEY_0}='core.hooksPath'; git commit -m x",
                "$env:GIT_CONFIG_KEY_0 ='core.hooksPath'; git commit -m x",
                "$env:GIT_CONFIG_KEY_0= 'core.hooksPath'; git commit -m x",
                "Set-Item env:GIT_CONFIG_KEY_0 core.hooksPath; git commit -m x",
                "New-Item -Path env:GIT_CONFIG_KEY_0 -Value core.hooksPath; git commit -m x",
                "&git commit -n -m x", "git commit `" + chr(10) + "-n -m x",
                "<# don" + chr(39) + "t #> git commit -n -m x",
                "git commit " + chr(8216) + "-n" + chr(8217) + " -m x"):
    check(f"PowerShell: skipping the hook behind an expression is denied: {command!r}", ps_skips(command), command)
for command in ("git commit -m " + chr(8220) + "docs: use -n never" + chr(8221),
                "git commit -m x <# never use -n #>",
                "git commit -m @'" + chr(13) + chr(10) + "it" + chr(39) + "s -n" + chr(13) + chr(10) + "'@"):
    check(f"PowerShell: text that only mentions a flag still passes: {command!r}",
          run(bare, command, tool="PowerShell")[1] is None, command)
for command in ("npm.cmd run dev", "npm run ('dev')", "if ($true) {npm run dev}", "$job = npm run dev"):
    check(f"PowerShell: the dev server behind an expression is denied: {command!r}",
          ps(configured, command) is not None, command)
for command in ("cmd /c git push origin main", "if ($?) {git push origin main}", "git push origin ('main')",
                "Start-Process git -ArgumentList 'push','origin','main'"):
    check(f"PowerShell: autonomous, the main branch behind an expression is denied: {command!r}",
          run(repo, command, tool="PowerShell")[1] is not None, command)
check("PowerShell: the autonomous-mode guard reads it too",
      run(repo, "git switch main; git merge feat/x", tool="PowerShell")[1] is not None)

# A standing approval lets the publish of a READY delivery through, and nothing else
repo = tempfile.mkdtemp(prefix="guard_standing_")
for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@t.com"), ("config", "user.name", "t"),
             ("commit", "-q", "--allow-empty", "-m", "base")):
    sh("git", *args)
sh(sys.executable, LEDGER_PY, "start", "--slug", "x")
sh(sys.executable, LEDGER_PY, "mode", "autonomous", "--until", (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).isoformat(timespec="seconds"))
sh("git", "checkout", "-q", "-b", "feat/x")


def commit_file(name, text):
    os.makedirs(os.path.dirname(os.path.join(repo, name)) or repo, exist_ok=True)
    with open(os.path.join(repo, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    sh("git", "add", name)
    sh("git", "commit", "-q", "-m", name)


def git_head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()


commit_file("a.txt", "a\n")
gated = git_head()
REPORT = "docs/quality-reports/2026-10-31-x.md"
commit_file(REPORT, f"# x\n\n2026-10-31 · 0000000..{gated[:7]} · v1.2.0\n\n## Checks\n")
PUBLISH = ("gh pr merge 3 --merge", "git checkout main && git merge --no-ff feat/x && git push origin main")
for command in PUBLISH:
    check(f"autonomous, READY report but no standing approval: denied {command!r}", reaches_main(command))
r = subprocess.run([sys.executable, LEDGER_PY, "approve", "--until", "1.5.0", "--conditions", "gate READY"], cwd=repo,
                   capture_output=True, text=True)
check("approve records a standing approval", r.returncode == 0, r.stderr)
for command in PUBLISH:
    check(f"standing approval and a READY report at this tree: passes {command!r}",
          run(repo, command)[1] is None, str(run(repo, command)))
os.makedirs(os.path.join(repo, "sub"), exist_ok=True)
for command in PUBLISH:
    check(f"standing approval, the session in a subfolder of the repository: passes {command!r}",
          run(os.path.join(repo, "sub"), command)[1] is None, str(run(os.path.join(repo, "sub"), command)))
check("standing approval: a push of every branch is still denied", reaches_main("git push --all"))
commit_file("b.txt", "after the gate\n")
check("standing approval: a commit after the READY report is denied", reaches_main("gh pr merge 3 --merge"))
sh("git", "reset", "-q", "--hard", "HEAD~1")
commit_file(REPORT, f"# x\n\n2026-10-31 · 0000000..{gated[:7]} · v1.6.0\n\n## Checks\n")
check("standing approval: a version past --until is denied", reaches_main("gh pr merge 3 --merge"))
sh("git", "reset", "-q", "--hard", "HEAD~1")
r = subprocess.run([sys.executable, LEDGER_PY, "approve", "--revoke"], cwd=repo, capture_output=True, text=True)
check("approve --revoke ends it: denied again", r.returncode == 0 and reaches_main("gh pr merge 3 --merge"), r.stderr)

# A delivery starts only in auto mode unless the user says so: ledger.py start outside it asks first
START = 'sh "${CLAUDE_PLUGIN_ROOT}/hooks/python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/manager/ledger.py" start --slug x'
bare_start = tempfile.mkdtemp(prefix="start_")
reason = run(bare_start, START, mode="default")[1]
check("ledger.py start outside auto mode asks the user, naming the mode",
      reason and reason[0] == "ask" and "default" in reason[1] and "auto" in reason[1], str(reason))
check("start --next of the next delivery asks too", (run(bare_start, START.replace("start", "--ledger "
      ".superpowers/next-x.jsonl start --next"), mode="acceptEdits")[1] or ("",))[0] == "ask")
check("in PowerShell too", (run(bare_start, r"& python C:\p\skills\manager\ledger.py start --slug x",
                                tool="PowerShell", mode="default")[1] or ("",))[0] == "ask")
check("in auto mode it passes", run(bare_start, START, mode="auto")[1] is None)
check("with permissions bypassed it passes", run(bare_start, START, mode="bypassPermissions")[1] is None)
check("another ledger command passes in any mode", run(bare_start, START.replace("start --slug x", "status"),
                                                       mode="default")[1] is None)
check("with no permission_mode in the payload it passes", run(bare_start, START)[1] is None)


# T5: a hub session (its session_id in sessoes of the hub.json found from cwd upwards) cannot approve, integrate or
# run kickoff, and only the owner (dono) writes the registry
def git_repo(folder, autonomous=False):
    for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@t.com"), ("config", "user.name", "t"),
                 ("commit", "-q", "--allow-empty", "-m", "base")):
        subprocess.run(["git", *args], cwd=folder, check=True, capture_output=True)
    subprocess.run([sys.executable, LEDGER_PY, "start", "--slug", "x"], cwd=folder, check=True, capture_output=True)
    if autonomous:
        until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
        subprocess.run([sys.executable, LEDGER_PY, "mode", "autonomous", "--until", until.isoformat(timespec="seconds")],
                       cwd=folder, check=True, capture_output=True)
    return folder.replace(os.sep, "/")


hub_root = tempfile.mkdtemp(prefix="hubroot_")
HUB_JSON = os.path.join(hub_root, ".superpowers", "hub.json")
os.makedirs(os.path.dirname(HUB_JSON))


def hub_json(text):
    with open(HUB_JSON, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


hub_json(json.dumps({"abrir": None, "bg": None, "projetos": {}, "dono": "h2", "sessoes": ["h1", "h2"]}))
os.makedirs(os.path.join(hub_root, "proj"))
hub_proj = git_repo(os.path.join(hub_root, "proj"))
PY = "python C:/p/plugins/foreman/skills"


def hub_denied(command, session="h2", tool="Bash", background=False, cwd=None, text="hub session"):
    reason = run(cwd or hub_root, command, tool=tool, background=background, session=session)[1]
    return reason is not None and reason[0] == "deny" and text in reason[1]


for command in (f"{PY}/manager/ledger.py note --text x", f"{PY}/manager/ledger.py plan --path p",
                f"{PY}/manager/ledger.py mode autonomous", f"{PY}/manager/ledger.py waive --check x",
                f"{PY}/manager/ledger.py extend --tasks 1", f"{PY}/manager/gate.py --report s",
                START, f"{PY}/manager/ledger.py --ledger x.jsonl note --text x"):
    check(f"AC_T5_1 a hub session cannot write a ledger nor run the gate: {command!r}", hub_denied(command),
          str(run(hub_root, command, session="h2")))
check("AC_T5_1 the denial names the step and the project's session",
      "belongs to the project's session" in (run(hub_root, f"{PY}/manager/gate.py", session="h2")[1] or ("", ""))[1])
check("AC_T5_1 ledger.py start in a hub session is denied, not asked", (run(hub_root, START, session="h2", mode="default")[1] or ("",))[0] == "deny")
for command in (f"{PY}/manager/ledger.py status", f"{PY}/manager/ledger.py status --json"):
    check(f"AC_T5_1 a hub session reads a ledger: {command!r}", run(hub_root, command, session="h2")[1] is None,
          str(run(hub_root, command, session="h2")))
for command in ("git commit -m x", "git merge b", "git push", "git cherry-pick c", "git rebase main",
                f"git -C {hub_proj} merge b", f"git -C {hub_proj} commit -m x", "echo ok && git push origin feat/x"):
    for tool in ("Bash", "PowerShell"):
        check(f"AC_T5_2 a hub session cannot commit or integrate ({tool}): {command!r}", hub_denied(command, tool=tool),
              str(run(hub_root, command, tool=tool, session="h2")))
check("AC_T5_2 in the background too", hub_denied("git merge b", background=True))
check("AC_T5_2 the former owner too", hub_denied("git commit -m x", session="h1"))
check("AC_T5_2 from a subfolder of the root too", hub_denied("git commit -m x", cwd=os.path.join(hub_root, "proj")))
for command in ("git status", "git log -n 3", f"git -C {hub_proj} status", f"git -C {hub_proj} log"):
    for tool in ("Bash", "PowerShell"):
        check(f"AC_T5_2 a hub session reads git ({tool}): {command!r}",
              run(hub_root, command, tool=tool, session="h2")[1] is None, str(run(hub_root, command, tool=tool, session="h2")))
for command in ("git init", "git init proj2",
                "sh C:/p/plugins/foreman/hooks/python.sh C:/p/plugins/foreman/hooks/pre-commit-secret-scan.py --install-pre-commit"):
    check(f"AC_T5_3 a hub session cannot start a kickoff: {command!r}", hub_denied(command),
          str(run(hub_root, command, session="h2")))
WRITES = ("delegate --projeto proj", "add --nome a --pasta C:/a", "set --bg on", "remove --projeto a", "init")
for sub_command in WRITES:
    command = f"{PY}/hub/hub.py {sub_command}"
    check(f"AC_T5_4 a former hub session cannot write the registry: {sub_command!r}",
          hub_denied(command, session="h1", text="another hub session took over this root"),
          str(run(hub_root, command, session="h1")))
    check(f"AC_T5_4 the owner writes the registry: {sub_command!r}", run(hub_root, command, session="h2")[1] is None,
          str(run(hub_root, command, session="h2")))
check("AC_T5_4 in PowerShell too", hub_denied(f"& python {PY}/hub/hub.py delegate --projeto proj", session="h1",
                                              tool="PowerShell", text="took over"))
for sub_command in ("status", "status --json", "abrir --projeto proj"):
    check(f"AC_T5_4 a former hub session still reads and opens: {sub_command!r}",
          run(hub_root, f"{PY}/hub/hub.py {sub_command}", session="h1")[1] is None)
for session, folder in (("h2", hub_root), ("h1", hub_root), ("p1", bare), (None, bare)):
    reason = run(folder, f"{PY}/hub/hub.py claim --sessao {session}", session=session)[1]
    check(f"AC_T5_4 hub.py claim from a shell is denied in any session ({session})",
          reason and reason[0] == "deny" and "SessionStart" in reason[1], str(reason))
proj_dir = os.path.join(hub_root, "proj")
for command in ("git commit -m x", "git merge b", f"{PY}/manager/ledger.py note --text x", "git push origin main"):
    check(f"AC_T5_5 a project session inside the hub root works as today: {command!r}",
          run(proj_dir, command, session="p1") == run(proj_dir, command)
          and (run(proj_dir, command)[1] or ("ask",))[0] == "ask", str(run(proj_dir, command, session="p1")))
check("AC_T5_6 no session_id: nothing of the hub is denied", run(hub_root, "git commit -m x")[1] is None)
hub_json("{broken")
check("AC_T5_6 an invalid hub.json: nothing of the hub is denied",
      run(hub_root, "git commit -m x", session="h2")[1] is None)
hub_json(json.dumps({"projetos": [], "dono": "h2", "sessoes": ["h2"]}))
check("AC_T5_6 a hub.json of the wrong shape: nothing of the hub is denied",
      run(hub_root, "git commit -m x", session="h2")[1] is None)
hub_json(json.dumps({"projetos": {}, "dono": "h2", "sessoes": ["h2"]}))
os.makedirs(os.path.join(hub_root, ".superpowers"), exist_ok=True)
open(os.path.join(hub_root, ".superpowers", "ledger.jsonl"), "w").close()
check("AC_T5_6 a hub.json beside a ledger is ignored: the project wins",
      run(hub_root, "git commit -m x", session="h2")[1] is None)
os.remove(os.path.join(hub_root, ".superpowers", "ledger.jsonl"))
check("AC_T5_6 the hub is back once the ledger is gone", hub_denied("git commit -m x"))

# AC-T5-7: git -C <folder> and cd <absolute> are read against that folder's repository, in any session
supervised = git_repo(tempfile.mkdtemp(prefix="t5sup_"))
autonomous = git_repo(tempfile.mkdtemp(prefix="t5auto_"), autonomous=True)
outside = tempfile.mkdtemp(prefix="t5out_")
for command in (f'git -C "{supervised}" merge feat/x', f'git -C "{supervised}" push origin main',
                f'cd "{supervised}" && git push origin main', f'cd "{supervised}" && git merge feat/x'):
    check(f"AC_T5_7 supervised elsewhere: asks {command!r}", asks(command, outside), str(run(outside, command)))
for command in (f'git -C "{autonomous}" merge feat/x', f'git -C "{autonomous}" push origin main',
                f'cd "{autonomous}" && git push origin main', f'cd "{autonomous}"; git merge feat/x'):
    check(f"AC_T5_7 autonomous elsewhere: denied {command!r}", (run(outside, command)[1] or ("",))[0] == "deny",
          str(run(outside, command)))
check("AC_T5_7 in PowerShell too", (run(outside, f"Set-Location {autonomous}; git push origin main",
                                        tool="PowerShell")[1] or ("",))[0] == "deny")
check("AC_T5_7 the target, not the session's folder: from an autonomous repo, a supervised one asks",
      (run(autonomous, f'git -C "{supervised}" push origin main')[1] or ("",))[0] == "ask")
check("AC_T5_7 the target, not the session's folder: from a supervised repo, an autonomous one is denied",
      (run(supervised, f'cd "{autonomous}" && git push origin main')[1] or ("",))[0] == "deny")
for command in (f'git -C "{autonomous}" push origin feat/x', f'cd "{autonomous}" && git status',
                f'git -C "{outside}" push origin main'):
    check(f"AC_T5_7 passes {command!r}", run(outside, command)[1] is None, str(run(outside, command)))

config = json.load(open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8"))
pre = config["hooks"]["PreToolUse"]
check("hooks.json registers bash-guard.py for Bash and PowerShell",
      len(pre) == 1 and pre[0]["matcher"] == "Bash|PowerShell"
      and "${CLAUDE_PLUGIN_ROOT}/hooks/bash-guard.py" in pre[0]["hooks"][0]["command"], json.dumps(config))

print("ALL PASS" if all(results) else "SOME FAILED", f"({sum(results)}/{len(results)})")
sys.exit(0 if all(results) else 1)
