# GitHub publishing guide

Recommended repository name: `TetrisBattle-Educational`.

The complete archive may include original-era Flash-derived sounds or art for which redistribution rights are unconfirmed. **Publish it privately unless you have the necessary rights.** The code-only package excludes those extracted media files, but you should still review any upstream bundled graphics and sounds before making it public.

## GitHub CLI

Install [Git](https://git-scm.com/downloads) and [GitHub CLI](https://cli.github.com/). From the extracted project root:

```powershell
gh auth login
powershell -ExecutionPolicy Bypass -File .\tools\publish_github.ps1 -Repo "TetrisBattle-Educational" -Visibility private
```

Only select `-Visibility public` after reviewing rights and public release packaging. The script does not upload anything until you execute it.

## Manual Git commands

Create a **blank private** repository at [github.com/new](https://github.com/new) and run:

```bash
git init
git branch -M main
git add .
git commit -m "Prepare TetrisBattle educational edition"
git remote add origin https://github.com/YOUR_USERNAME/TetrisBattle-Educational.git
git push -u origin main
```

Check `.gitignore`, confirm `README.md`, `CHANGELOG.md`, `NOTICE.md`, `LICENSE` and the correct GIFs appear, and never commit personal tokens or credentials.
