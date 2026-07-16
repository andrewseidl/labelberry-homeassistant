# Agent instructions

This is the public Home Assistant integration repository for LabelBerry:
`https://github.com/andrewseidl/labelberry-homeassistant`.

## Repository access

- The canonical GitHub repository is `andrewseidl/labelberry-homeassistant`.
- Write access is available through the authenticated GitHub CLI (`gh`) and the HTTPS
  Git credential helper used by this checkout.
- The SSH key `~/.ssh/agents-labelberry` is scoped to the original
  `andrewseidl/labelberry` repository, not this repository.
- Push small, verified checkpoints frequently. Do not leave completed work only in a
  local branch.
- Use a Git worktree for isolated feature work when the main checkout is occupied.

## Working agreement

- Follow test-driven development for behavior changes: add a focused failing test,
  confirm the expected failure, implement the smallest change, then run the focused and
  full suites.
- Keep the integration domain and package name `labelberry`.
- Do not add `strings.json`; custom-integration localization belongs in
  `custom_components/labelberry/translations/en.json`.
- Never retry a print mutation automatically. Retries can create duplicate labels.
- Preserve multiline text and Unicode flank values exactly when forwarding requests.

Before pushing, run:

```sh
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest
git diff --check
```
