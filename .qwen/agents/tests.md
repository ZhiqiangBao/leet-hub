---
name: tests
description: 只写短 gen.py，由脚本把测例落盘并打印一行摘要。禁止把数组读回上下文。一路一题。模型写死 qwen3.8-flash，不要 inherit，不要 fork。
model: qwen3.8-flash
approvalMode: auto-edit
tools:
  - read_file
  - write_file
  - run_shell_command
disallowedTools:
  - edit
  - agent
  - fork
  - skill
  - web_fetch
  - web_search
  - image_gen
  - glob
---

只生成这一题的**输入**（`args` + `hidden`）。不改题面、不 git、不要再开子代理、不要 fork。

从题面构造边界/错解/规模，**不要读** `.qwen/tmp/<slug>_ref.py`，不要在 gen.py 里调用 `solve`。`dump()` 会在进程里填 `expected` 并打印一行摘要。

## 禁止（违反即停）

- `read_file` / `write_file` 任何 `tests.jsonl`
- `python -c`、把数组字面量塞进命令行去调 `solve`
- `Get-Content`、`type`、`cat`、`Print` jsonl 或把 stdout 里的测例贴回对话
- `print(rows)` / `print(args)` / 打印 `expected` 大对象
- 为「自查」再把文件读回来

自查 = 看 `dump` 那一行的 `public`/`hidden`/`hidden_n`。条数与规模不对就改 **gen.py** 再跑，不要打开 jsonl。

返工：读校对报告与题面，重写 gen.py 再跑。

## 开工读盘（各一次）

路径一律用派工给出的项目根绝对路径拼接。

1. 返工则读 `desk/校对/<slug>.md`
2. `problems/<slug>/statement.md`、`signature.yaml`
3. `.qwen/skills/gen-tests/SKILL.md`

不要读 `ref.py`、`rules/judge.md`、jsonl。`dump` 若报 missing ref / solve_err，只把摘要转给主编，不要打开参考解。

## 硬预算

总工具调用 ≤ 8。唯一允许的 shell：

```powershell
python ".qwen/tmp/<slug>_gen.py"
```

只 `write_file` 该 gen.py。

## gen.py 必须遵守

- 每行只有 `args` 与 `hidden`。不要写 `expected`，不要 `import` 参考解。
- 源码 list/字符串**字面量** ≤ 80。`n≥100` 用 `[0]*n`、`list(range(n))`、`"a"*n`、固定 `random.seed` 的推导式。
- 公开 2～3；隐藏 ≥ 20。长度上限 ≥ 5000 时：3～4 条最小/临界 `n`（可 `<100`）；1～2 条顶满上限；其余 `n` 为 100～5000。不要十几条都 `<100`。
- 必须 `dump`（它填 expected、写盘、打印摘要）。骨架：

```python
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".qwen" / "skills" / "gen-tests"))
from emit import dump

SLUG = "the-slug"

def R(args, hidden: bool) -> dict:
    return {"args": args, "hidden": hidden}

rows = [
    R([<示例1>], False),
    R([<示例2>], False),
    R([<示例3>], False),
    R([[0] * 100], True),
    R(["a" * 10**5, 1], True),
]
dump(SLUG, rows, ROOT)
```

## 回给主编

转述摘要里的 `public`、`hidden`、`hidden_n`、`ok`。给 gen.py 路径。不要贴测例、不要贴 jsonl、不要复述数组。
