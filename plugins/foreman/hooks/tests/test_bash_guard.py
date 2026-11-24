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
WRITES = ("delegate --projeto proj", "add --nome a --pasta C:/a", "set --bg on", "remove --projeto a", "init",
          "liberar --projeto proj")
for sub_command in WRITES:
    command = f"{PY}/hub/hub.py {sub_command}"
    check(f"AC_T5_4 a former hub session cannot write the registry: {sub_command!r}",
          hub_denied(command, session="h1", text="another hub session took over this root"),
          str(run(hub_root, command, session="h1")))
    check(f"AC_T5_4 the owner writes the registry: {sub_command!r}", run(hub_root, command, session="h2")[1] is None,
          str(run(hub_root, command, session="h2")))
check("AC_T5_4 in PowerShell too", hub_denied(f"& {PY}/hub/hub.py delegate --projeto proj", session="h1",
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

# T5 fix round 1 (the review probe rows)
import shutil


def decision(folder, command, **kw):
    return (run(folder, command, **kw)[1] or ("pass",))[0]


hub_json(json.dumps({"abrir": None, "bg": None, "projetos": {}, "dono": "h2", "sessoes": ["h1", "h2"]}))
outs = outside.replace(os.sep, "/")
# 1. a step whose folder comes from cd tracking is judged against the tracked folder and the session's: the stricter
auto_name = os.path.basename(autonomous)
for command in (f"pushd {outs}; popd; git push origin main", f"(cd {outs} && ls); git push origin main",
                f"ls $(cd {outs} && pwd); git merge feat/x", f"cd {outs} && cd ../{auto_name} && git push origin main",
                f"git -C {outs} -C {autonomous} push origin main", f"cd {outs}; cd -; git push origin main",
                f"cd {outs} && gh pr merge 1", f"(cd {outs}); git merge feat/x"):
    check(f"FIX1_T5 a cd the guard cannot follow keeps the session's own repository: denied {command!r}",
          decision(autonomous, command) == "deny", str(run(autonomous, command)))
check("FIX1_T5 PowerShell Push-Location and Pop-Location too",
      decision(autonomous, f"Push-Location {outs}; Pop-Location; git push origin main", tool="PowerShell") == "deny")
parent = os.path.dirname(autonomous)
check("FIX1_T5 every -C joins the one before it, as git does",
      decision(outside, f"git -C {parent} -C {auto_name} push origin main") == "deny")
check("FIX1_T5 a rooted -C alone decides: a work-branch push there passes",
      decision(autonomous, f'git -C "{supervised}" push origin feat/x') == "pass")
# 2. a hub.json that raises leaves the rest of the guard on
nest = tempfile.mkdtemp(prefix="t5nest_")
os.makedirs(os.path.join(nest, ".superpowers"))
os.makedirs(os.path.join(nest, "p"))
inner = git_repo(os.path.join(nest, "p"), autonomous=True)
with open(os.path.join(nest, ".superpowers", "hub.json"), "w", encoding="utf-8") as handle:
    handle.write("[" * 200000)
for command in ("git push origin main", "git commit --no-verify -m x"):
    check(f"FIX2_T5 a hub.json nested too deep above a project: still denied {command!r}",
          decision(inner, command, session="p1") == "deny", str(run(inner, command, session="p1")))
copy = tempfile.mkdtemp(prefix="t5copy_")
os.makedirs(os.path.join(copy, "hooks"))
shutil.copy(SCRIPT, os.path.join(copy, "hooks"))
shutil.copytree(os.path.join(HOOKS, "..", "skills", "manager"), os.path.join(copy, "skills", "manager"),
                ignore=shutil.ignore_patterns("tests", "__pycache__"))
os.makedirs(os.path.join(copy, "skills", "hub"))


def copied(command):
    payload = {"tool_name": "Bash", "cwd": hub_root, "session_id": "h2", "tool_input": {"command": command}}
    done = subprocess.run([sys.executable, os.path.join(copy, "hooks", "bash-guard.py")], input=json.dumps(payload),
                          capture_output=True, text=True, encoding="utf-8", cwd=tempfile.gettempdir())
    return json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] if done.stdout.strip() else "pass"


for label, text in (("missing", None), ("broken", "def (:\n"), ("exiting", "raise SystemExit(0)\n")):
    if text is not None:
        with open(os.path.join(copy, "skills", "hub", "hub.py"), "w", encoding="utf-8") as handle:
            handle.write(text)
    check(f"FIX2_T5 a {label} hub.py: the rest of the guard still runs", copied("git commit -n -m x") == "deny")
# 3. a shell of the other kind is read whatever the tool
for command in ("cmd /c git commit -m x", "powershell -Command 'git commit -m x'", "pwsh -c 'git merge b'",
                "cmd //c 'git commit -m x'"):
    check(f"FIX3_T5 Bash: a hub session reads into {command!r}", hub_denied(command), str(run(hub_root, command, session="h2")))
for command in ("bash -c 'git commit -m x'", 'sh -c "git push"', "Start-Process git 'commit -m x'",
                "Start-Process -FilePath git -ArgumentList 'commit -m x'"):
    check(f"FIX3_T5 PowerShell: a hub session reads into {command!r}", hub_denied(command, tool="PowerShell"),
          str(run(hub_root, command, tool="PowerShell", session="h2")))
for command in ("cmd /c git commit -n -m x", "powershell -Command 'git commit --no-verify -m x'"):
    check(f"FIX3_T5 Bash: skipping the hook in the other shell is denied {command!r}", skips(command))
for command in ("bash -c 'git commit -n -m x'", "Start-Process git 'commit -n -m x'"):
    check(f"FIX3_T5 PowerShell: skipping the hook in the other shell is denied {command!r}", ps_skips(command))
# 4. a hub session runs only read-only git
for command in ("git pull . feat/x", "git revert HEAD", "git am x.patch", "git fetch . feat/x:main", "git fetch",
                "git commit-tree x", "git update-ref refs/heads/main abc", "git reset --hard feat/x",
                "git branch -f main feat/x", "git branch new", "git tag v1", "git tag -d v1", "git stash",
                "git checkout -B main feat/x", "git worktree add ../w", "git clone x y", "git remote add o u",
                "git config user.name x", "git symbolic-ref HEAD refs/heads/x", "git switch main", "git restore x",
                "git --attr-source HEAD commit -m x"):
    check(f"FIX4_T5 a hub session cannot run git that writes: {command!r}", hub_denied(command),
          str(run(hub_root, command, session="h2")))
for command in ("git status", "git log", "git diff", "git show HEAD", "git rev-parse HEAD", "git remote", "git remote -v",
                "git branch", "git branch -a", "git branch --list 'f*'", "git branch --show-current",
                "git config --get user.name", "git config --list", "git ls-files", "git describe", "git shortlog -s",
                "git blame f", "git grep x", "git cat-file -p HEAD", "git for-each-ref", "git merge-base a b",
                "git name-rev HEAD", "git symbolic-ref HEAD", "git worktree list", "git stash list", "git tag",
                "git tag -l", "git --version"):
    check(f"FIX4_T5 a hub session reads with git: {command!r}", decision(hub_root, command, session="h2") == "pass",
          str(run(hub_root, command, session="h2")))
# 5. options that hide the subcommand
for command in ("git --attr-source HEAD commit -n -m x", "git -c alias.z=commit z -m x",
                "git --config-env=alias.z=E z -m x", "git -c Alias.z='commit -n' z"):
    check(f"FIX5_T5 a hidden subcommand or an alias is denied in any session: {command!r}", skips(command),
          str(run(bare, command)))
# 6. a script counts only when it runs
SKILLS = "C:/p/plugins/foreman/skills"
for command in (f"cat {SKILLS}/manager/ledger.py", "ls skills/manager/ledger.py", f"grep -n status {SKILLS}/manager/gate.py",
                f"cat {SKILLS}/hub/hub.py", "cat hub.py claim", "grep -n hub.py claim.txt"):
    check(f"FIX6_T5 a hub session reads a script's file: {command!r}", decision(hub_root, command, session="h2") == "pass",
          str(run(hub_root, command, session="h2")))
check("FIX6_T5 any session: cat hub.py claim passes", decision(bare, "cat hub.py claim", session="p1") == "pass")
for command in (f"cd {SKILLS}/manager && python -m ledger note --text x", f"python -X utf8 {SKILLS}/manager/ledger.py note",
                f"python3 {SKILLS}/manager/gate.py", f"py -3 {SKILLS}/manager/ledger.py waive x",
                f"{SKILLS}/manager/ledger.py note --text x"):
    check(f"FIX6_T5 a hub session still cannot run it: {command!r}", hub_denied(command),
          str(run(hub_root, command, session="h2")))
check("FIX6_T5 PowerShell: python -m ledger", hub_denied("python -m ledger note", tool="PowerShell"))
check("FIX6_T5 hub.py claim behind an option is denied",
      decision(hub_root, f"python {SKILLS}/hub/hub.py --raiz . claim --sessao h1", session="p1") == "deny")
# 7. a junction or link to a folder under the root is the hub
link = os.path.join(tempfile.mkdtemp(prefix="t5link_"), "j")
if os.name == "nt":
    subprocess.run(["cmd", "/c", "mklink", "/J", link, os.path.join(hub_root, "proj")], capture_output=True)
else:
    os.symlink(os.path.join(hub_root, "proj"), link)
check("FIX7_T5 a hub session through a junction to a folder under the root", os.path.isdir(link)
      and hub_denied("git commit -m x", cwd=link), str(run(link, "git commit -m x", session="h2")))
# 8. --git-dir, --work-tree and GIT_DIR name the repository like -C
for command in (f"git --git-dir={autonomous}/.git --work-tree={autonomous} push origin main",
                f"git --git-dir {autonomous}/.git push origin main", f"GIT_DIR={autonomous}/.git git merge feat/x",
                f"export GIT_DIR={autonomous}/.git; git push origin main"):
    check(f"FIX8_T5 the repository a git dir names decides: denied {command!r}", decision(outside, command) == "deny",
          str(run(outside, command)))
check("FIX8_T5 PowerShell $env:GIT_DIR too",
      decision(outside, f"$env:GIT_DIR='{autonomous}/.git'; git push origin main", tool="PowerShell") == "deny")
# 9. only the dono writes a registry that exists
proj_dir_slash = proj_dir.replace(os.sep, "/")
root_slash = hub_root.replace(os.sep, "/")
for command in (f"{PY}/hub/hub.py set --raiz {root_slash} --bg on",
                f"{PY}/hub/hub.py delegate --raiz={root_slash} --projeto proj"):
    check(f"FIX9_T5 a project session cannot write the hub's registry: {command!r}",
          decision(proj_dir, command, session="p1") == "deny", str(run(proj_dir, command, session="p1")))
    check(f"FIX9_T5 the dono can, from anywhere: {command!r}", decision(proj_dir, command, session="h2") == "pass",
          str(run(proj_dir, command, session="h2")))
check("FIX9_T5 a session in the root that is not in sessoes cannot write it",
      decision(hub_root, f"{PY}/hub/hub.py add --nome a --pasta C:/a", session="x9") == "deny")
fresh = tempfile.mkdtemp(prefix="t5fresh_").replace(os.sep, "/")
check("FIX9_T5 init where there is no hub.json yet passes for anyone",
      decision(proj_dir, f"{PY}/hub/hub.py init --raiz {fresh}", session="p1") == "pass")
check("FIX9_T5 reading the registry passes for anyone",
      decision(proj_dir, f"{PY}/hub/hub.py status --raiz {root_slash}", session="p1") == "pass")

# T5 fix round 2 (the re-review probe rows)
# 1. a named folder the guard cannot resolve falls back to the cd-tracked folder and the session's
for command, tool in (('git -C "$PWD" push origin main', "Bash"), ('git -C "$(pwd)" merge feat/x', "Bash"),
                      ('git -C "$(git rev-parse --show-toplevel)" push origin main', "Bash"),
                      ("git -C $REPO push origin main", "Bash"), ('git --git-dir="$PWD/.git" push origin main', "Bash"),
                      ("GIT_DIR=$PWD/.git git merge feat/x", "Bash"), ("git -C nope merge feat/x", "Bash"),
                      ("git -C $PWD push origin main", "PowerShell"), ("git -C (Get-Location) merge x", "PowerShell")):
    check(f"FIX2_1_T5 a folder the guard cannot resolve keeps the session's repository ({tool}): denied {command!r}",
          decision(autonomous, command, tool=tool) == "deny", str(run(autonomous, command, tool=tool)))
# 2. a registry with no dono yet (fresh from init) is writable by any session; once claimed, only by the dono
HUB_PY = os.path.join(HOOKS, "..", "skills", "hub", "hub.py")
first = tempfile.mkdtemp(prefix="t5first_")
subprocess.run([sys.executable, HUB_PY, "init", "--raiz", first], check=True, capture_output=True)
first_s = first.replace(os.sep, "/")
FIRST_WRITES = (f"{PY}/hub/hub.py add --nome a --pasta C:/a", f"{PY}/hub/hub.py set --bg on",
                f"{PY}/hub/hub.py delegate --projeto a")
for command in FIRST_WRITES:
    check(f"FIX2_2_T5 a fresh hub with no dono: any session writes {command!r}",
          decision(first, command, session="s1") == "pass", str(run(first, command, session="s1")))
subprocess.run([sys.executable, HUB_PY, "claim", "--sessao", "s2", "--raiz", first], check=True, capture_output=True)
for command in FIRST_WRITES:
    check(f"FIX2_2_T5 once s2 claims, s1 is denied {command!r}", decision(first, command, session="s1") == "deny")
    check(f"FIX2_2_T5 once s2 claims, s2 writes {command!r}", decision(first, command, session="s2") == "pass")
check("FIX2_2_T5 with a dono, a payload with no session_id is denied", decision(first, FIRST_WRITES[0]) == "deny")
# 3. the usual launchers are looked through
LAUNCH_START = f"uv run python {SKILLS}/manager/ledger.py start --slug x"
check("FIX2_3_T5 uv run python ledger.py start outside auto mode asks",
      decision(bare_start, LAUNCH_START, mode="default") == "ask", str(run(bare_start, LAUNCH_START, mode="default")))
for launcher in ("uv run", "poetry run", "pipenv run", "hatch run", "pdm run", "uv run --frozen"):
    command = f"{launcher} python {SKILLS}/manager/ledger.py note --text x"
    check(f"FIX2_3_T5 a hub session cannot write a ledger behind {launcher!r}", hub_denied(command),
          str(run(hub_root, command, session="h2")))
check("FIX2_3_T5 py -3 python version flag", hub_denied(f"py -3.12 {SKILLS}/manager/ledger.py note"))
# 4. more read-only git
for command in ("git rev-list HEAD", "git ls-tree HEAD", "git show-ref", "git ls-remote origin", "git branch --contains x",
                "git branch --merged main", "git branch --no-merged", "git reflog", "git reflog show HEAD"):
    check(f"FIX2_4_T5 a hub session reads with git: {command!r}", decision(hub_root, command, session="h2") == "pass",
          str(run(hub_root, command, session="h2")))
for command in ("git reflog expire --all", "git reflog delete HEAD@{1}"):
    check(f"FIX2_4_T5 a hub session cannot write the reflog: {command!r}", hub_denied(command))
# 5. git -c alias.* has a reason of its own
alias_reason = (run(bare, "git -c alias.z=commit z -m x")[1] or ("", ""))[1]
check("FIX2_5_T5 git -c alias.* names the alias, not the secret scan",
      "alias" in alias_reason and "secret-scan" not in alias_reason, alias_reason)
check("FIX2_5_T5 --no-verify keeps the secret-scan reason",
      "secret-scan" in (run(bare, "git commit -n -m x")[1] or ("", ""))[1])

# Final review I1: a stray hub.json inside a project under the hub root does not hide the real hub
hub_json(json.dumps({"abrir": None, "bg": None, "projetos": {}, "dono": "h2", "sessoes": ["h1", "h2"]}))
stray = os.path.join(hub_root, "proj", ".superpowers")
os.makedirs(stray, exist_ok=True)
for label, text, beside in (("unlisted", json.dumps({"projetos": {}, "dono": "x9", "sessoes": ["x9"]}), False),
                            ("invalid", "{broken", False),
                            ("beside a ledger", json.dumps({"projetos": {}, "dono": "h2", "sessoes": ["h2"]}), True)):
    with open(os.path.join(stray, "hub.json"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    if beside:
        open(os.path.join(stray, "ledger.jsonl"), "w").close()
    for command in ("git commit -m x", f"{PY}/manager/ledger.py approve"):
        check(f"FINAL_I1 a {label} hub.json in a project under the hub: still denied {command!r}",
              hub_denied(command, cwd=os.path.join(hub_root, "proj")),
              str(run(os.path.join(hub_root, "proj"), command, session="h2")))
    for name in ("hub.json", "ledger.jsonl"):
        if os.path.exists(os.path.join(stray, name)):
            os.remove(os.path.join(stray, name))
# Final review M1: a hub session does not merge a pull request
for command in ("gh pr merge 3 --merge", "glab mr merge 3"):
    check(f"FINAL_M1 a hub session cannot merge a pull request: {command!r}", hub_denied(command),
          str(run(hub_root, command, session="h2")))

config = json.load(open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8"))
pre = config["hooks"]["PreToolUse"]
check("hooks.json registers bash-guard.py for Bash and PowerShell",
      len(pre) == 1 and pre[0]["matcher"] == "Bash|PowerShell"
      and "${CLAUDE_PLUGIN_ROOT}/hooks/bash-guard.py" in pre[0]["hooks"][0]["command"], json.dumps(config))

print("ALL PASS" if all(results) else "SOME FAILED", f"({sum(results)}/{len(results)})")
sys.exit(0 if all(results) else 1)
