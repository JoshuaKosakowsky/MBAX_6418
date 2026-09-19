# AGENTS.md

Ground rules, conventions, and workflow standards for **any agent or collaborator** working in this repository, including AI coding agents (Hermes, Claude Code, GitHub Copilot, etc.). Read this file before making any change.

This is a **group project** for the course *MBAX 6418 — Building Business Solutions with Generative AI and LLMs*. The repo tracks projects and assignments. All work flows through **issues** and **pull requests** — never commit directly to the protected branch.

---

## 1. Core principles — "a good logic base"

1. **Ground every change in logic.** Before writing code, a commit, or a fix, state the *why*: the problem being solved, the approach, and how it will be verified.
2. **One concern per change.** Split work into small, logically coherent units (bug vs. feature vs. refactor vs. docs). If a change mixes concerns, split it into multiple commits/PRs.
3. **Prefer verifiable over assumable.** Always test your work before claiming it done. "Works" means a test (or real execution) confirms it, not that it looks reasonable.
4. **If unsure, ask or document the assumption.** Never silently guess. Label assumptions explicitly.
5. **Respect the repo's history and structure.** Follow the commit and testing standards below so teammates and tooling can operate on a clean, predictable history.

---

## 2. Git commit convention — Conventional Commits 1.0.0

All commit messages **MUST** follow the [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) specification.

### 2.1 Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### 2.2 Allowed types

- `feat:` — a new feature
- `fix:` — a bug fix
- `build:` — changes to build system or dependencies
- `chore:` — routine tasks / maintenance
- `ci:` — CI/CD configuration changes
- `docs:` — documentation only
- `style:` — formatting, whitespace, no logic change
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `perf:` — a performance improvement
- `test:` — adding or correcting tests
- `revert:` — reverting a previous commit

### 2.3 Rules

- **Type is REQUIRED** and must be a lowercase noun, followed by a **required** colon + space (`fix: `).
- **Optional scope** in parentheses after the type, e.g. `feat(parser):`, `fix(auth):`. Use a noun naming the module/area.
- **Optional `!`** before the `:` to mark a **BREAKING CHANGE**, e.g. `feat!: drop support for legacy exports`. Breaks map to a MAJOR version bump in SemVer.
- **Description** is required, must immediately follow `type: `, and is a short, imperative summary of the change.
- **Body** (optional) goes one blank line after the description, in free-form paragraphs explaining *why*.
- **Footers** (optional) go one blank line after the body, using the git-trailer convention (`Token: value` or `Token #value`), with `-` instead of spaces in tokens. Use `Refs: #123` to link an issue/PR.
- `BREAKING CHANGE:` (uppercase, required) as a footer, or the `!` marker, indicates a breaking change.

### 2.4 Examples

```
feat(agent): add end-to-end test harness for the sales pipeline

Introduces a Playwright-based flow covering the core user journey.

Refs: #12
```

```
fix: prevent racing requests in the report generator

Return the current request id so stale asynchronous responses are discarded.

Reviewed-by: team
```

```
docs: explain Conventional Commits workflow in CONTRIBUTING
```

```
feat!: migrate auth to federated SSO

BREAKING CHANGE: `API_KEY` env config is replaced by OIDC discovery.
```

### 2.5 Good commit hygiene

- **Never** use vague messages (`update`, `stuff`, `fix stuff`, `more changes`).
- **Split multi-concern changes** into separate commits/PRs.
- Describe **what and why**, not just what you typed.
- Keep the scope consistent with the branch/issue it addresses.
- Link the relevant issue in the footer (`Refs: #N`).

---

## 3. Git workflow — branching, issues, PRs

This repository is a **group project**; collaboration happens via **issues** and **pull requests**.

### 3.1 Issues

- **Create an issue for every new task, feature, or bug** before doing the work.
- Use a clear, searchable title (the Bugzilla-style summary — see §4).
- Fill in the issue template: context, acceptance criteria, steps to reproduce (for bugs), and proposed approach.
- Reference/close issues from commits and PRs by number (`Fixes #42`, `Refs #420`).

### 3.2 Branching

- **Never commit directly to `main`.** Work on a short-lived feature branch.
- One branch per issue/feature: `<type>/<short-description>`, e.g. `feat/test-harness`, `fix/duplicate-submission`, or just `issue-<N>-<short-slug>`.
- Keep branches short-lived and rebase on an up-to-date `main` before opening the PR.

### 3.3 Pull requests

- Open a PR for **every** merge into a shared branch.
- PR title uses the Conventional Commits type: `feat: / fix: / docs: …`.
- PR description: summary, why, test evidence, and links to the related issue (`Closes #N`).
- Keep PRs focused and small; preview PRs are preferred for reviewers.
- Squash-merge with a clean Conventional Commits message, or keep a tidy commit history — agree with the team on which.
- **Do not merge your own PR without a review** from at least one teammate (unless explicitly waived for a solo assignment).

---

## 4. Bug reporting — Bugzilla methodology

All bug reports (issues filed as bugs) **MUST** follow the [Mozilla Bugzilla Bug Writing Guidelines](https://bugzilla.mozilla.org/page.cgi?id=bug-writing.html): *one bug per report*, with a clear, unique summary and reproducible detail.

### 4.1 Issue title (summary)

A **clear, unique summary of ~10 words / one sentence** that lets a triager identify the report at a glance. Imperative, specific:

- ✅ `Fix drag-select crash when selecting large pages`
- ❌ `help` / `it broke` / `crash`

### 4.2 Body template for a bug

```markdown
**Overview**
One or two sentences restating the summary with enough detail to stand alone.

**Environment**
- Area/Component: e.g. `ai-agent`, `build`, `docs`
- Branch/Commit: the version or commit where it was observed
- Related issue/PR (if any): `#N`

**Steps to reproduce**
1. (First concrete step)
2. (Second concrete step)
3. `exact command or input used`

**Expected results**
What should have happened.

**Actual results**
What happened instead (include error text / logs).

**Additional information**
Anything unique: screenshots, stack traces, data, frequency (always / sometimes / only on X).
```

### 4.3 Rules

- **One issue per bug** — file separate reports for separate problems.
- Only report if you can reproduce, or give unique details about the occurrence.
- **Search for duplicates first** before filing.
- Test the latest version/branch before reporting (it may already be fixed).
- Prefer numbered steps to reproduce; make them precise enough for someone who has never seen your screen.
- Distinguish **Expected** from **Actual** results explicitly.
- Include environment/build info so similar-but-different bugs aren't conflated.

---

## 5. Testing strategy

All three levels of testing are used in this repo. Deliver them in proportion to the change and log evidence in the PR.

### 5.1 Unit tests

- Test individual functions/modules in isolation — the smallest unit.
- Run on every change to the code being unit-tested.
- Fast, deterministic, must run in CI on every push.

### 5.2 Smoke tests

- **Cheaper models are prioritized for smoke tests.** Always run the smoke suite with the cheapest/fastest available model first, because it catches obvious failures quickly and at low cost before any expensive run is spent.
- A smoke test verifies the critical path / core wiring works *at all* — a quick "does it boot, does the main flow run without error" check. It is **not** full-depth validation.
- Run smoke tests before deploying and before investing in slow or expensive end-to-end runs.

### 5.3 End-to-end (E2E) tests

- Test complete user journeys across the real integrated components.
- Run on the full, most capable setup — reserved for validating real scenarios after smoke tests pass.
- Second in cost, last in pipeline: only after unit tests (and smoke tests where applicable) are green.

### 5.4 Testing order & cost

| Level     | Scope             | Cost   | Run when                                   |
|-----------|-------------------|--------|--------------------------------------------|
| Unit      | smallest unit     | lowest | on every push to changed code              |
| Smoke     | core path/wiring  | low    | pre-deploy, before E2E — **use cheap models** |
| End-to-end| full journey      | highest| after unit + smoke pass                     |

- **Always** run the appropriate tests before opening/marking a PR ready; document the results in the PR description.
- Fix failures at the lowest-cost level before moving up; don't pay for an expensive run that a cheap one would have caught.

---

## 6. What the team expects

- Read `README.md` and this file before contributing.
- Default to **small, focused, well-tested changes** with clean Conventional Commits messages.
- Communicate the *why* in commit bodies and PR descriptions.
- When something is ambiguous, ask — or label the assumption explicitly.
