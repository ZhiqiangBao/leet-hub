# R2 · 题目文件

**读的人**：`author`、`quality`。

## 目录

`author` 写：

```text
problems/<slug>/
  meta.yaml
  statement.md
  signature.yaml
  starter/          # 不要手写；跑 scripts/write-starters.py
```

`tests.jsonl` 由 `tests` 写，`author` 不创建、不修改。不必手写 JS / Go / Rust / Zig starter（脚本加 `--all` 才会生成）。

## meta.yaml

`slug`、`title`（中文）、`difficulty`、`time_limit_ms`（1000–5000，默认 2000）、`memory_limit_mb`（默认 256）、`tags`。

## statement.md

首行必须是 `# <中文标题>`（与 `meta.yaml` 的 `title` 一致）。题意、参数、返回值、2～3 个示例、约束。不要要求从标准输入读入。不要把参考解或 `def solve` 写进题面。

### 示例区排版（机检契约）

`statement.py` 用 `输入[:：]\s*(.*?)\s*输出[:：]\s*([^\n]+)` 取期望值。排版不对时会报 `ref_example_mismatch`（看起来像 ref 算错，其实是期望值没被读到）。每个示例必须写成：

**示例 1**

```
输入：s = "aabbccc", k = 2
输出：2
解释：……一行纯文本……
```

- `输入：` / `输出：` / `解释：` 各占一行，全角冒号，值紧跟冒号同一行；
- 这三行不得包在 `**…**` 里，不得用反引号包裹值，不得把值单独放到下一行或代码围栏里；
- 题面其他区域可用 LaTeX；只有示例代码围栏内要求纯文本。

## signature.yaml

```yaml
class_name: Solution
method: <驼峰方法名>
params:
  - name: <参数名>
    type: <类型>
return_type: <类型>
compare: exact   # 下标集合无序时用 any_order
```

`params` 顺序与 `tests.jsonl` 的 `args` 一致。类型见 R4。默认 `int`；只有会超 int32 的字段才写成 `long`。

## starter

空函数体。禁止 `main`、禁止占位 `return`。**不要手写**：`signature.yaml` 落盘后执行

```powershell
python "scripts/write-starters.py" --slug <slug>
```

默认生成 `starter/python3.py`、`starter/c.c`、`starter/cpp17.cpp`。改签名后重跑。不要把生成结果贴进对话。

生成形态如下（供对照，不是让你手抄）：

Python：

```python
class Solution:
    def method(self, ...) -> ...:
        
```

C（`List[int]` / `List[long]` 参数展开为指针加长度；返回数组时加 `int* returnSize`，返回值 `malloc`。yaml `long` → `long long`）：

```c
int method(...) {
    
}
```

C++（语言 id `cpp17`，文件名 `starter/cpp17.cpp`，标准见 R4）：

```cpp
class Solution {
public:
    ... method(...) {
        
    }
};
```
