# R5 · 落盘与 git

**读的人**：写盘或提交时。

出题机检走 MCP（服务器名 `leet`，实现在 `.qwen/tools/`）。`scripts/` 只给评测机。

| 行名 | 路径 | 谁写 |
|---|---|---|
| 题目 | `problems/<slug>/`（`meta.yaml`、`statement.md`、`signature.yaml`、`starter/`） | `author` 写题面与签名；`mcp__leet__fix_format` 改题面结构与示例排版、补 bounds、写 `starter/` |
| 已出题表 | `problems/catalog.md` | 主编 **commit 前** 调 `mcp__leet__write_catalog` |
| 参考解（oracle） | `.qwen/tmp/<slug>_ref.py`（`def solve(*args)`） | `oracle`；`dump` / `mcp__leet__fill_expected` 填 expected |
| 答题者解 | `.qwen/tmp/<slug>_solve2.py` | `solver`；`mcp__leet__check_tests` 对照 expected |
| 测例 | `problems/<slug>/tests.jsonl` | `tests` 写 args（`mcp__leet__run_gen`）；脚本写 expected |
| 质量 | `desk/质量/<slug>.md` | `quality`；不通过则不要派 tests/solver |
| 校对 | `desk/校对/<slug>.md` | 主编调 `mcp__leet__check_tests` 时由脚本写入 |
| 裁决 | `desk/裁决/<slug>.md` | `arbiter`；author 错则 `mcp__leet__fill_expected`（promote）并重填 expected |
| 机检 | `mcp__leet__check_tests` | **主编**调用 |
| 换题删稿 | `mcp__leet__drop_problem` | **主编**调用；删 `problems/<slug>/` 与 `.qwen/tmp/<slug>_*.py`；不动 catalog / desk / 其它 slug |
| 原创索引 | `index/clones.jsonl` | 人跑 `.qwen/tools/build_clones.py` 从仓外 doocs 题表生成；quality 只调 `mcp__leet__clone_check`，不读正文 |
| 题面机检 | `mcp__leet__statement_check` | `quality`：`skip_ref=true`；`oracle` 默认 `_ref.py`；`solver`：`ref=solve2`。主编仅兜底时 `skip_ref=true` |

`desk/` 与 `.qwen/tmp/` 不进 git。提交范围：校对通过的 `problems/<slug>/` 以及更新后的 `problems/catalog.md`。不要写 `desk/tmp-probe/` 或把假 ref 拷进 `desk/`。退回不 commit 则不要调 `mcp__leet__write_catalog`。换题用 `mcp__leet__drop_problem`，不要把废稿 `git add`。

## 写盘（Windows）

中文用 `write_file`（UTF-8）。只改任务 slug。

## git（主编）

1. `git status`、`git diff --stat`、`git log -5 --oneline`
2. `git add` 校对通过的 `problems/<slug>/`
3. 调 `mcp__leet__write_catalog`（`slug`）
4. `git add problems/catalog.md`
5. `git commit`
6. 不 `git push`，不改 git config，不用 `--no-verify`
