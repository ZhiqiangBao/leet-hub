# 后续改进方向

本文记录希望做成的能力，以及和现状的差距。实现时按条目拆开做，不一次改完。

当前已有：登录、题库（搜索 / 难度 / 知识点筛选）、做题页、Python / C / C++20 / JavaScript / TypeScript 评测、测试（只跑公开示例）与提交分开、草稿、个人提交记录与成绩排行、管理员统计与全站提交、管理员网页增题、题面 `$…$` KaTeX、整站浅色 / 深色背景切换。签名默认 `int`（int32），少数字段用 `long`。题库真源仍是 GitHub 的 `problems/`。出题走 Qwen 流水线（`QWEN.md`），不要复制力扣原题。

## 1. 提交数据、排行与后台

已实现，不再排期。

- 管理员「管理」页：全站计数、各题提交/AC、提交表（可看源码）。`/admin/problems` 增题。不在网页上改别人密码、不删账号。
- 用户「提交记录」「成绩」：各题各语言最好一次 `AC` 的 `time_ms` 与名次。题目页：当前语言排行榜。未 `AC` 不进榜。
- 测试运行不写库，不进榜、不改已通过。

`time_ms` 仍是整次运行墙钟时间，不是从源码推断的 `O(n)`。

## 2. 持续增加题库

### 现状

已有 11 题（3 道种子题 + 后续原创题）。出题流程见 [problems.md](problems.md)。种子题隐藏测例已扩到 ≥20。后续原创题继续按词表加。

### 做法

- 在能 `git push` 的电脑上新增 `problems/<slug>/`，推送后评测主机 `bash scripts/update-from-github.sh`。
- 每题至少：题面、签名、公开测例 2～3 条（`hidden: false`）、不少于 20 条隐藏测例（`hidden: true`）。starter 用 `scripts/write-starters.py` 从签名生成（含尚未可评测的 Go / Rust / Zig 空模板）。
- 签名与力扣一致，便于对照；C 按自由函数展开（指针 + 长度 / `returnSize`）。
- 网页「管理」只作应急。不要 Ubuntu 改盘与 GitHub 同时改同一题。

建议顺序：数组 / 哈希 / 栈 / 双指针 / 字符串的 easy，再补 medium。语言适配器不阻塞加题。

## 3. 「测试」与「提交」分开

已实现。题目页两个按钮：

| 按钮 | 跑哪些测例 | 是否写入成绩 | 失败时展示 |
| --- | --- | --- | --- |
| 测试 | 仅 `hidden: false`（题面示例） | 否 | 每条的输入、期望、实际输出 |
| 提交 | 全部测例 | 是 | 与原来相同，隐藏测例只给序号 |

## 4. 题面公式与主题

已实现，不再排期。

- 题面 Markdown 中 `$…$` / `$$…$$` 用 KaTeX 渲染。
- 整站浅色 / 深色可切换（含编辑器），选择记在浏览器本地。

## 5. 其余语言适配器

可评测：Python 3、C、C++20、JavaScript、TypeScript。Go / Rust / Zig 仍是桩，提交为 `NA`。写法见 [adapters.md](adapters.md)；主机装工具链见 [server.md](server.md)。

计划接入（评测机 Ubuntu x64；压缩包体积如下，解压后更大）：

| 语言 | 工具链 | 安装体积（约） | 说明 |
| --- | --- | --- | --- |
| JavaScript（`javascript`） | Node.js | linux-x64 `.tar.xz` **34 MB** | **已接入。** `node --check` / `node solution.js`，标准库 `JSON`，禁止 npm 包。 |
| TypeScript（`typescript`） | 同上 Node + `tsc` | `typescript` npm 包几十 MB | **已接入。** 官方 `tsc` 跑在 Node 上。`sudo npm install -g typescript`。`tsc` 编成 JS 再 `node` 跑。与 JS 共用 Node。不要 Bun / Deno。 |
| Go（`go`） | `go` | `linux-amd64.tar.gz` **64 MB** | 已有桩。`GOPROXY=off`，标准库 `encoding/json`。 |
| Zig（`zig`） | 官方 tarball | **0.16.0** linux x86_64 **53MiB** | 已有桩。以评测机上的 Zig 版本写 `std.json`。 |
| Rust（`rust`） | `rustup` **minimal** | 约 **200–300 MB** | 已有桩。只要 `rustc`，不要 docs / clippy。JSON 用内置小型解析，禁止 `cargo add`。 |

TypeScript 接口与 JS 对齐：`class Solution { method(...) { ... } }`，语言 id `typescript`，源文件 `solution.ts`。

建议实现顺序：Go → Zig → Rust（磁盘最大）。每接入一种：适配器 `implemented = True`、主机安装编译器、`GET /api/languages` 该项可用、两数之和 AC/WA 各一次。各题空 starter 已由 `write-starters.py` 生成，不必再手补。

## 不做或后置

- 用静态分析给代码打 `O(n)` 标签再排名。
- 把网页管理当成题库真源。
- 公开全站任意用户源码给普通用户（管理员后台除外）。
- Rust `default` 工具链（含 docs，500 MB 以上）。
- 用 Bun / Deno 代替 `tsc`+`node` 跑 TypeScript。

## 尚未完成

- 按词表继续加原创题（隐藏测例 ≥20）。
- Go / Rust / Zig 做成可评测语言（把桩做成真适配器。starter 已有）。
- 仓库仍为公开；SSH 已通，随时可改私密。

## 建议实现顺序

1. 按词表加题，隐藏测例不少于 20 条。
2. Go、Zig、Rust 适配器（按磁盘与工作量）。
