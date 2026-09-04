---
name: design-problem-tests
description: >-
  Designs hidden submit tests for leet-hub problems in problems/*/tests.jsonl.
  Requires at least 20 hidden cases covering boundary and critical conditions.
  Use when writing 测试用例, tests.jsonl, 边界条件, 临界条件, adding a problem, or
  expanding submit tests (not the 2–3 statement examples used by 测试/运行).
---

# 设计提交测试用例

本仓库题目的测例在 `problems/<slug>/tests.jsonl`，一行一个 JSON，**没有**单独的测试集文件夹。

两类测例不要混：

| 用途 | `hidden` | 条数 | 内容 |
| --- | --- | --- | --- |
| 测试 / 运行（题面示例） | `false` | 2～3 | 与 `statement.md` 示例一致，给人看 |
| 提交 | `true` | **不少于 20** | 覆盖边界、临界、反例、规模；失败时网页不展示输入 |

用户说「测试」时指公开示例；用户说「提交测试用例」或「测试集」时指 `hidden: true` 的正式数据。

## 工作流程

1. 读 `statement.md` 的**约束**、保证（是否唯一解、可否重复使用同一元素）和示例。
2. 读 `signature.yaml`：`params` 顺序 = `args` 顺序；`compare` 决定 `expected` 是否允许乱序。
3. 先写 2～3 条 `hidden: false`，与题面示例逐字对应。
4. 再写 **≥ 20** 条 `hidden: true`。用下方清单勾选，缺一类就补一类，不要用重复数据凑数。
5. 用一份参考解（通常 Python）对全部行算出 `expected`，禁止手算大样例。
6. 确认每条都在约束内，且按题意 `expected` 唯一（或 `any_order` 下 multiset 唯一）。

## 提交测例覆盖清单（必须）

`n` 的含义见仓库 `rules/bank.md`（规模，不是 `nums[i]`）。口径与 `rules/tests.md` 一致。

针对本题约束勾选：

- [ ] `n` 与值域的最小值
- [ ] 值域端点 `±10^9`（可出现在 `n` 为 `100`～`5000` 的数组上）
- [ ] 临界：端点下标、相邻、阈值刚好命中
- [ ] 全相同、已排序、逆序
- [ ] 负数、零、正数（类型为数时）
- [ ] 重复值（题意涉及时）
- [ ] 解在开头、中间、结尾
- [ ] 常见错解：只看相邻、漏负数、错误双指针
- [ ] `n` 为 `100`～`5000`：题面长度上限 ≥ 5000 时，除下一条外的隐藏测例
- [ ] `n` = 题面规模上限：1～2 条
- [ ] 题面 `n` 上限为十几：全部 ≤ 该上限，1～2 条取上限
- [ ] 单个整数参数为 `10^9`：测该值，不生成长度为 `10^9` 的数组
- [ ] 布尔真与假；允许空结果则含空结果

不满 20 条时，在约束内组合上述维度，每条一个考察点。

## 还需要遵守的原则

1. **不越约束**。题面写 `2 <= n <= 10000` 就不要 `n = 1` 或 `n = 10001`。越界测的是驱动，不是用户解。
2. **公开与隐藏职责分离**。示例只放公开行；隐藏行不要复制示例。提交数据可以更狠、更大，但必须合法。
3. **期望值可判定**。不要出「多种合法输出却用 `compare: exact`」的题；下标集合用 `any_order`。浮点题约束小数精度，并与评测容差（约 `1e-6`）一致。
4. 题面长度上限 ≥ 5000 时：隐藏测例除 1～2 条取上限外，长度为 `100`～`5000`。上限为十几时全体不超过该上限。
5. **一条一个意图**。注释写在提交说明或 PR 里，不要写进 `tests.jsonl`（JSONL 无注释）。本地可用并列清单记下每条在测什么。
6. **参考解生成 expected**。改约束或签名后必须重跑生成，禁止只改 `args` 不改 `expected`。
7. **语言中立**。测例是 JSON，对 Python / C / C++ 同一份。避免依赖「整数溢出当 unsigned」或 Python 无限整数才对的数据；值域跟题面走，且 C 的 `int` 能表示（本站常规是 32 位有符号范围内）。
8. **C 可表示**。`List[int]` 不要用超过 32 位有符号的整数；字符串不要嵌 `\0`；返回数组题的 `expected` 长度要与题意一致。
9. **反作弊适度**。1～2 条取题面长度上限，其余打错解。
10. **时限匹配规模**。`time_limit_ms` 以取上限的那 1～2 条为准：正确复杂度 AC，劣一档 TLE。
11. **确定性**。同一输入永远同一 `expected`。不要把「任意一种合法方案」写死成某一个，除非题面指定字典序 / 最小下标等。
12. **JSONL 格式**。UTF-8，一行一个对象，行间无逗号，无尾逗号。`args` 是数组，`hidden` 必须是布尔。

## 写入格式

```json
{"args":[[2,7,11,15],9],"expected":[0,1],"hidden":false}
{"args":[[1,2,3,4,5,6,7,8,9,10],19],"expected":[8,9],"hidden":true}
```

完成后自检：公开行数 2～3；隐藏行数 ≥ 20；`hidden: true` 的失败不会在网页上露出 `args`。

## 详细对照

- 按题型展开的边界表：[reference.md](reference.md)
- 两数之和：20+ 条隐藏测例示例：[examples.md](examples.md)
- 题目文件约定：[docs/problems.md](../../../docs/problems.md)
