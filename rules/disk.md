# R5 · 落盘与 git

**读的人**：写盘或提交时。

| 行名 | 路径 | 谁写 |
|---|---|---|
| 题目 | `problems/<slug>/`（`meta.yaml`、`statement.md`、`signature.yaml`、`starter/`） | `author` |
| 参考解 | `.qwen/tmp/<slug>_ref.py`（`def solve(*args)`） | `author`；`tests` / `proof` 调用 |
| 测例 | `problems/<slug>/tests.jsonl` | `tests` |
| 校对 | `desk/校对/<slug>.md` | `proof` |
| 机检 | `.qwen/skills/proof-tests/check.py` | `proof` 调用 |

`desk/` 与 `.qwen/tmp/` 不进 git。提交范围：`problems/<slug>/`。

## 写盘（Windows）

中文用 `write_file`（UTF-8）。不用 `echo`、`Set-Content`、`Out-File`。只改任务 slug。

## git（主编）

1. `git status`、`git diff`、`git log -5 --oneline`
2. `git add` 校对通过的 `problems/<slug>/`
3. `git commit`
4. 不 `git push`，不改 git config，不用 `--no-verify`
