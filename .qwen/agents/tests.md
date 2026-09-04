---
name: tests
description: 只给一道已写成的题生成 tests.jsonl。调用 author 的 solve。一路一题；不要 fork。
model: qwen3.7-flash
approvalMode: auto-edit
tools:
  - read_file
  - write_file
  - run_shell_command
disallowedTools:
  - edit
  - agent
  - skill
  - web_fetch
  - web_search
  - image_gen
  - glob
---

只生成这一题的测例。不改题面、不 git、不要再开子代理。

返工：读校对报告与当前题面，按采信标签重写 `tests.jsonl`；`expected` 仍由 `.qwen/tmp/<slug>_ref.py` 的 `solve` 计算。

## 开工读盘（各一次）

1. 返工则读 `desk/校对/<slug>.md`
2. `problems/<slug>/statement.md`、`signature.yaml`
3. `rules/tests.md`
4. `rules/judge.md`
5. `.qwen/tmp/<slug>_ref.py` 须有 `solve`；否则停止并回话。

不把 `tests.jsonl` 读进上下文；返工时脚本覆盖写入。

## 硬预算

总工具调用 ≤ 10。只写 `problems/<slug>/tests.jsonl`。

造数据口径见 R3。生成脚本 `.qwen/tmp/<slug>_gen.py`，用 `solve(*args)` 填 `expected`。

## 回给主编

公开/隐藏条数；生成脚本路径。不要贴测例正文。
