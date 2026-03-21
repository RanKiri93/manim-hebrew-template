# GitHub: [RanKiri93/manim-hebrew-template](https://github.com/RanKiri93/manim-hebrew-template)

**This local project is the canonical codebase** for that repository. An older version of the repo existed before; it is **not** pulled or merged here — the history on GitHub may be replaced by pushing this tree.

## Do not pull the old remote history

There is **no** `template` remote and no expectation to `git pull` old commits. Work from this folder only.

## Push this project to GitHub

1. Commit any changes you need locally.
2. Push (first time):

```bash
git push -u origin main
```

If the remote still has unrelated history and you intend to **replace** the default branch with this project (destructive on GitHub):

```bash
git push --force-with-lease origin main
```

Use `--force-with-lease` only when you are sure you want to overwrite `main` on GitHub. Prefer coordinating with anyone else who uses the repo.

## Clone for others

```bash
git clone https://github.com/RanKiri93/manim-hebrew-template.git
```

They get **this** tooling (`hebrew_utils`, `tools/tex_line_codegen/`, `tools/hebrewmanim_mcp/`, etc.).
