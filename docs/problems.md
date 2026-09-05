# 在磁盘上编写题目

题库真源是 Git 仓库中的 `problems/` 目录。推荐在能 `git push` 的电脑上改文件、推送到 https://github.com/ZhiqiangBao/leet-hub，再由评测主机拉取。也可直接在 Ubuntu 的克隆目录里改文件，但未推送的改动会在下次 `git pull` 时冲突或丢失。

样例：[`problems/two-sum/`](../problems/two-sum/)。

## 添加一道题

1. 选定 `slug`：只含小写字母、数字和连字符，例如 `two-sum`。目录名必须等于 slug。
2. 创建目录 `problems/<slug>/`，写入下表所列文件。
3. 提交并推送仓库。
4. 评测主机进入克隆目录后执行 `./scripts/update-from-github.sh`，或 `git pull` 后 `sudo systemctl restart local-leet`。管理员也可在网页「管理」中选择「从磁盘重新加载」。

不要只改 Ubuntu 本地磁盘却不推送，同时也不要一边用网页「管理」写盘、一边用 Git 改同一题。

## 目录结构

```text
problems/<slug>/
  meta.yaml
  statement.md
  signature.yaml
  tests.jsonl
  starter/
    python3.py
    c.c
    cpp17.cpp
    javascript.js
    typescript.ts
    go.go
    rust.rs
    zig.zig
```

| 文件 | 必填 | 说明 |
| --- | --- | --- |
| `meta.yaml` | 是 | 标题、难度、时限、内存、标签 |
| `statement.md` | 是 | 题面（Markdown），显示在题目页左侧 |
| `signature.yaml` | 是 | 类名、方法名、参数、返回类型、比较方式 |
| `tests.jsonl` | 是 | 测试集，一行一个 JSON |
| `starter/python3.py` | 建议 | 打开题目时 Python 编辑器的初始代码 |
| `starter/c.c` | 建议 | C 初始代码（力扣式自由函数） |
| `starter/cpp17.cpp` | 建议 | C++ 初始代码 |
| `starter/javascript.js` | 建议 | JavaScript 初始代码 |
| `starter/typescript.ts` | 建议 | TypeScript 初始代码 |

## meta.yaml

```yaml
slug: two-sum
title: 两数之和
difficulty: easy
time_limit_ms: 2000
memory_limit_mb: 256
tags:
  - array
  - hash
```

- `difficulty`：`easy`、`medium` 或 `hard`。
- `time_limit_ms`：用户程序运行时限（毫秒），建议 1000–5000。
- `memory_limit_mb`：运行内存上限（MB）。编译阶段不使用此值。
- `tags`：小写英文 id，1～3 个。题库页按知识点筛选；中文名在 `frontend/src/tags.ts`。

## statement.md

Markdown 题面。写清题意、输入含义（对应函数参数）、输出含义（对应返回值）、示例和约束。用户不读写标准输入，只实现函数。

## signature.yaml

评测机按此签名注入驱动并调用用户代码。

```yaml
class_name: Solution
method: twoSum
params:
  - name: nums
    type: List[int]
  - name: target
    type: int
return_type: List[int]
compare: any_order
```

- Python / C++：用户实现 `class Solution` 中的方法，方法名与 `method` 一致。
- C：力扣式自由函数，无 `class Solution`。`List[int]` / `List[long]` 参数展开为指针加长度（`int* nums, int numsSize` 或 `long long*`）；返回数组时再加 `int* returnSize`，返回值须 `malloc`。`str` 为 `char*`，`List[str]` 为 `char**` 加长度，`bool` 为 `bool`。yaml `long` 在 C/C++ 为 `long long`，Python 注解仍为 `int`。
- `params` 顺序必须与 `tests.jsonl` 里 `args` 的顺序一致。
- `compare`：`exact` 表示按结构逐位比较；`any_order` 表示顶层列表元素顺序无关（如下标数组）。

支持的 `type`：`int`、`long`、`float`、`bool`、`str`、以及嵌套的 `List[T]`（如 `List[int]`、`List[long]`、`List[str]`）。默认用 `int`；仅答案或参数会超 32 位有符号整数时用 `long`。C 不支持 `List[List[int]]`。链表、二叉树尚未支持。

## tests.jsonl

每行一个 JSON 对象，UTF-8，行与行之间不要逗号。

```json
{"args":[[2,7,11,15],9],"expected":[0,1],"hidden":false}
{"args":[[3,2,4],6],"expected":[1,2],"hidden":false}
{"args":[[1,2,3,4,5,6,7,8,9,10],19],"expected":[8,9],"hidden":true}
```

- `args`：参数列表，与 `signature.params` 一一对应。
- `expected`：期望返回值，类型与 `return_type` 一致。
- `hidden: false`：该测例失败时，网页展示输入、期望与实际输出。
- `hidden: true`：只提示第几号测例失败。正式数据放隐藏测例。

公开测例 2～3 条，与题面示例一致。提交用隐藏测例不少于 20 条，须覆盖边界与临界条件。写法见项目 skill [design-problem-tests](../.cursor/skills/design-problem-tests/SKILL.md)。

## starter

与力扣相同：只给出类/函数签名，函数体留空，不要写 `return {}`、`return false` 等占位返回值。由 `scripts/write-starters.py` 根据 `signature.yaml` 生成，不要手抄。Python 空缩进块是语法错误，提交空 starter 得到 `CE` 即可。

不要在用户代码里定义 `main`，否则与驱动中的 `main` 冲突，结果为 `CE`。

Python：

```python
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        
```

C（驱动已包含 `json.h`，其中有 `stdbool.h` / `stdlib.h`）：

```c
/**
 * Note: The returned array must be malloced, assume caller calls free().
 */
int* twoSum(int* nums, int numsSize, int target, int* returnSize) {
    
}
```

C++（驱动已包含 `<bits/stdc++.h>` 与 `using namespace std;`）：

```cpp
class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        
    }
};
```

## 在 Ubuntu 磁盘上直接改题

适用于临时改一题、且立刻要在本机生效：

```bash
cd ~/leet-hub          # 实际克隆路径
# 编辑 problems/<slug>/ 下文件
sudo systemctl restart local-leet
```

或管理员登录网页后点「从磁盘重新加载」。改完后若需与 GitHub 一致，在能推送的电脑上把同一改动提交并 `git push`。

网页「管理」写入的也是评测主机上的 `problems/`，效果与直接改磁盘相同，同样需要再推送到 GitHub 才能成为仓库真源。
