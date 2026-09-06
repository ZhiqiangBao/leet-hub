# 评测主机工具链

面向家里那台 **Ubuntu 26.04 LTS**。答题端不用装这些。

已在 26.04 上核对过的版本：

| 命令 | 版本 |
| --- | --- |
| `go version` | `go1.26.0 linux/amd64` |
| `rustc --version` | `rustc 1.93.1` |
| `zig version` | `0.14.1` |

Zig 适配器按 **0.14.x** 编写（26.04 里 `apt install zig` 默认就是 0.14）。不要换成 0.15 / 0.16，标准库 JSON / IO 对不上会 CE。

## 26.04：一条 apt

`zig` 在 universe 源。桌面版一般已经打开。

```bash
sudo apt update
sudo apt install golang-go rustc zig
go version
rustc --version
zig version
```

应出现在 `/usr/bin`，systemd 服务 `local-leet` 能直接找到。装完后：

```bash
sudo systemctl restart local-leet
```

打开 `GET /api/languages`，`go` / `rust` / `zig` 的 `available` 应为 true。

首次部署用仓库里的 `./scripts/setup-ubuntu.sh`，其中已包含这三个包。

## 低版本 Ubuntu

语言适配器已经进 Git，**编译器仍要本机有**。版本差太多时按下面处理，不要为了追新去装 0.16 的 Zig。

### 先看缺什么

```bash
go version
rustc --version
zig version
```

网页语言下拉框灰色、提交 `NA`、接口文案「未安装编译器」，就是评测进程找不到对应二进制。

### Go

`sudo apt install golang-go` 在旧版 Ubuntu 也有。Go 1.22 及以上即可（模块、`any`）。apt 更旧时：

1. 仍先试 `golang-go`，能编过 `scripts/selftest.py` 里的 Go 用例就不用换。
2. 不行再装官方包（不是本仓库源码站）：<https://go.dev/dl/> ，解压到 `/usr/local/go`，保证 `/usr/local/go/bin/go` 存在。适配器会找 `/usr/bin/go` 与 `/usr/local/go/bin/go`。

评测设置了 `GOPROXY=off`，不要 `go get`。

### Rust

优先 `sudo apt install rustc`。只要 `rustc` 能编 edition 2021 即可，**不要**为评测装 rustup default（带 docs，体积大）。

找不到 `/usr/bin/rustc` 时（例如只装了 rustup 且 systemd 没有 `~/.cargo/bin`）：

```bash
sudo ln -sf "$HOME/.cargo/bin/rustc" /usr/local/bin/rustc
sudo systemctl restart local-leet
```

禁止判题时 `cargo add`。JSON 用仓库内置小解析器。

### Zig（最容易踩版本）

官方 Ubuntu 源从 **25.10** 才有 `zig` 包。26.04 默认 `zig` → **0.14.1**。适配器只按 0.14 写。

| 情况 | 做法 |
| --- | --- |
| 26.04，`zig version` 为 0.14.x | 不用改 |
| 26.04，误装了 0.15 包 | `sudo apt install zig0.14`，确认 `which zig` 指向 0.14；必要时 `sudo apt install zig`（defaults 指向 0.14） |
| 25.10 | `sudo apt install zig`，确认是 0.14 |
| **25.04 及更早**，仓库里没有 `zig` | **不要** `snap install zig` 去追最新稳定版（常为 0.15/0.16）。从 [ziglang.org/download](https://ziglang.org/download/) 下载 **0.14.1** 的 `zig-x86_64-linux-0.14.1.tar.xz`，解压后把 `zig` 放到 `/usr/local/bin` |

Zig 源码托管已迁到 Codeberg，**二进制仍从 ziglang.org 下**，不要去 GitHub 找官方 tarball。

```bash
# 仅当 apt 没有 zig 时（25.04 及更早）
cd /tmp
curl -fLO https://ziglang.org/download/0.14.1/zig-x86_64-linux-0.14.1.tar.xz
sudo tar -xJf zig-x86_64-linux-0.14.1.tar.xz -C /usr/local
sudo ln -sfn /usr/local/zig-x86_64-linux-0.14.1/zig /usr/local/bin/zig
zig version   # 必须是 0.14.1
```

### 服务找不到编译器

`node` / `tsc` / `go` / `rustc` / `zig` 若只在用户交互式 `PATH` 里（nvm、rustup、手动解压目录），systemd 里的 `local-leet` 看不见。处理：

- 用 apt 装到 `/usr/bin`，或
- `sudo ln -s` 到 `/usr/local/bin`，然后 `sudo systemctl restart local-leet`

不要改评测机上的 `git config`。改完工具链后必须重启服务再看 `/api/languages`。
