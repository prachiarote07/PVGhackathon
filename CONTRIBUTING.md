# Contribution checkpoints

Preserve the existing repository and use one local checkout. Never force-push, overwrite another member’s work, or commit credentials.

Before each checkpoint:

1. Inspect `git status --short`, `git diff`, and `git remote -v`.
2. Run the module's relevant checks. Frontend: `npm test`, `npm run build`, `npm run test:e2e` from `frontend/`.
3. Show all proposed new and changed files. Include shared files only when the member approves their ownership.
4. Stop for the named member's review and explicit commit/push authorization.
5. Check the configured author and authenticated GitHub account. Do not switch identities without that person's authorization. A module label alone does not establish authorship.
6. Stage only approved paths, review the staged diff, then commit and push only as authorized.
7. Verify the remote branch contains the exact approved commit.

Keep monetary fields in integer paise. Do not replace verified calculations with generated text. Label demo assumptions, consent and limitations. Add regression checks for monetary changes and avoid unnecessary dependencies.

The approved integration target is the existing `main` branch. Later module checkpoints must preserve earlier reviewed frontend code and replace the local reference adapter with the agreed backend API deliberately.
