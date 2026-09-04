# R2 · 题目文件

**读的人**：`author`。

## 目录

`author` 写：

```text
problems/<slug>/
  meta.yaml
  statement.md
  signature.yaml
  starter/python3.py
  starter/c.c
  starter/cpp17.cpp
```

`tests.jsonl` 由 `tests` 写，`author` 不创建、不修改。不必写 JS / Go / Rust / Zig starter。

## meta.yaml

`slug`、`title`（中文）、`difficulty`、`time_limit_ms`（1000–5000，默认 2000）、`memory_limit_mb`（默认 256）、`tags`。

## statement.md

题意、参数、返回值、2～3 个示例、约束。不要要求从标准输入读入。

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

`params` 顺序与 `tests.jsonl` 的 `args` 一致。类型见 R4。

## starter

空函数体。禁止 `main`、禁止占位 `return`。

Python：

```python
class Solution:
    def method(self, ...) -> ...:
        
```

C（`List[int]` 参数展开为指针加长度；返回 `List[int]` 时加 `int* returnSize`，返回值 `malloc`）：

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
