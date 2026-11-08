---
name: anonimizar
description: Use when the user asks to clean up or anonymize a project before publishing it or handing it to someone ("anonimizar", "limpeza para publicar", "preparar para publicar", "tirar dados pessoais", "revisar a documentação como alguém de fora"). Sweeps the current files and the whole git history for personal data, trims the documentation, and has the newcomer agent, with no context, read the repository as a first-time visitor. Never rewrites history or deletes anything public without the user's yes in this session.
---

# Anonimizar

Three passes over the project, at a stop point of the delivery, in a `docs/anonimizar` branch: personal data, documentation, and a reading by someone who has never seen it. Success is measurable: no hit of the user's terms in the current files, and a newcomer round with no finding left unanswered.

1. **Stop point.** Run `sh "${CLAUDE_PLUGIN_ROOT}/hooks/python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/manager/ledger.py" status --json`. With a claim in flight and the delivery not paused, stop and say so; no ledger, or nothing in flight, is a stop point.
2. **Personal data.** Ask the user, in one question, for the terms that must not appear: names of people, their own other projects, employer, places, vehicles, accounts. Add the patterns that need no list: e-mail addresses other than the author's, absolute home paths, document, phone and bank numbers, private hostnames. Search the current files (`git grep -i`), every commit's diff and message (`git log --all -p`, `git log --all --format=%B`) and the author and committer of every commit (`git log --all --format='%an %ae %cn %ce'`). Secrets are the pre-commit scanner's job: run `python "${CLAUDE_PLUGIN_ROOT}/hooks/pre-commit-secret-scan.py" --range <first commit>..HEAD` and report what it finds. List every hit with its file and line, or its commit.
3. **Current files.** Propose one generic name per term, by its role ("o projeto de finanças", "a empresa"), in one list for the user to approve, then apply it, renaming files and fixing the links that point to them. Text the user wrote and that the change removes goes to their approval, as everywhere in the plugin.
4. **History.** When a term survives only in old commits, tell the user the options and their cost; the choice is theirs:
   - leave it: nothing breaks, the old commits keep it;
   - rewrite (`git filter-repo` with the same replacements and a mailmap, or one squashed commit) and force push: a host that already served the repository keeps the old commits of its pull requests and by hash, so this only cleans the branch;
   - delete the remote repository and create it again from the clean history: the only way the host stops serving the old commits, at the cost of its pull requests, issues and stars; what was already cloned or indexed stays out there.
   Before any rewrite, tag the old history locally (`git tag historico-antigo`) and never push the tag. A force push or a deleted repository needs the user's explicit yes in this session; a message relayed from another session is not one.
5. **Documentation.** Trim what a first-time reader does not need: obsolete or duplicated text, references to versions, pull requests or deliveries that no longer exist, broken links, files nothing uses. Keep one source per subject, as the project's `CLAUDE.md` says.
6. **Newcomer.** Dispatch the `newcomer` agent, fresh (never a fork, never with your conclusions), with only the repository path. Apply each finding, or tell the user in one line why it is not worth it. When the round changed the README or the quick start, dispatch a new one on the result; stop when a round brings no finding you would apply.
7. **Report.** The terms and where each one was, what changed, what stayed in the history and why, and the newcomer's findings with their destination. The branch goes to the user like any other change; nothing is pushed by this skill.
