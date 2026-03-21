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

If `git push` is rejected because the remote has **old, unrelated history** (same situation as when this project replaced the previous `manim-hebrew-template` tree), overwrite `main` deliberately:

```bash
git push --force origin main
```

Use only when you intend to **replace** the GitHub branch entirely. `--force-with-lease` is safer if others might push between your fetch and push.

## Clone for others

```bash
git clone https://github.com/RanKiri93/manim-hebrew-template.git
```

They get **this** tooling (`hebrew_utils`, `tools/tex_line_codegen/`, `tools/hebrewmanim_mcp/`, etc.).
