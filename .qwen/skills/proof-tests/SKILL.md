---
name: proof-tests
description: >-
  仅 proof 子代理按命令跑 check.py。主编不要调用本 skill，不要打开 check.py。
disable-model-invocation: true
priority: 20
---

# 测例机检

不识题意、不改文件。不要把 jsonl 读进模型。

```powershell
python ".qwen/skills/proof-tests/check.py" --slug <slug>
```

默认 `--ref .qwen/tmp/<slug>_ref.py`、`--solver .qwen/tmp/<slug>_solve2.py`。缺 solver 则 fail-closed。JSON 只含计数与至多若干行号，不含 `args`。

题面机检（`quality` 在 tests 之前调用，不读 jsonl）：

```powershell
python ".qwen/skills/proof-tests/statement.py" --slug <slug>
```
