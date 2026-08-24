# Release process

This project publishes releases through GitHub. HACS uses the GitHub release tag and displays the GitHub release body to users, so every release needs manually written release notes.

Replace `X.Y.Z` in the commands below with the new version, including the leading `v` only where shown.

## 1. Inspect the unreleased changes

Start from an up-to-date, clean `main` branch:

```bash
git fetch origin --prune --tags
git switch main
git pull --ff-only origin main
git status --short --branch
gh release list --limit 5
PREVIOUS_TAG=$(gh release list --limit 1 --json tagName --jq '.[0].tagName')
git log --oneline "$PREVIOUS_TAG"..main
git diff --stat "$PREVIOUS_TAG"..main
gh pr list --state merged --base main --limit 20
```

Do not release with uncommitted changes. Review the merged PR descriptions and the actual diff. Release notes must describe the changes since the previous release, not merely the version-bump PR.

Choose the version from the user-visible changes:

- Patch, `X.Y.Z`, for compatible fixes and small changes.
- Minor, `X.Y.0`, for new compatible features.
- Major, `X.0.0`, for breaking changes.

Use the version requested by the maintainer if it differs from this guideline.

## 2. Prepare the release branch

Create a branch named after the release:

```bash
git switch -c release/vX.Y.Z
```

Update the project version in both authoritative locations:

- `pyproject.toml`
- `custom_components/huckleberry/manifest.json`

Keep the versions identical, then run `uv lock` to update the `huckleberry-homeassistant` package entry in `uv.lock`. Do not change the `huckleberry-api` dependency unless the release needs a new API version. If it changes, update both `pyproject.toml` and `custom_components/huckleberry/manifest.json` before running `uv lock`.

Check the version diff:

```bash
uv lock
git diff --check
git diff -- pyproject.toml custom_components/huckleberry/manifest.json uv.lock
uv lock --check
```

## 3. Run release verification

Run the same Python checks used by pull requests:

```bash
uv sync --locked --dev
uv run ruff check .
uv run ty check
uv run pytest
```

If `uv` is unavailable on the host and Docker is available, run them in an isolated container:

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e UV_PROJECT_ENVIRONMENT=/tmp/huckleberry-venv \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/astral-sh/uv:python3.14-bookworm \
  sh -c 'uv lock --check && uv sync --locked --dev && uv run ruff check . && uv run ty check && uv run pytest'
```

Stop if any check fails. Fix the failure and rerun the full verification command.

## 4. Open the release PR

Inspect the final diff before committing:

```bash
git status --short --branch
git diff --check
git diff
git log --oneline -10
```

Commit and push only the version files:

```bash
git add pyproject.toml custom_components/huckleberry/manifest.json uv.lock
git commit -m "Release vX.Y.Z"
git push -u origin release/vX.Y.Z
```

Create a PR titled `Release vX.Y.Z`. Its summary should name the user-facing release, followed by the exact checks and results from the local run. Apply the `unslop` skill to the title and body before creating it.

Example:

```markdown
## Summary

Bump the integration version to X.Y.Z for the <feature or fix> release.

## Verification

- `uv lock --check`
- `uv run ruff check .`
- `uv run ty check`
- `uv run pytest` (<result>)
```

Save the completed body to `/tmp/release-pr-vX.Y.Z.md`, then create the PR:

```bash
gh pr create \
  --base main \
  --head release/vX.Y.Z \
  --title "Release vX.Y.Z" \
  --body-file /tmp/release-pr-vX.Y.Z.md
```

## 5. Wait for PR validation and merge

Watch all PR checks, replacing `PR_NUMBER`:

```bash
gh pr checks PR_NUMBER --watch --interval 10
```

Do not merge while a check is pending, skipped unexpectedly, cancelled, or failed. The expected checks include tests, Ruff, Ty, hassfest, HACS, and any repository security checks.

After every reported check passes, merge using a merge commit and delete the remote branch:

```bash
gh pr merge PR_NUMBER --merge --delete-branch
gh pr view PR_NUMBER --json state,mergedAt,mergeCommit,url
git switch main
git pull --ff-only origin main
git status --short --branch
```

The release tag must point to the merge commit on `main`, not the release branch commit.

## 6. Write the HACS release notes

Write the notes manually. Do not use GitHub's generated notes as the user-facing body. Describe only changes since the previous release and use names that users see in Home Assistant.

Use this structure:

```markdown
## What's changed

<One sentence stating the main user-visible change.>

- <New behavior, entity, or service.>
- <Important options or supported values.>
- <Relevant matching, migration, or compatibility behavior.>

<Known limitation, if one matters.> No configuration changes or migration steps are required. After updating, reload the integration or restart Home Assistant to make the changes available.
```

Release notes should:

- Explain what users can now do, rather than listing commits or internal classes.
- Put service and entity IDs in backticks.
- Mention migration or configuration steps explicitly. If there are none, say so.
- Mention meaningful limitations without listing deferred implementation details that do not affect users.
- Avoid contributor workflow, test counts, PR numbers, and dependency details unless users need them.
- Use plain sentences and a short list. Apply the `unslop` skill before publishing.

Save the final body to a temporary Markdown file such as `/tmp/release-vX.Y.Z.md` so shell quoting cannot alter it.

## 7. Publish and verify the GitHub release

Read the merge commit SHA from the merged PR, then publish a non-draft, non-prerelease release:

```bash
MERGE_SHA=$(gh pr view PR_NUMBER --json mergeCommit --jq '.mergeCommit.oid')
gh release create vX.Y.Z \
  --target "$MERGE_SHA" \
  --title "vX.Y.Z" \
  --latest \
  --notes-file /tmp/release-vX.Y.Z.md
```

Verify the published body, target, and local tag:

```bash
gh release view vX.Y.Z \
  --json name,tagName,targetCommitish,body,url,isDraft,isPrerelease,publishedAt
git fetch --tags origin
git show-ref --tags vX.Y.Z
git status --short --branch
```

The release is complete only when:

- The release PR is merged and every PR check passed.
- The `vX.Y.Z` tag points to the PR merge commit on `main`.
- The GitHub release is published, not a draft or prerelease.
- The release body contains the reviewed manual notes that HACS users will see.
- The local worktree is clean on `main`.
