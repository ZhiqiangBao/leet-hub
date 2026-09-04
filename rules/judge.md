# R4 · 评测约束

**读的人**：`author`、`tests`、`proof`。

## 语言

Python 3；C：`gcc -std=gnu11`；C++20：`-std=c++20`，语言 id `cpp17`，starter 文件名 `cpp17.cpp`，界面显示 C++20。

JS / Go / Rust / Zig 为桩，提交 `NA`。

## 类型

`int`、`float`、`bool`、`str`、`List[int]`、`List[str]`。不要用 `List[List[int]]`（C 不支持）。

C：`List[int]` 参数 → `int* name, int nameSize`；返回 `List[int]` → 另加 `int* returnSize`，`malloc`。`str` → `char*`。`bool` → `bool`。

## 整数

测例与答案中的 `int` / `List[int]` 在 `[−2^{31}, 2^{31}−1]`。

## 行长度

C 单行缓冲 8MB（堆）。三语共用同一 jsonl。`n` 为数组长度 `10^5`、每个 `int` 约 10 位十进制时，一行约 1MB。`n` 从不表示「构造长度为 `10^9` 的数组」。

## 时限

`time_limit_ms` 以 `n` 取题面规模上限的那 1～2 条为准：正确复杂度 AC，劣一档 TLE。参考解须跑完全部测例。
