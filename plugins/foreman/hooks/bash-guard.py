#!/usr/bin/env python3
"""PreToolUse hook (matcher Bash|PowerShell, see hooks.json): denies skipping the secret-scan pre-commit hook,
anything that reaches the default branch while the delivery is in autonomous mode, a relative cd before a git step
that lands work, a git checkout or restore that overwrites work not committed, a project command inside timeout,
the project's dev server outside background mode, and what a foreman hub session may not do (approve, integrate,
run kickoff), and gh text published with one of the owner's terms; asks the user before a delivery starts outside Claude Code's auto permission mode (not the delivery's
autonomous mode).

With a ledger (any mode), denied in the foreground or background: a relative change of directory (cd, pushd,
Set-Location and their aliases, to a path that does not start at a root, a drive or ~, or cd -) followed in the same
command by a git merge, cherry-pick, commit, rebase, pull, worktree remove or branch delete, dev agents' commands in
their worktree included. Not read: a cd inside ( ) or $( ), which stays in its subshell, a target held in a variable,
and a git step after a later rooted cd or with git -C and a rooted path. From a copy's worktree a
relative path lands somewhere else, and a failed cd lets the steps after it run in the wrong folder or not at all
without anyone noticing (an integration skipped twice in one delivery); git -C with an absolute path names the folder.

With a ledger (any mode), also denied in the foreground or background: a git checkout or git restore whose paths
(after --, or the words that are no commit) git status lists as changed, in the folder of its git -C or of the
latest rooted cd before it: the work in those files is lost with no way back (a dev undid uncommitted work this way
twice in one delivery, against a lesson no project test can check). Passing: a branch change, restore --staged
alone, --ours, --theirs, -p, a file with no change.

In any repository, with or without a ledger: a gh pr, gh issue or gh release command whose title, body or notes
(--title, --body, --notes and their short forms, or the file --body-file or --notes-file names), or a gh api whose
body or title field (-f, -F, --field, --raw-field, or the --input file), holds one of the owner's terms or a home path,
or a file it names that cannot be read, by the rules of pre-commit-secret-scan.py (a value the shell builds, stdin
or a file the same command writes is read from the whole command, the file paths taken out; the gh options above, a
short option glued to its value and -R before the subcommand are read): that text reaches the host directly, where no commit scan reads it, and a
comment's edit history stays public (a pull request comment named a project's flows once). A file the same command
writes is read from the command. The reason never prints the term.

A ledger.py start (also start --next), run in a session whose permission_mode is neither auto nor
bypassPermissions, asks the user first, naming the mode: the delivery would stop at each permission prompt while the
user is away. A payload with no permission_mode passes.

In autonomous mode (the latest mode entry of the ledger ledger.py finds from the session's directory), denied in the
foreground or background: a git push of the default branch (named by origin/HEAD, else init.defaultBranch, main or
master: as a refspec's target, with --all or --mirror, or with no refspec while it is checked out; --tags alone
passes), a git merge while it is checked out (--abort and --quit pass), and a pull request merge (gh pr merge or glab
mr merge or accept, also behind the tool's own options, and its api on pulls/<n>/merge or merge_requests/<n>/merge). A
git checkout or switch earlier in the same command counts as what is checked out for the rest of it (a checkout with
-- or of a word that is no branch here restores files and changes nothing). Each step is read in the repository it
runs in, in any session, with that repository's default branch, checked-out branch, ledger mode and standing
approval, as if the command ran there. A rooted path decides alone: a git -C (every -C joined to the one before it,
as git does), --git-dir, --work-tree, or GIT_DIR or GIT_WORK_TREE set before it (a prefix or an export); a named
folder the guard cannot resolve ($PWD, $(pwd), a missing folder) counts as none. Otherwise
the step is read both in the folder of the latest cd to a rooted path before it and in the session's directory, and
the stricter answer wins (deny, then ask): a cd the guard does not follow (popd, cd -, a relative cd, one inside ( )
or $( )) cannot move the check away from the session's repository. Pushing and merging the work branch pass; in
supervised mode, or with no ledger, nothing here is denied, and a push of the default branch (the same reading) asks
the user: approval 2 is theirs, and a push of a work branch passes, since a permission rule cannot tell them apart
inside a compound command. With the user's standing
approval (ledger.py approve, read from approval.json beside the ledger), a publish passes when what it publishes is a
gated delivery: the commit (the ref a git merge names, HEAD for a pull request merge, the source of a push, or the
default branch a merge earlier in the same command already approved) has the tree of the commit that last added the
delivery's quality report (docs/quality-reports/*-<slug>.md, which the gate writes on READY only), the report's head
differs from that commit only in docs/quality-reports/, and the report's version is at most the approval's --until. A
push with --all, --mirror or --delete is still denied.

A git -c or --config-env that defines an alias is denied in any session, with a reason of its own: the alias can
hide the real subcommand (and skip the hook).

Skipping the hook is denied in any project, in the foreground or background: a git commit with --no-verify (or an
unambiguous prefix such as --no-veri) or -n (also inside a cluster such as -nm or -an), a git -c or --config-env that
sets core.hooksPath, a GIT_CONFIG_* assignment naming it (also through env or export), and a git config that writes or
unsets it. The command is read word by word as the shell splits it, after the heredoc bodies the shell only passes
along are removed, so a flag quoted inside a commit message is a message, not a flag. Wrappers such as env, command,
time, nohup, xargs, `!`, `{` and if/then are looked through; a command given to a shell's -c (also -lc, and after
options that take a value, such as -o pipefail), to powershell, pwsh or cmd (whichever tool runs it) or to
eval is read the same way (a script the shell runs is a command
of its own), and so is a command substitution outside quotes; one inside double quotes is not read. Permission rules
match the command as plain text and cannot tell a flag from a message, which is why this check lives here. A command
that does not parse (an unbalanced quote) passes, since the shell refuses it too.

A foreman hub session (its payload session_id in "sessoes" of the first .superpowers/hub.json from the session's
directory upwards that lists it, valid by hub.py's own check, and with no .superpowers/ledger.jsonl beside it: there
the project wins; a stray hub.json below the hub is passed over; links and junctions resolved) only reads and
delegates; it is denied a pull request merge (gh, glab) too. Denied in it, in the foreground or background, git -C
included: any git outside the read-only list (status, log, diff, show, rev-parse, ls-files, describe, shortlog,
blame, grep, cat-file, for-each-ref, merge-base, name-rev, rev-list, ls-tree, show-ref, ls-remote; remote alone or
-v; branch with no name or with --list, --contains, --merged or --no-merged; config --get, --get-all or --list;
symbolic-ref with one name; worktree list; stash list; reflog alone or show; tag alone or -l), so
commit, merge, push, fetch, pull, reset and init too; any ledger.py command but status; gate.py;
pre-commit-secret-scan.py --install-pre-commit (the first writing steps of a kickoff). A script counts when it runs:
as the program, as the script of python, py, sh or bash (also through python.sh and behind uv, poetry, pipenv, hatch
or pdm run), or as python -m <name>; reading
its file (cat, grep, ls) passes. The reason reads "hub session: <step> belongs to the project's session". A hub
session that is not the "dono" is denied hub.py delegate, add, set, remove, liberar and init ("another hub session took over
this root"); status and abrir pass. In any session, those writing commands are denied when the root they name
(--raiz, else the session's directory) has a valid hub.json whose dono is another session (no session_id included);
a registry with no dono yet (fresh from init) is written by any session, and the next SessionStart claims it.
hub.py claim is denied in every session, since only the SessionStart hook runs it. Without a session_id, or with no
valid hub.json that lists it, the session is no hub session; a hub.json or hub.py that fails to load leaves the rest of
the guard on.

A PowerShell call goes through the same checks, read with PowerShell's own rules. Text the command only passes
along: single quotes literal ('' an escaped quote), double quotes with a backtick escape, the typographic quotes as
the straight pair they stand for, a here-string body (@'...'@), a `<# ... #>` block and a `#` that opens a word, to
the end of its line. Separators: `;` `|` a newline and `&&` `||`, and `{` `}` too, since a script block is a
command of its own whether or not a space follows the brace; a backtick before a line break is a space, and what
stands between parentheses is read also as an argument of the command around them, which is what PowerShell makes
of it. Looked through: the call operator `&`, alone or glued to the name; `$name = <command>`, the variable gone
and the command kept; -Command (any unambiguous prefix), cmd's /c, the first positional argument of powershell.exe
and a decoded -EncodedCommand, read like a shell's -c; Invoke-Expression or iex, like eval; and Start-Process with
its -ArgumentList. `$env:NAME = value` is read as the assignment it is, in any spacing, as `${env:NAME}` and as a
Set-Item or New-Item on env:NAME. Not read, so still passing: a flag held in a variable, an alias, splatting, a
`%VAR%` expanded after `--%` (a flag written out after it still counts) and a command inside double quotes.

A dev server run in the foreground never returns: the call hangs, and the process is orphaned when it times out.
The command comes from the project's CLAUDE.md, the line `- Rodar em desenvolvimento: `<command>`` under
"Comandos" (the same lines gate.py reads); the plugin knows no stack. Without a CLAUDE.md found from the session's
directory upwards, or without that line holding a command in backticks, it does nothing.

Denied: a call without run_in_background whose command contains the dev command at the start of a shell
segment (after &&, ||, ;, |, a newline, an opening parenthesis or env assignments), alone or followed by arguments;
`npm run dev &` counts too, because the shell leaves the same orphan. Text the shell only passes along is not
read: quoted strings (a commit message) and heredoc bodies (a file being written), unless a shell reads the
heredoc (`bash <<EOF`). The reason names the right form.

Denied in a Bash call, in the foreground or background: any command of a "Comandos" line run as timeout's command
(timeout and its options and duration at the start of a shell segment, read as the dev server is): timeout kills it
at the limit, the suite half run (a qa lost an interface run so). The reason names background mode with a log of its
own. Any failure of the hook itself lets the call through."""
import base64
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "..", "skills", "manager", "gate.py")
LEDGER = os.path.join(HERE, "..", "skills", "manager", "ledger.py")
HUB = os.path.join(HERE, "..", "skills", "hub", "hub.py")
LABEL = "rodar em desenvolvimento"


def project_commands(start):
    """The commands of the "Comandos" lines of the CLAUDE.md found from start upwards: [(label key, command)]."""
    spec = importlib.util.spec_from_file_location("foreman_gate", GATE)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    folder = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(folder, "CLAUDE.md")):
            os.chdir(folder)
            return [(gate.label_key(label), command) for label, command in gate.comandos() if command]
        parent = os.path.dirname(folder)
        if parent == folder:
            return []
        folder = parent


def dev_command(commands):
    return next((command for key, command in commands if key == LABEL), None)


HEREDOC = re.compile(r"^(?P<head>[^\n]*?)(?<!<)<<(?!<)-?\s*\\?(['\"]?)(?P<tag>[\w.-]+)\2[^\n]*\n(?P<body>.*?)"
                     r"(?:\n[ \t]*(?P=tag)[ \t]*(?=\n|$)|\Z)", re.S | re.M)
SHELL_INPUT = re.compile(r"(?:^|[\s;&|(])(?:ba|z|da)?sh(?:\s+-\w+)*\s*$")
QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")


def executed(command):
    """The command without the text the shell only passes along: heredoc bodies (unless a shell reads them) and
    quoted strings, so a message or a file that mentions the dev command is not taken for running it."""
    def heredoc(match):
        text = match.group(0)
        return text if SHELL_INPUT.search(match.group("head")) else text.replace(match.group("body"), "", 1)
    return QUOTED.sub("''", HEREDOC.sub(heredoc, command))


def program_name(word):
    """The command's name without its path, its case or a Windows executable suffix."""
    return re.sub(r"\.(exe|cmd|bat|ps1)$", "", re.split(r"[\\/]", word)[-1].lower())


TIMEOUT = r"timeout(?:\s+(?:-[ks]\s+\S+|-\S+))*\s+\d[\d.]*[smhd]?\s+"


def runs_it(command, dev, powershell=False, prefix=""):
    """True when the command runs the dev command: in PowerShell, as a simple command of its own, since its
    quoting is resolved word by word; in Bash, at the start of a shell segment of the text the shell executes."""
    words = dev.split()
    if powershell:
        return any(program == program_name(words[0]) and list(arguments[:len(words) - 1]) == words[1:]
                   for program, arguments, _ in simple_commands(command, powershell=True))
    pattern = r"\s+".join(re.escape(word) for word in words)
    return re.search(r"(?:^|&&|\|\||[;|\n(])\s*(?:[A-Za-z_]\w*=\S*\s+)*" + prefix + pattern + r"(?=\s|$|[;&|)])",
                     executed(command)) is not None


SHELLS = {"sh", "bash", "zsh", "dash"}
SHELL_VALUE = {"--rcfile", "--init-file"}  # with -o, -O, +o, +O (also ending a cluster): an option and its value
PS_SHELLS = {"powershell", "pwsh", "cmd"}
PS_LAUNCHERS = {"start-process", "saps", "start"}
PS_SET_ENV = {"set-item", "si", "new-item", "ni", "set-variable", "sv"}
EVALS = {"eval"}
PS_EVALS = {"invoke-expression", "iex"}
WRAPPERS = {"env", "command", "time", "nohup", "exec", "xargs", "!", "{", "&", "if", "then", "else", "elif", "do",
            "while", "until"}
CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--list", "-l", "get", "list"}
CONFIG_UNSETS = {"--unset", "--unset-all", "unset"}
COMMIT_VALUE = set("mFCct")
COMMIT_ATTACHED = set("uS")
PUSH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
COMMIT_LONG_VALUE = {"--message", "--file", "--author", "--date", "--reuse-message", "--reedit-message", "--template",
                     "--fixup", "--squash", "--cleanup", "--trailer", "--pathspec-from-file"}


def segments(command, commenters=""):
    """Each simple command as its words, quotes resolved, with heredoc bodies the shell only passes along removed."""
    text = HEREDOC.sub(lambda match: match.group(0) if SHELL_INPUT.search(match.group("head"))
                       else match.group(0).replace(match.group("body"), "", 1), command)
    lexer = shlex.shlex(re.sub(r"[<>]&|&>", ">", text), posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace, lexer.whitespace_split, lexer.commenters = " \t\r", True, commenters
    found, words = [], []
    for token in lexer:
        if token and set(token) <= set(";&|()\n"):
            if words:
                found.append(words)
            words = []
        else:
            words.append(token)
    return found + [words] if words else found


PS_HERESTRING = re.compile(r"@(['\"])[ \t]*\r?\n.*?\n\1@", re.S)
PS_SEPARATORS = ";\n|(){}"
PS_QUOTES = {"'": "'", '"': '"', "\u2018": "\u2019", "\u2019": "\u2019", "\u201c": "\u201d", "\u201d": "\u201d"}
PS_LITERAL = {"'", "\u2018", "\u2019"}


def ps_quoted(text, index, quote):
    """The text of the quoted string that opens at index, and the index after it. Inside single quotes '' is an
    escaped quote and nothing else is special; inside double quotes a backtick escapes the next character. The
    typographic quotes PowerShell also accepts are read as the straight pair they stand for."""
    closing, word, index = PS_QUOTES[quote], "", index + 1
    while index < len(text):
        char = text[index]
        if char == closing:
            if text[index + 1:index + 2] != closing:
                return word, index + 1
            index += 1
        elif char == "`" and quote not in PS_LITERAL:
            index += 1
            if index >= len(text):
                break
        word += text[index]
        index += 1
    raise ValueError(f"unbalanced {closing} in the PowerShell command")


def ps_glued(words):
    """An assignment written with the `=` apart put back together: `$x = v`, `$x =v` and `$x= v` all become `$x=v`,
    so one rule reads every spacing PowerShell accepts."""
    found, index = [], 0
    while index < len(words):
        word = words[index]
        if word.startswith("$") and "=" not in word and words[index + 1:index + 2] \
                and words[index + 1].startswith("="):
            word, index = word + words[index + 1], index + 1
        if word.startswith("$") and word.endswith("=") and words[index + 1:index + 2]:
            word, index = word + words[index + 1], index + 1
        found.append(word)
        index += 1
    return found


def ps_assignments(words):
    """A PowerShell assignment read as the shape the checks already know. `$env:NAME=value` becomes
    `export NAME=value` (also `${env:NAME}=`, the `=` spaced either way, and a Set-Item or New-Item on env:NAME):
    it does change the process environment of what follows. `$name = <command>` keeps the command, which runs
    either way, and drops the variable. A `$env:NAME` read as a value is left as it is, so it stays one argument."""
    words = ps_glued(words)
    if words and program_name(words[0]) in PS_SET_ENV:
        names = [word[len("env:"):] for word in words[1:] if re.fullmatch(r"env:\w+", word, re.I)]
        values = [word for word in words[1:]
                  if not word.startswith("-") and not re.fullmatch(r"env:\w+", word, re.I)]
        if names and values:
            return ["export", names[0] + "=" + values[-1]]
    found = []
    for word in words:
        name, sep, value = word.partition("=")
        plain = name.replace("${", "$").replace("}", "")
        if plain.lower().startswith("$env:") and sep:
            found += ["export", plain[len("$env:"):] + "=" + value]
        elif plain.startswith("$") and sep:
            found += [value] if value else []
        else:
            found.append(word)
    return found


def ps_segments(command):
    """Each simple command of a PowerShell command line as its words, quotes resolved, with the here-string bodies
    the command only passes along removed. Raises ValueError on an unbalanced quote, which PowerShell refuses too."""
    text = PS_HERESTRING.sub("''", command)
    found, words, word, open_word, index = [], [], "", False, 0
    while index < len(text):
        char, pair = text[index], text[index:index + 2]
        if char in PS_QUOTES:
            quoted, index = ps_quoted(text, index, char)
            word, open_word = word + quoted, True
            continue
        if pair == "${" and text.find("}", index + 2) >= 0:
            end = text.find("}", index + 2)
            word, open_word, index = word + text[index:end + 1], True, end + 1
            continue
        if open_word and (char in " \t\r" or char in PS_SEPARATORS or pair in ("&&", "||")):
            words.append(word)
            word, open_word = "", False
        if pair == "<#" and not open_word:
            end = text.find("#>", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        if char == "`" and text[index + 1:index + 2] in ("\n", "\r"):
            index += 1
            while index < len(text) and text[index] in "\r\n":
                index += 1
            continue
        if char == "#" and not open_word:
            index = text.find("\n", index)
            if index < 0:
                break
            continue
        if char in PS_SEPARATORS or pair in ("&&", "||"):
            if words:
                found.append(words)
                words = []
            index += 2 if pair in ("&&", "||") else 1
        elif char in " \t\r":
            index += 1
        else:
            if char == "`":
                index += 1
                if index >= len(text):
                    break
            word, open_word = word + text[index], True
            index += 1
    if open_word:
        words.append(word)
    return [ps_assignments(segment) for segment in (found + [words] if words else found)]


def hooks_path(key):
    return key.split("=", 1)[0].lower() == "core.hookspath"


def alias_key(key):
    return key.split("=", 1)[0].lower().startswith("alias.")


PS_COMMAND_FLAGS = ("/c", "/k", "/r", "//c", "//k")  # //c: cmd's /c as Git Bash passes it


def ps_inner(words):
    """The command a PowerShell or cmd call runs: behind -Command (any unambiguous prefix) or cmd's /c, decoded
    from -EncodedCommand, or the first word that is not an option, which powershell.exe reads as -Command too."""
    for index, word in enumerate(words[1:], 1):
        lower = word.lower()
        if lower.startswith("-") and len(lower) > 2 and "-encodedcommand".startswith(lower):
            try:
                return base64.b64decode(words[index + 1]).decode("utf-16-le", "ignore")
            except Exception:
                return None
        if (lower.startswith("-") and len(lower) > 1 and "-command".startswith(lower)) \
                or lower in PS_COMMAND_FLAGS:
            return " ".join(words[index + 1:])
        if not lower.startswith(("-", "/")):
            return " ".join(words[index:])
    return None


def simple_commands(command, powershell=False):
    """Each simple command the shell runs, as (program, its arguments, the segment's words), looking through
    wrappers and into a shell's -c (PowerShell's -Command) and eval (Invoke-Expression). In Bash a '#' is read as
    text first (it starts a comment only at the start of a word, which shlex cannot tell); a command that does not
    parse that way is read again with '#' as a comment, and one that parses neither way yields nothing."""
    try:
        parsed = ps_segments(command) if powershell else segments(command)
    except ValueError:
        if powershell:
            return
        try:
            parsed = segments(command, "#")
        except ValueError:
            return
    if powershell and "(" in command:
        try:
            parsed = parsed + ps_segments(command.replace("(", " ").replace(")", " "))
        except ValueError:
            pass
    for segment in parsed:
        words = segment
        while words:
            if words[0] in WRAPPERS or re.fullmatch(r"[A-Za-z_]\w*=.*", words[0]) \
                    or (words[0].startswith("-") and len(words) > 1):
                words = words[1:]
            elif powershell and words[0].startswith("&") and len(words[0]) > 1:
                words = [words[0][1:]] + words[1:]
            else:
                break
        if not words:
            continue
        program = program_name(words[0])
        if program in PS_SHELLS:  # read whatever the tool: a Bash call can run PowerShell and the reverse
            inner = ps_inner(words)
            if inner:
                yield from simple_commands(inner, True)
        elif powershell and program in PS_LAUNCHERS:
            parts = [part for word in words[1:] if not word.startswith("-")
                     for part in re.split(r"[,\s]+", word) if part]
            if parts:
                yield program_name(parts[0]), parts[1:], parts
        elif program in SHELLS:
            position = 1
            while position < len(words) - 1:
                word = words[position]
                if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", word):
                    yield from simple_commands(words[position + 1])
                    break
                if not word.startswith(("-", "+")):
                    yield program, words[1:], segment  # a script the shell runs
                    break
                position += 2 if word in SHELL_VALUE or re.fullmatch(r"[-+][A-Za-z]*[oO]", word) else 1
        elif program in (PS_EVALS if powershell else EVALS):
            yield from simple_commands(" ".join(words[1:]), powershell)
        else:
            yield program, words[1:], segment


GIT_VALUE = ("-C", "--git-dir", "--work-tree", "--namespace", "--attr-source")


def git_command(arguments):
    """The git subcommand and its arguments, past git's own options, and whether those options set core.hooksPath
    (True) or else an alias ("alias", which can hide the real subcommand)."""
    rest, override = list(arguments), False
    while rest and rest[0].startswith("-"):
        option, _, attached = rest[0].partition("=")
        if option in ("-c", "--config-env"):
            key = attached or (rest[1] if len(rest) > 1 else "")
            override = True if hooks_path(key) else override or ("alias" if alias_key(key) else False)
            rest = rest[1:] if attached else rest[2:]
        elif option in GIT_VALUE and not attached:
            rest = rest[2:]
        else:
            rest = rest[1:]
    return (rest[0] if rest else ""), rest[1:], override


def skips_hook(command, powershell=False):
    """True when the command skips the pre-commit hook."""
    for program, arguments, segment in simple_commands(command, powershell):
        if any(re.fullmatch(r"GIT_CONFIG\w*=.*", word) and "core.hookspath" in word.lower() for word in segment):
            return True
        if program != "git":
            continue
        name, rest, override = git_command(arguments)
        if override is True:
            return True
        if name == "config":
            keys = [i for i, word in enumerate(rest) if word.lower() == "core.hookspath"]
            if keys and not CONFIG_READS & set(rest) and (keys[0] + 1 < len(rest) or CONFIG_UNSETS & set(rest)):
                return True
        elif name == "commit" and commit_skips(rest):
            return True
    return False


def sets_alias(command, powershell=False):
    """True when a git step defines an alias on its command line (git -c alias.x=..., --config-env=alias.x=...)."""
    return any(program == "git" and git_command(arguments)[2] == "alias"
               for program, arguments, _ in simple_commands(command, powershell))


def git_out(cwd, *args):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def ledger_state(cwd):
    """(ledger module, ledger path, entries) for the session's directory, or None with no ledger."""
    spec = importlib.util.spec_from_file_location("foreman_ledger", LEDGER)
    ledger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger)
    os.chdir(cwd)
    try:
        path = ledger.default_ledger("status")
        return ledger, path, ledger.read(path)
    except SystemExit:
        return None


def gated(cwd, ref, state):
    """True when the standing approval covers publishing ref: see the docstring."""
    ledger, path, entries = state
    cwd = git_out(cwd, "rev-parse", "--show-toplevel") or cwd  # the report's paths are from the root, not a subfolder
    approval, slug = ledger.standing(path), entries and entries[0].get("slug")
    commit = ref and git_out(cwd, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    if not approval or not slug or not commit:
        return False
    reports = sorted(name for name in git_out(cwd, "ls-tree", "--name-only", commit, "docs/quality-reports/").splitlines()
                     if name.endswith(f"-{slug}.md"))
    added = reports and git_out(cwd, "log", "-1", "--format=%H", commit, "--", reports[-1])
    match = added and re.search(r"\b[0-9a-f]{7,40}\.\.([0-9a-f]{7,40})\b.*?\bv(\d+\.\d+\.\d+)\b",
                                git_out(cwd, "show", f"{added}:{reports[-1]}"))
    if not match or (ledger.version_key(match.group(2)) or ()) > ledger.version_key(approval["until"]):
        return False
    head = git_out(cwd, "rev-parse", "--verify", "--quiet", match.group(1) + "^{commit}")
    if not head or subprocess.run(["git", "diff", "--quiet", added, commit], cwd=cwd, capture_output=True).returncode:
        return False
    changed = subprocess.run(["git", "diff", "--name-only", head, added], cwd=cwd, capture_output=True, text=True)
    return changed.returncode == 0 and all(line.startswith("docs/quality-reports/")
                                           for line in changed.stdout.splitlines())


def main_branch(cwd):
    remote = git_out(cwd, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if remote:
        return remote.split("/", 1)[-1]
    names = [git_out(cwd, "config", "--get", "init.defaultBranch"), "main", "master"]
    return next((name for name in names
                 if name and git_out(cwd, "rev-parse", "--verify", "--quiet", "refs/heads/" + name)), None)


def push_sources(arguments, main, current):
    """What a push that reaches the default branch publishes there: the source of each refspec whose target it is
    (the branch checked out with no refspec), or None when it is no single commit (--all, --mirror, --delete)."""
    if {"--all", "--mirror", "--delete", "-d"} & set(arguments):
        return None
    positional = [word for position, word in enumerate(arguments) if not word.startswith("-")
                  and not (position and arguments[position - 1] in PUSH_VALUE)]
    if len(positional) < 2:
        return [current]
    sources = []
    for spec in positional[1:]:
        source, _, target = spec.lstrip("+").rpartition(":") if ":" in spec else ("", "", spec.lstrip("+"))
        if target.removeprefix("refs/heads/") == main or (target in ("HEAD", "@") and current == main):
            sources.append(source if ":" in spec else target)
    return sources if all(sources) else None


def merged_ref(arguments):
    value_next = False
    for word in arguments:
        if value_next:
            value_next = False
        elif word in ("-m", "-s", "-X", "-F", "--strategy", "--strategy-option", "--file"):
            value_next = True
        elif not word.startswith("-"):
            return word
    return None


def push_reaches(arguments, main, current):
    positional, value_next = [], False
    for word in arguments:
        if value_next:
            value_next = False
        elif word in ("--all", "--mirror"):
            return True
        elif word in PUSH_VALUE:
            value_next = True
        elif not word.startswith("-"):
            positional.append(word)
    if len(positional) < 2:
        return current == main and "--tags" not in arguments
    for spec in positional[1:]:
        target = spec.lstrip("+").split(":")[-1].removeprefix("refs/heads/")
        if target == main or (target in ("HEAD", "@") and current == main):
            return True
    return False


def switched_to(name, arguments, cwd):
    """The branch a git checkout or git switch leaves checked out, or None when it is not a branch change: a git
    checkout with -- or of a word that is no local or remote branch here (a path, ., HEAD) restores files."""
    if name == "checkout" and "--" in arguments:
        return None
    for position, word in enumerate(arguments):
        if word in ("-b", "-B", "-c", "-C", "--orphan"):
            return arguments[position + 1] if position + 1 < len(arguments) else None
        if not word.startswith("-"):
            if name == "switch" or git_out(cwd, "rev-parse", "--verify", "--quiet", f"refs/heads/{word}") \
                    or git_out(cwd, "for-each-ref", "--count=1", f"refs/remotes/*/{word}"):
                return word
            return None
    return None


def merges_pull_request(arguments):
    pairs = zip(arguments, arguments[1:])
    return any(pair in (("pr", "merge"), ("mr", "merge"), ("mr", "accept")) for pair in pairs) or (
        arguments[:1] == ["api"]
        and any(re.search(r"(pulls|merge_requests)/\d+/merge\b", word) for word in arguments))


GIT_PLACE = re.compile(r"GIT_(DIR|WORK_TREE)=(.*)")


def git_folders(arguments, places, bases):
    """The folders a git step may run in. Every -C joins the one before it, as git does, and --git-dir, --work-tree
    and GIT_DIR or GIT_WORK_TREE (places) name the repository the same way; a rooted path decides alone, a relative
    one joins each base (the folder cd tracking gives and the session's: the stricter answer wins, see reaches_main).
    When none of the named folders exists, the bases are read."""
    paths, place, rest = [], dict(places), list(arguments)
    while rest and rest[0].startswith("-"):
        option, sep, value = rest[0].partition("=")
        if option in GIT_VALUE and not sep:
            value, rest = (rest[1] if len(rest) > 1 else ""), rest[2:]
        else:
            rest = rest[1:]
        if option == "-C":
            paths.append(value)
        elif option in ("--git-dir", "--work-tree"):
            place["DIR" if option == "--git-dir" else "WORK_TREE"] = value
    named = place.get("WORK_TREE") or place.get("DIR")
    if named:
        paths.append(named)
    named = bases
    for path in paths:
        named = [folder_of(path, base) for base in (["/"] if ROOTED.match(path) else named)]
    found = []
    for folder in named:
        folder = os.path.abspath(folder)
        if os.path.basename(folder) == ".git":
            folder = os.path.dirname(folder)
        if os.path.isdir(folder) and folder not in found:
            found.append(folder)
    # a name the guard cannot resolve ($PWD, $(pwd), a missing folder): read the bases instead, never nothing
    return found or [folder for folder in dict.fromkeys(map(os.path.abspath, bases)) if os.path.isdir(folder)]


def reaches_main(command, cwd, powershell=False):
    """Returns "deny" in autonomous mode when the command merges into or pushes the default branch, or merges a pull
    request; "ask" for the same commands otherwise (supervised, or no ledger); None when neither. Each step is read
    in each repository it may run in (git_folders), and the stricter answer wins. A git checkout or switch earlier
    in the same command counts as the branch checked out there for what follows it. The session's folder is left
    out only when every cd so far went to an existing rooted folder inside a repository, in a chain of && and ;
    alone (no ||, pipe, background, subshell, block, substitution, redirection or newline), so each step runs there."""
    cwd = os.path.abspath(cwd)
    calls, where, places = [], cwd, {}
    chained = re.fullmatch(r"[^|&()\n`$<>{}]*(&&[^|&()\n`$<>{}]*)*", command) is not None
    here = lambda: [where] if chained and where != cwd else list(dict.fromkeys([where, cwd]))
    for program, arguments, segment in simple_commands(command, powershell):
        if program == "export":
            places.update(match.groups() for match in map(GIT_PLACE.fullmatch, arguments) if match)
        elif program.lower() in CHANGES_DIRECTORY:
            target = next((word for word in arguments if not word.startswith("-")), None)
            if target and ROOTED.match(target) and os.path.isdir(folder_of(target, where)):
                where = os.path.abspath(folder_of(target, where))
                chained = chained and bool(git_out(where, "rev-parse", "--show-toplevel"))
            else:
                chained = False
        elif program == "git":
            name, rest, _ = git_command(arguments)
            start = next((i for i, word in enumerate(segment) if program_name(word) == "git"), 0)
            local = dict(places)
            local.update(match.groups() for match in map(GIT_PLACE.fullmatch, segment[:start]) if match)
            if name in ("push", "merge", "checkout", "switch"):
                calls.append((program, name, rest, git_folders(arguments, local, here())))
        elif program in ("gh", "glab"):
            calls.append((program, "", arguments, here()))
    if not any(name in ("push", "merge") or (program != "git" and merges_pull_request(rest))
               for program, name, rest, _ in calls):
        return None
    repos, verdicts = {}, set()
    for program, name, rest, folders in calls:
        for folder in folders:
            if folder not in repos:
                state = ledger_state(folder)
                repos[folder] = {"state": state, "autonomous": bool(state) and state[0].autonomous(state[2]),
                                 "main": main_branch(folder), "current": git_out(folder, "branch", "--show-current"),
                                 "published": set()}
            verdicts.add(publish_verdict(program, name, rest, folder, repos[folder]))
    return "deny" if "deny" in verdicts else "ask" if "ask" in verdicts else None


def publish_verdict(program, name, rest, folder, repo):
    """"deny", "ask" or None for one step in one repository; a checkout or switch moves repo["current"]."""
    state, autonomous, main, current = repo["state"], repo["autonomous"], repo["main"], repo["current"]
    if program != "git":
        if merges_pull_request(rest) and not autonomous:
            return "ask"
        if autonomous and merges_pull_request(rest) and not gated(folder, "HEAD", state):
            return "deny"
    elif name in ("checkout", "switch"):
        repo["current"] = switched_to(name, rest, folder) or current
    elif main and name == "push" and push_reaches(rest, main, current):
        if not autonomous:
            return "ask"
        sources = push_sources(rest, main, current)
        if sources is None or not all(source in repo["published"] or gated(folder, source, state)
                                      for source in sources):
            return "deny"
    elif main and name == "merge" and current == main and not {"--abort", "--quit"} & set(rest):
        if not autonomous:
            return "ask"
        if not gated(folder, merged_ref(rest), state):
            return "deny"
        repo["published"].add(main)
    return None


def commit_skips(arguments):
    value_next = False
    for word in arguments:
        if value_next:
            value_next = False
        elif word == "--":
            return False
        elif word.startswith("--"):
            name = word.split("=", 1)[0]
            if name.startswith("--no-v") and "--no-verify".startswith(name):
                return True
            value_next = name in COMMIT_LONG_VALUE and "=" not in word
        elif word.startswith("-") and len(word) > 1:
            for position, flag in enumerate(word[1:], 1):
                if flag == "n":
                    return True
                if flag in COMMIT_VALUE:
                    value_next = position == len(word) - 1
                    break
                if flag in COMMIT_ATTACHED:
                    break
    return False


UNATTENDED = {"auto", "bypassPermissions"}


INTERPRETER = re.compile(r"python[\d.]*w?|py|sh|bash|zsh|dash")
PYTHON_VALUE = {"-W", "-X", "-Q"}
LAUNCHERS = {"uv", "poetry", "pipenv", "hatch", "pdm"}


def script_args(program, arguments, name):
    """The arguments of the script called name (ledger.py, gate.py, hub.py) when the step runs it: as the program
    itself, or as the script an interpreter runs (python, py, sh, bash, also through python.sh), python -m <name>
    included; past ledger.py's --ledger. None when the step does not run it (cat ledger.py, python -c ...)."""
    if program in LAUNCHERS and arguments[:1] == ["run"]:
        rest = list(arguments[1:])
        while rest and rest[0].startswith("-"):  # shortcut: a launcher option with a value (uv run --with x) is not read
            rest = rest[1:]
        return script_args(program_name(rest[0]), rest[1:], name) if rest else None
    if program == name:
        rest = list(arguments)
    elif INTERPRETER.fullmatch(program):
        position, rest = 0, None
        while position < len(arguments):
            word = arguments[position]
            if word == "-m":
                if arguments[position + 1:position + 2] != [name[:-len(".py")]]:
                    return None
                rest = arguments[position + 2:]
                break
            if word == "-c":
                return None
            if word.startswith("-"):
                position += 2 if word in PYTHON_VALUE else 1
            elif program_name(word) == "python.sh":
                position += 1
            else:
                rest = arguments[position + 1:] if program_name(word) == name else None
                break
        if rest is None:
            return None
    else:
        return None
    while rest and rest[0].startswith("--ledger"):
        rest = rest[1:] if "=" in rest[0] else rest[2:]
    return list(rest)


def starts_delivery(command, powershell=False):
    """True when the command runs ledger.py start (also start --next): the delivery begins there."""
    return any((script_args(program, arguments, "ledger.py") or [])[:1] == ["start"]
               for program, arguments, _ in simple_commands(command, powershell))


def hub_registry(folder):
    """The hub.json of folder when hub.py's own valid() accepts it, else None; any failure (a file that does not
    parse, nested too deep, a hub.py that is missing or broken) is None, so the rest of the guard still runs."""
    try:
        with open(os.path.join(folder, ".superpowers", "hub.json"), encoding="utf-8") as handle:
            data = json.load(handle)
        spec = importlib.util.spec_from_file_location("foreman_hub", HUB)
        hub = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hub)
        return data if hub.valid(data) else None
    except (Exception, SystemExit):
        return None


def hub_session(cwd, session_id):
    """"owner" or "former" when session_id is in sessoes of the first hub.json from cwd upwards that lists it (links
    and junctions resolved); one that is invalid, beside a ledger (that project wins for its own sessions) or does
    not list the session is passed over, so a stray hub.json in a project does not hide the hub above it. None with
    no session_id or no hub.json that lists it."""
    if not isinstance(session_id, str) or not session_id:
        return None
    folder = os.path.realpath(cwd)
    while True:
        here = os.path.join(folder, ".superpowers")
        if os.path.isfile(os.path.join(here, "hub.json")) and not os.path.exists(os.path.join(here, "ledger.jsonl")):
            data = hub_registry(folder)
            if data and session_id in data.get("sessoes", []):
                return "owner" if data.get("dono") == session_id else "former"
        if os.path.dirname(folder) == folder:
            return None
        folder = os.path.dirname(folder)


HUB_COMMANDS = {"init", "status", "add", "set", "remove", "delegate", "abrir", "claim", "liberar"}
HUB_WRITES = {"delegate", "add", "set", "remove", "init", "liberar"}
GIT_READS = {"status", "log", "diff", "show", "rev-parse", "ls-files", "describe", "shortlog", "blame", "grep",
             "cat-file", "for-each-ref", "merge-base", "name-rev", "rev-list", "ls-tree", "show-ref", "ls-remote",
             "help", "version", ""}
BRANCH_LISTS = {"--list", "-l", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at"}
BRANCH_READS = {"-a", "-r", "-v", "-vv", "--all", "--remotes", "--verbose", "--show-current"} | BRANCH_LISTS
CONFIG_WRITES = {"--add", "--replace-all", "--unset", "--unset-all", "--rename-section", "--remove-section", "--edit",
                 "-e", "set", "unset", "rename-section", "remove-section", "edit"}
TOOK_OVER = ("another hub session took over this root: only the newest hub session writes the registry. This one "
             "still reads (hub.py status) and opens projects (hub.py abrir); work from the newest hub window.")


def git_reads(name, rest):
    """True for the git a hub session may run: it only reads. Everything else writes or can (fetch . x:main)."""
    positional = [word for word in rest if not word.startswith("-")]
    if name in GIT_READS:
        return True
    if name == "remote":
        return rest in ([], ["-v"], ["--verbose"])
    if name == "branch":
        return all(word in BRANCH_READS for word in rest if word.startswith("-")) \
            and (not positional or bool(BRANCH_LISTS & set(rest)))
    if name == "config":
        return bool(CONFIG_READS & set(rest)) and not CONFIG_WRITES & set(rest)
    if name == "symbolic-ref":
        return len(positional) <= 1 and not {"-d", "--delete"} & set(rest)
    if name == "reflog":
        return rest[:1] in ([], ["show"])
    if name in ("worktree", "stash"):
        return rest[:1] == ["list"]
    if name == "tag":
        return not rest or bool({"-l", "--list"} & set(rest)) and not {"-d", "--delete", "-f", "-a", "-s", "-m"} & set(rest)
    return False


def hub_denial(command, powershell, role, cwd, session_id):
    """Why the command may not run, or None: a hub session (role "owner" or "former", None for any other) only reads
    and delegates; a registry that exists is written only by its dono; hub.py claim runs only from SessionStart."""
    for program, arguments, _ in simple_commands(command, powershell):
        hub = script_args(program, arguments, "hub.py")
        sub = next((word for word in hub or [] if word in HUB_COMMANDS), None)
        if sub == "claim":
            return ("hub.py claim is run only by the SessionStart hook: a session becomes the hub's owner by "
                    "starting or resuming in the hub folder.")
        if sub in HUB_WRITES:
            if role == "former":
                return TOOK_OVER
            raiz = next((after for word, after in zip(hub, hub[1:]) if word == "--raiz"), None) or next(
                (word.split("=", 1)[1] for word in hub if word.startswith("--raiz=")), None)
            data = hub_registry(folder_of(raiz, cwd) if raiz else cwd)
            if data and data.get("dono") and data["dono"] != session_id:
                return TOOK_OVER if session_id in data.get("sessoes", []) else (
                    f"hub.py {sub} writes a hub's registry, and only that hub's owner session (its newest hub "
                    "window) writes it; ask there.")
        if role is None:
            continue
        ledger, step = script_args(program, arguments, "ledger.py"), None
        if program == "git" and not git_reads(*git_command(arguments)[:2]):
            step = "git " + git_command(arguments)[0]
        elif program in ("gh", "glab") and merges_pull_request(arguments):
            step = f"{program} merge of a pull request"
        elif ledger is not None and ledger[:1] != ["status"]:
            step = " ".join(["ledger.py"] + ledger[:1])
        elif script_args(program, arguments, "gate.py") is not None:
            step = "gate.py"
        elif "--install-pre-commit" in (script_args(program, arguments, "pre-commit-secret-scan.py") or []):
            step = "pre-commit-secret-scan.py --install-pre-commit"
        if step:
            return (f"hub session: {step} belongs to the project's session. The hub only reads and delegates: send "
                    "the request with hub.py delegate, and the user approves in the project's window.")
    return None


CHANGES_DIRECTORY = {"cd", "pushd", "set-location", "sl", "chdir", "push-location"}
# The git steps that integrate, commit or remove a copy: run in the wrong folder they do the wrong thing or nothing.
LANDS = {"merge", "cherry-pick", "commit", "rebase", "pull"}
ROOTED = re.compile(r"[/\\~]|[A-Za-z]:")


def relative_cd_before_git(command, powershell=False):
    """True when a relative change of directory comes before a git step that integrates, commits or removes a
    copy, in the same command. A cd inside ( ) or $( ) stays in its subshell, a target held in a variable is not
    read, a rooted cd after it puts the folder back on firm ground, and git -C with a rooted path names its own."""
    while (inner := re.sub(r"\$?\([^()]*\)", " ", command)) != command:
        command = inner
    moved = False
    for program, arguments, _ in simple_commands(command, powershell):
        if program.lower() in CHANGES_DIRECTORY:
            target = next((word for word in arguments if not word.startswith("-") or word == "-"), None)
            if target is not None and not re.match(r"[$%`]", target):
                moved = not ROOTED.match(target)
        elif moved and program == "git":
            name, rest, _ = git_command(arguments)
            named = any(word == "-C" and ROOTED.match(after) for word, after in zip(arguments, arguments[1:]))
            deletes = name == "branch" and any(word == "--delete" or re.fullmatch(r"-[A-Za-z]*[dD][A-Za-z]*", word)
                                               for word in rest)
            if not named and (name in LANDS or (name == "worktree" and rest[:1] == ["remove"]) or deletes):
                return True
    return False


KEEPS_WORK = {"--ours", "--theirs", "-p", "--patch", "-m", "--merge", "--conflict"}
RESTORE_VALUE = {"-s", "--source", "--pathspec-from-file"}


def folder_of(target, cwd):
    """A cd target or git -C path as a folder the git subprocess can enter (/c/x is C:/x on Windows)."""
    target = os.path.expanduser(target)
    if os.name == "nt" and re.match(r"/[A-Za-z](/|$)", target):
        target = target[1] + ":" + (target[2:] or "/")
    return os.path.join(cwd, target)


def discards_work(command, cwd, powershell=False):
    """True when a git checkout or git restore overwrites a file whose work is not committed: the paths it names
    (after --, or the words that are no commit) that git status lists as changed in that folder. A branch change, a
    restore of the index alone (--staged), a conflict side (--ours, --theirs) and the interactive -p pass."""
    where = cwd
    for program, arguments, _ in simple_commands(command, powershell):
        if program.lower() in CHANGES_DIRECTORY:
            target = next((word for word in arguments if not word.startswith("-")), None)
            if target and ROOTED.match(target):
                where = folder_of(target, cwd)
            continue
        if program != "git":
            continue
        name, rest, _ = git_command(arguments)
        named = next((after for word, after in zip(arguments, arguments[1:]) if word == "-C"), None)
        folder = folder_of(named, where) if named else where
        if name not in ("checkout", "restore") or KEEPS_WORK & set(rest) or not os.path.isdir(folder):
            continue
        if name == "restore" and ({"--staged", "-S"} & set(rest)) and not ({"--worktree", "-W"} & set(rest)):
            continue
        if name == "checkout" and "--" not in rest and switched_to(name, rest, folder):
            continue
        paths, value_next = [], False
        for position, word in enumerate(rest):
            if word == "--":
                paths = rest[position + 1:]
                break
            if value_next:
                value_next = False
            elif word in RESTORE_VALUE or (name == "checkout" and word in ("-b", "-B", "--orphan")):
                value_next = True
            elif not word.startswith("-") and not (name == "checkout" and not paths and git_out(
                    folder, "rev-parse", "--verify", "--quiet", word + "^{commit}")):
                paths.append(word)
        if paths and git_out(folder, "status", "--porcelain", "--untracked-files=no", "--", *paths):
            return True
    return False


GH_TEXT = {"--body", "-b", "--title", "-t", "--notes", "-n", "--subject"}
GH_FILE = {"--body-file", "-F", "--notes-file"}
GH_FIELD = {"-f", "-F", "--field", "--raw-field"}
GH_KEYS = {"body", "title", "query", "name", "description", "message"}
GH_SHORT = {flag for flag in GH_TEXT | GH_FILE | GH_FIELD if not flag.startswith("--")}


def local_path(path, cwd):
    match = re.fullmatch(r"/([a-zA-Z])(/.*)?", path)  # a Git Bash path such as /c/Users/...
    if os.name == "nt" and match:
        path = match.group(1) + ":" + (match.group(2) or "/")
    return os.path.join(cwd, os.path.expanduser(path))


def published_text(command, cwd, powershell=False):
    """The text a gh command publishes on the host (the title, body, notes or subject of a pull request, issue,
    comment, release or merge, and the body, title, query, name, description or message fields of gh api), each file
    it names read, and the files it names but nobody can read. A value the shell builds (a $( ) or heredoc, a
    variable, a PowerShell here-string or expression, stdin) or a file the same command writes is read from the whole
    command, with those file paths taken out."""
    texts, paths, unreadable, whole = [], [], [], False
    for program, arguments, _ in simple_commands(command, powershell):
        if program != "gh":
            continue
        while arguments and arguments[0].startswith("-"):  # gh -R owner/repo pr ...
            arguments = arguments[2 if arguments[0] in ("-R", "--repo") else 1:]
        api = bool(arguments) and arguments[0] == "api"
        if not api and (not arguments or arguments[0] not in ("pr", "issue", "release") or len(arguments) < 2):
            continue
        for index, word in enumerate(arguments):
            if word.startswith("--"):
                flag, _, inline = word.partition("=")
            elif len(word) > 2 and word[:2] in GH_SHORT:
                flag, inline = word[:2], word[2:]
            else:
                flag, inline = word, ""
            value = inline or (arguments[index + 1] if index + 1 < len(arguments) else "")
            name = None
            if api and flag in GH_FIELD:
                key, _, field = value.partition("=")
                if key not in GH_KEYS:
                    continue
                if flag == "-F" and field.startswith("@"):
                    name = field[1:]
                else:
                    value = field
            elif api and flag == "--input" or not api and flag in GH_FILE:
                name = value
            elif api or flag not in GH_TEXT:
                continue
            if name is None:
                if not value or re.search(r"[$`]", value) or value.startswith(("@'", '@"', "(")):
                    whole = True
                else:
                    texts.append(value)
            elif name == "-":
                whole = True
            else:
                try:
                    texts.append(open(local_path(name, cwd), encoding="utf-8", errors="replace").read())
                except OSError:
                    if command.count(name) > 1:  # the same command writes it
                        whole = True
                        paths.append(name)
                    else:
                        unreadable.append(name)
    if whole:
        rest = command
        for name in paths:
            rest = rest.replace(name, "")
        texts.append(rest)
    return [text for text in texts if text], unreadable


def owner_hit(texts, cwd):
    """Whether a text holds one of the owner's terms or a home path, by the pre-commit scanner's own rules."""
    if not texts:
        return False
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "foreman_scan", os.path.join(os.path.dirname(os.path.abspath(__file__)), "pre-commit-secret-scan.py"))
    scan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scan)
    owner = scan.Owner(cwd)
    return any(owner.term_in(text) or any(scan.home_path(line) for line in text.splitlines()) for text in texts)


def main():
    payload = json.load(sys.stdin)
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return
    powershell = payload["tool_name"] == "PowerShell"
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    cwd = payload.get("cwd") or os.getcwd()
    mode = payload.get("permission_mode")
    found = {}
    commands = lambda folder: found.setdefault(folder, project_commands(folder))
    try:  # a hub.json or hub.py that fails never switches off the rest of the guard
        role = hub_session(cwd, payload.get("session_id"))
    except Exception:
        role = None
    hub_reason = hub_denial(command, powershell, role, cwd, payload.get("session_id"))
    if not hub_reason and mode and mode not in UNATTENDED and starts_delivery(command, powershell):
        json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                          "permissionDecisionReason": (
                                              f"This session is in {mode} mode, not auto: the delivery would stop at "
                                              "each permission prompt while the user is away. Start it anyway, or "
                                              "restart the session in auto mode first?")}}, sys.stdout)
        return
    try:  # a parse that fails never switches off the rest of the guard
        published = published_text(command, cwd, powershell)
    except Exception:
        published = ([], [])
    skips = skips_hook(command, powershell)
    aliased = not skips and sets_alias(command, powershell)
    publishes = None if skips or hub_reason or aliased else reaches_main(command, cwd, powershell)
    if hub_reason:
        reason = hub_reason
    elif aliased:
        reason = ("git -c alias.* can hide the real subcommand (and skip the pre-commit hook): define the alias in git "
                  "config, or run the command itself.")
    elif skips:
        reason = ("This skips the secret-scan pre-commit hook (--no-verify, -n or a core.hooksPath override), and a "
                  "secret committed stays in the history. Commit without it; if the hook blocks, fix what it reports "
                  "(a false positive is allowlisted by the user, as its message explains).")
    elif published[1]:
        reason = ("This publishes the text of a file nobody can read from here (" + ", ".join(published[1]) + "), so "
                  "the owner's terms cannot be checked before it reaches the host. Name the file by a path from this "
                  "folder, or write it in the same command.")
    elif owner_hit(published[0], cwd):
        reason = ("This publishes text on the host (a pull request, issue, comment or release title or body) with one "
                  "of the owner's terms or a home path, and the commit scan never sees it. Reword it generically (a "
                  "project of the author, the role instead of the name, no internal names) and publish again; the "
                  "term is not printed here.")
    elif publishes == "deny":
        reason = ("The delivery is in autonomous mode (the ledger says so), and nothing reaches the default branch "
                  "without the user: no push to it, no merge into it, no pull request merge. Leave the merge and the "
                  "push for approval 2, when the user returns.")
    elif relative_cd_before_git(command, powershell) and (ledger_state(cwd) or (0, 0, []))[2]:
        reason = ("A relative cd before a git merge, cherry-pick, commit, rebase, pull, worktree remove or branch "
                  "delete runs that step from wherever the cd lands, or not at all when it fails, and the steps "
                  "after it go on silently. Name the folder instead, with git -C <absolute path>, one step per "
                  "command (as references/parallel.md integrates).")
    elif discards_work(command, cwd, powershell) and (ledger_state(cwd) or (0, 0, []))[2]:
        reason = ("This git checkout or git restore overwrites a file whose work is not committed, and that work is "
                  "lost for good. Undo only the lines you mean to with an edit, or commit (a wip: commit) or stash "
                  "first; git status lists what would go.")
    elif not powershell and any(runs_it(command, line, prefix=TIMEOUT) for _, line in commands(cwd)):
        reason = ("timeout kills this project command at its limit, the suite half run and the run lost. Run it with "
                  "the tool's run_in_background set to true, its output in a log of its own, and read the log when "
                  "it finishes.")
    elif tool_input.get("run_in_background"):
        reason = None
    else:
        dev = dev_command(commands(cwd))
        reason = None if not dev or not runs_it(command, dev, powershell) else (
            f"`{dev}` is this project's dev server and never returns, so in the foreground it hangs the call and "
            "leaves an orphan process. Run the same command with the tool's run_in_background set to true "
            "(and stop it before you finish), or reuse a server already running for this directory.")
    if reason is None:
        if publishes == "ask":  # only when nothing above denies: a denial wins over the ask
            json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                              "permissionDecisionReason": "This reaches the main branch (a push, a "
                                              "merge into it or a pull request merge): approval 2 is the user's."}},
                      sys.stdout)
        return
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                      "permissionDecisionReason": reason}}, sys.stdout)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
