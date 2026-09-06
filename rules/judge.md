# R4 · 评测约束

**读的人**：`author`、`solver`、`quality`。

## 语言

Python 3；C：`gcc -std=gnu11`；C++20：`-std=c++20`，语言 id `cpp17`，starter 文件名 `cpp17.cpp`，界面显示 C++20。

JavaScript、TypeScript、Go、Rust、Zig 均可评测（主机须有对应编译器 / 运行时）。Zig 按 `zig version` 分派 0.14 / 0.16 驱动。

## 类型

`int`、`long`、`float`、`bool`、`str`、`List[int]`、`List[long]`、`List[str]`。不要用 `List[List[int]]`（C 不支持）。yaml 写 `long`，不要写 `long long` / `int64`。

| yaml | Python 注解 | C | C++ |
|---|---|---|---|
| `int` | `int` | `int` | `int` |
| `long` | `int` | `long long` | `long long` |
| `List[long]` | `list[int]` | `long long* name, int nameSize` | `vector<long long>` |

C：`List[int]` / `List[long]` 参数 → 指针加长度；返回数组 → 另加 `int* returnSize`，`malloc`。`str` → `char*`。`bool` → `bool`。

## 整数

**默认 `int`，绝大多数题走 int32** `[−2^{31}, 2^{31}−1]`。不要每题都用 `long`。

仅当某个返回值或参数的闭式上界会超 `2^{31}−1`、且需要保留该规模时，**只把那个字段**改成 `long`（`[−2^{63}, 2^{63}−1]`）。能收窄约束仍进 int32 的，优先收窄，不要升位宽。

定约束前先估算上界。题面写清范围。不要写「请用能容纳的整型」却不改签名。选题时算清：收窄会不会把 `n` 锁死到没法考复杂度。

## 行长度

C 单行缓冲 8MB（堆）。三语共用同一 jsonl。`n` 为数组长度 `10^5`、每个 `int` 约 10 位十进制时，一行约 1MB。`n` 从不表示「构造长度为 `10^9` 的数组」。

## 时限

`time_limit_ms` 以 `n` 取题面规模上限的那 1～2 条为准：正确复杂度 AC，劣一档 TLE。参考解须跑完全部测例。
