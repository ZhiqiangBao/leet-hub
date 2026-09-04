# R5 · 落盘与 git

**读的人**：写盘或提交时。

| 行名 | 路径 | 谁写 |
|---|---|---|
| 题目 | `problems/<slug>/`（`meta.yaml`、`statement.md`、`signature.yaml`、`starter/`） | `author` |
| 参考解（oracle） | `.qwen/tmp/<slug>_ref.py`（`def solve(*args)`） | `author`；`dump` / `fill_expected` 填 expected |
| 答题者解 | `.qwen/tmp/<slug>_solve2.py` | `solver`；`check.py` 对照 expected |
| 测例 | `problems/<slug>/tests.jsonl` | `tests` 写 args；脚本写 expected |
| 质量 | `desk/质量/<slug>.md` | `quality`；不通过则不要派 tests/solver |
| 校对 | `desk/校对/<slug>.md` | `proof` |
| 裁决 | `desk/裁决/<slug>.md` | `arbiter`；author 错则 `--promote` 并重填 expected |
| 机检 | `.qwen/skills/proof-tests/check.py` | `proof` 调用 |
| 题面机检 | `.qwen/skills/proof-tests/statement.py` | `quality` 调用 |

`desk/` 与 `.qwen/tmp/` 不进 git。提交范围：`problems/<slug>/`。禁止写 `desk/tmp-probe/` 或把假 ref 拷进 `desk/`。

## 写盘（Windows）

中文用 `write_file`（UTF-8）。不用 `echo`、`Set-Content`、`Out-File`。只改任务 slug。

## git（主编）

1. `git status`、`git diff`、`git log -5 --oneline`
2. `git add` 校对通过的 `problems/<slug>/`
3. `git commit`
4. 不 `git push`，不改 git config，不用 `--no-verify`
