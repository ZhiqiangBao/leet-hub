# R2 · 题目文件

**读的人**：`author`、`quality`。

## 目录

`author` 写：

```text
problems/<slug>/
  meta.yaml
  statement.md
  signature.yaml
  starter/          # 不要手写；调 mcp__leet__fix_format
```

不要创建或修改 `tests.jsonl`。starter 一律由 `mcp__leet__fix_format` 生成（含 JS / TS / Go / Rust / Zig），不要手写。

`problems/catalog.md` 是已出题表（slug、标题、tags、签名）。对照此表即可。

## meta.yaml

`slug`、`title`（中文）、`difficulty`、`time_limit_ms`（1000–5000，默认 2000）、`memory_limit_mb`（默认 256）、`tags`。

规模与值域（`dump` / `mcp__leet__check_tests` 读这些，不解析题面 Markdown）。缺省：`n_min=1`、`n_max=100000`、`elem_min=-10^9`、`elem_max=10^9`。long 题把 `elem_max` 提到 int64，或加 `param_bounds`（嵌套与扁平都认；认不出的键会报 issue，不会静默用别的参数的界）。

```yaml
n_min: 1
n_max: 100000
elem_min: -1000000000
elem_max: 1000000000
param_bounds:
  hi:
    min: 1
    max: 2000000
# 扁平也可以：param_bounds: {hi_min: 1, hi_max: 2000000}
```

## 示例改写

排版由 `mcp__leet__fix_format` 改，模型不要背模板。写完调 `mcp__leet__fix_format`（参数 `slug`）。不要 `run_shell_command`。

工具会把题面收成网页同一套结构：`## 题目描述` / `## 题意` 只去掉标题、保留正文；整节删掉「参数 / 返回值 / 输入格式」等多余小节；示例编号为 `### 示例 N`；拆掉包住整段示例或单独包住输入/输出值的代码围栏、统一全角冒号与硬换行、值同行，把 `nums = [1,3,2,4], hi = 5` 改成位置参数 `[1, 3, 2, 4], 5`，并生成 starter、补上缺的 bounds 字段。返回 JSON 含 `examples.edits`（第几条、input/layout、是否 kv_to_positional）与 `bounds_notes`。改写后的题面形如：

```text
# 中文标题

题意段落

## 示例

### 示例 1

输入：...
输出：...
解释：...

## 约束
```

## statement.md

首行必须是 `# <中文标题>`（与 `meta.yaml` 的 `title` 一致）。题意写成段落，不要单独开「参数」「返回值」「输入格式」小节。然后是 2～3 个示例、约束。不要要求从标准输入读入。不要把参考解或 `def solve` 写进题面。

示例解释只说明这个输出为什么对（哪些计入、哪些不计入）。不要写算法步骤（排序怎么配、指针怎么移、DP、容斥公式）。约束必须写 `n` 与值域（和力扣一样）。不要写「int32 通道」等评测黑话。配对/使用次数按下标说，不要和下标限制叠一句「元素只能用一次」。

每个示例写出「输入 / 输出 / 解释」三行即可（半角冒号、围栏、反引号都可以，交给 `mcp__leet__fix_format`）。`mcp__leet__statement_check` 按改写后的 `输入：` / `输出：` 取期望值。

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

`params` 顺序即函数参数顺序。类型见 R4。默认 `int`；只有会超 int32 的字段才写成 `long`。

## starter

空函数体。禁止占位 `return`，禁止再写 `func main` / `int main`（Go 模板里的 `package main` 要保留）。**不要手写**：由 `mcp__leet__fix_format` 生成。不要把生成结果贴进对话。

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
