<div align="center">

# Leet Hub

**家里那台 Ubuntu，就是评测机。**

局域网浏览器打开即可做题。力扣式 `class Solution`，隐藏测例提交，耗时榜按语言分开。

[仓库](https://github.com/ZhiqiangBao/leet-hub)
·
[服务端](docs/server.md)
·
[客户端](docs/client.md)
·
[出题](docs/problems.md)
·
[规划](docs/roadmap.md)

```
  手机 / Windows / Mac                 Ubuntu
 ┌─────────────────────┐            ┌──────────────────────┐
 │  题面 · 编辑器 · 榜   │  LAN :8080 │  FastAPI · 沙箱判题    │
 │  浅色 / 深色  切换    │ ─────────► │  python3 gcc g++ node │
 └─────────────────────┘            │  题库真源 = GitHub     │
                                    └──────────────────────┘
         答题端不装编译器                    判题只发生在这里
```

</div>

## 现在能跑什么

| | 语言 | 状态 |
| :--- | :--- | :--- |
| ● | Python 3 · C · C++20 | **可评测**（主机上的 `/usr/bin/python3`、`gcc`、`g++`） |
| ● | JavaScript · TypeScript | **可评测**（主机 `node`；TypeScript 另需全局 `tsc`：`sudo npm install -g typescript`） |
| ○ | Go · Rust · Zig | 空模板已有，适配器仍是桩，下拉框灰色，提交为 `NA` |

题面支持 `$…$` 公式（KaTeX）。测试只跑公开示例、不计分；提交跑全部隐藏测例、进该语言耗时榜。

浏览器访问：

```text
http://<Ubuntu局域网IP>:8080
```

IP 用评测机上的 `hostname -I`。必须带端口。答题端不装 Python / gcc。

## 文档

| | |
| :--- | :--- |
| [磁盘出题](docs/problems.md) | `problems/` 目录、题面与测试集、starter 脚本 |
| [服务端](docs/server.md) | Ubuntu 部署、systemd、从 GitHub 更新、协同 |
| [客户端](docs/client.md) | 注册、做题、测试 / 提交、网页管理 |
| [接入语言](docs/languages.md) | 主机装工具链 + 仓库改代码 |
| [语言适配器](docs/adapters.md) | `LanguageAdapter`、驱动协议、JS / TS / Go / Rust / Zig |
| [规划](docs/roadmap.md) | 加题、其余语言真正可评测 |

出题流水线见 [`QWEN.md`](QWEN.md)。starter 不要手写，签名落盘后：

```powershell
python scripts/write-starters.py --slug <slug>
```

## 评测主机：装起来

```bash
git clone https://github.com/ZhiqiangBao/leet-hub.git
cd leet-hub
chmod +x scripts/setup-ubuntu.sh scripts/run-ubuntu.sh scripts/update-from-github.sh scripts/serve-window.sh
./scripts/setup-ubuntu.sh
```

服务名 `local-leet`，端口 **8080**。细节在 [server.md](docs/server.md)。代码推上 GitHub 之后，主机只跑：

```bash
./scripts/update-from-github.sh
```

<details>
<summary>关掉 / 前台看日志</summary>

后台（关终端也不停）：

```bash
sudo systemctl stop local-leet
```

开机不再自启：`sudo systemctl disable local-leet`。停用并立刻关闭：`sudo systemctl disable --now local-leet`。

前台日志窗口（关窗口 = 停站）：

```bash
./scripts/serve-window.sh
```

会先 `stop` 已在跑的 `local-leet`，再弹出带日志的终端。`Ctrl+C` 或关窗口即结束。无图形界面时在当前终端前台跑，效果相同。

</details>

## 开发机

改仓库用，不当家里那台评测机。协作走 GitHub，Ubuntu 只 `pull` 部署，见 [协同开发](docs/server.md)。

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
cd frontend
npm install
npm run build
$env:PYTHONPATH = "$PWD\backend"
$env:LOCAL_LEET_ROOT = "$PWD"
.\.venv\Scripts\python scripts\selftest.py
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8080
```

前端热更新：`cd frontend && npm run dev`（`/api` 代理到 `8080`）。
