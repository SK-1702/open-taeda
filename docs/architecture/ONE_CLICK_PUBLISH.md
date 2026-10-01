# One-Click Publication

Open TAEDA uses a two-step trust model: configure the GitHub remote once, then publish validated research state with one command.

## One-time setup

```bash
git init
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git add .
git commit -m "initial Open TAEDA v0.1 platform"
git push -u origin main
```

Authentication should be handled by Git Credential Manager, SSH, or the GitHub CLI. Never put a GitHub token in the repository or experiment manifests.

## Every subsequent publication

```bash
ota publish --push
```

The command:

1. validates experiment manifests;
2. rebuilds/validates the local research database;
3. shows the repository state;
4. stages changes;
5. creates a publication commit if needed;
6. pushes to the configured Git remote;
7. lets GitHub Actions perform the server-side validation.

For a safe dry run:

```bash
ota publish
```

The v0.1 publisher deliberately refuses to force-push or rewrite history.
