# R3 · 测试用例

**读的人**：主编调 `mcp__leet__check_tests`（`tests` 读本规则口径；构造手法写在 `.qwen/agents/tests.md`）。

`n` 的含义见 R1（规模 = 长度或要展开的个数，**不是** `nums[i]`）。

测例文件：`problems/<slug>/tests.jsonl`，一行一个 JSON。

## 两类

| `hidden` | 条数 | 内容 |
| --- | --- | --- |
| `false` | 2～3 | 与 `statement.md` 示例一致 |
| `true` | ≥ 20 | 边界、临界、反例；失败时网页不展示输入 |

## 覆盖（均须落在本题约束内）

- `n` 与值域的最小值（长度下界、元素 `0` / 最小负数等）
- 值域端点 `±10^9`（可出现在 `n` 为 `100`～`5000` 的数组上）
- 临界：端点下标、相邻、阈值刚好命中
- 全相同、已排序、逆序
- 负数、零、正数（类型为数时）
- 重复值（题意涉及时）
- 解在开头、中间、结尾
- 常见错解：只看相邻、漏负数、错误双指针
- 1～2 条顶满 **meta.yaml 的 `n_max`**（不必是 `10^5`）。长度上限 ≥ 5000 时，其余隐藏大致：3～4 条最小/临界 `n`（可 `<100`）；剩下的 `n` 为 `100`～`5000`。`dump` / `mcp__leet__check_tests` 把 `lt100`/`missing_at_max`/`n_max_ne_U`/`out_of_bounds` 算进 `ok`，不要让模型看直方图。`out_of_bounds` 会带参数名与 got/min/max。`dump` 的 `overlay` 为 true 时，测例是按 dump kwargs 而不是盘上 `meta.yaml` 生成的，校对仍只认 meta。
- 题面 `n` 上限本身为十几：全部测例的 `n` ≤ 该上限，其中 1～2 条取上限
- 单个整数参数为 `10^9`：测该值，不生成长度为 `10^9` 的数组
- 布尔真与假；允许空结果则含空结果

`examples_parsed == examples_n` 只说明捕到了示例块，**不**代表已按 `signature.yaml` 绑定成功。`issues` 含 `cannot bind` 就是绑不上（即使 skip_ref 看起来 parsed 齐全）。带 ref 时看 `import_error` / `call_error` / `value_mismatch`，不要只看 `ref_example_mismatch`。三例全中且无 traceback 时先查示例区排版（R2），不要先动 ref。

## 原则

1. 不越题面约束。
2. 公开行即示例；隐藏行不复制示例。
3. 多种合法输出不用 `compare: exact`；下标集合用 `any_order`。
4. `expected` 由 `dump()` 调用磁盘上的 `solve` 填写。`tests` 模型只造 `args`，不读参考解、不手算大样例。改约束后重写 gen.py 再调 `mcp__leet__run_gen`。
5. JSONL：UTF-8，一行一个对象，`args` 为数组，`hidden` 为布尔。
6. 整数按签名通道（R4）：**默认 int32**。`int` / `List[int]` 落 int32；仅 `long` / `List[long]` 可到 int64。不要把 int 题的答案做成超 int32。字符串不含 `\0`。
7. 一行一个考察点。jsonl 无注释。

## 模型输出（只落盘、只回报摘要）

`tests` 不准把 `tests.jsonl` 读进对话。只写短 `gen.py`，调 `mcp__leet__run_gen` 看一行指标。

## 格式

```json
{"args":[[2,7,11,15],9],"expected":[0,1],"hidden":false}
{"args":[[1,2,3,4,5,6,7,8,9,10],19],"expected":[8,9],"hidden":true}
```
