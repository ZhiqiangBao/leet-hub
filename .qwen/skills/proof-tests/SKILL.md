---
name: proof-tests
description: 机检一道题的 tests.jsonl（条数、int32、行长、与 tmp 参考解是否一致）。由 proof 调用；主编不要 read_file jsonl。
priority: 20
---

# 测例机检

不识题意、不改文件。判定语义（示例是否对得上题面、R3 清单缺什么）仍由 `proof` 看 `statement.md` 与本脚本的 JSON。

```powershell
python ".qwen/skills/proof-tests/check.py" --slug <slug>
```

可选 `--ref .qwen/tmp/<slug>_ref.py`（默认就是这个路径）。参考解必须提供 `solve(*args)`。
