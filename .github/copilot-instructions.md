# Core: Generic DevOps Cycle

Applies to any project, any stack. These are the guardrails and workflow an
agent would not otherwise follow by default.

## Non-negotiables

- **Never commit or push.** Stage files, edit code, draft commit messages and
  PR descriptions; the developer reviews and runs `git commit`/`git push`.
- **Never run a destructive or irreversible command without explicit
  confirmation**: history rewrites (`push --force`, `reset --hard`, `rebase`
  on shared branches, `commit --amend` on pushed commits), deletions
  (`rm -rf`, `clean -fdx`, dropped branches/DBs/tables, `TRUNCATE`/`DROP`),
  or environment/production changes. Prefer dry-run/status first; explain the
  command and let the developer run it if in doubt.
- Use the `tara` CLI instead of hand-rolling setup or checks — `tara new`,
  `tara check`, `tara standards`; run `tara --help` to discover the rest.

## Workflow: the fixed flow

Don't skip steps; say why if one genuinely doesn't apply.

1. **Understand** the task and its Definition of Done before touching code.
2. **Plan** non-trivial changes and confirm before implementing.
3. **Test first** (TDD): one failing test per behaviour, independent tests.
4. **Implement** the minimum to pass, in small reviewable increments.
5. **Check**: `tara check` (lint, format, types, tests, security) green
   before moving on; don't pile new work on a red gate.
6. **Document**: update docs/README and the runnable example; changelog if
   user-facing.
7. **Hand off**: verify the Definition of Done, stage changes, draft the
   commit message, and log a handover note (below).

When blocked, say so; don't silently guess.

## Agent memory (`.agents/`, created by `tara init`)

Tracked, shared working knowledge: `plan/`, `design/` (finalized ADRs move to
`docs/decisions/`), `review/`, `memory/` (handover notes).

- Name docs `YYYYMMDDHHMM_<short-title>.md`; keep each folder's `index.md`
  current (newest first) so the next session can scan instead of opening
  every file.
- Drop a short note in `memory/` at the end of each phase or hand-off.
- Never put secrets here; it is committed and shared by default (see
  `[agents] gitignore` in `.tara/config.toml` to keep a subfolder local).

## Definition of done

- [ ] New behaviour is covered by tests; `tara check` passes end to end.
- [ ] The increment runs: an integration test plus a runnable example.
- [ ] Docs updated for the change; changelog updated if user-facing.
- [ ] No secrets, credentials, or local config staged.
- [ ] Handover notes in `.agents/memory/` are current.

---

# Python Stack

`ruff` for lint and format, `ty` for types (never mypy), `pytest` for tests.
Docstring convention is set in `pyproject.toml` (google by default).

For code style, structure, error handling, configuration, data, and testing
conventions, see the `python-code-style` skill. For scaffolding a new package
or library, see the `structuring-python-packages` skill.
