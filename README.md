# Leet Hub

家庭局域网评测站。题目以 LeetCode 函数形式作答（`class Solution`），由一台 Ubuntu 主机提供网页并判题。

仓库：https://github.com/ZhiqiangBao/leet-hub

判题使用 Ubuntu 系统自带的 `/usr/bin/python3`、`/usr/bin/gcc` 与 `/usr/bin/g++`。局域网内其他设备用浏览器访问 `http://<Ubuntu局域网IP>:8080`。答题端无需安装编译器。

JavaScript、Go、Rust、Zig 已预留适配器，实现步骤见文档。

## 文档

| 文档 | 内容 |
| --- | --- |
| [在磁盘上编写题目](docs/problems.md) | `problems/` 目录、题面与测试集写法、拉取后生效 |
| [服务端操作](docs/server.md) | Ubuntu 部署、服务、更新、接入语言时主机侧步骤、协同开发 |
| [客户端操作](docs/client.md) | 浏览器注册、做题、提交、网页管理 |
| [接入语言](docs/languages.md) | 入口：主机装工具链与仓库改代码 |
| [编写语言适配器](docs/adapters.md) | `LanguageAdapter`、驱动协议、JS / Go / Rust / Zig 写法 |
| [后续改进方向](docs/roadmap.md) | 提交后台与耗时榜、加题、测试/提交分离 |

## 快速开始（评测主机）

```bash
git clone https://github.com/ZhiqiangBao/leet-hub.git
cd leet-hub
chmod +x scripts/setup-ubuntu.sh scripts/run-ubuntu.sh scripts/update-from-github.sh scripts/serve-window.sh
./scripts/setup-ubuntu.sh
```

服务名：`local-leet`，端口 `8080`。完整步骤见 [服务端操作](docs/server.md)。

### 关闭服务

后台（systemd，关终端也不停）：

```bash
sudo systemctl stop local-leet
```

开机不再自启：`sudo systemctl disable local-leet`。停用并立刻关闭：`sudo systemctl disable --now local-leet`。

前台日志窗口（关闭窗口 = 停止整个服务）：

```bash
chmod +x scripts/serve-window.sh
./scripts/serve-window.sh
```

会先 `stop` 已在跑的 `local-leet`，再弹出带日志的终端。关掉该窗口或在其中 `Ctrl+C` 即结束网站与判题。无图形界面时在当前终端前台运行，效果相同。

## 开发环境

开发机用于修改本仓库，不作为家庭局域网评测机。多人协作在 GitHub 上进行，评测主机只负责拉取部署，见 [服务端操作 · 协同开发](docs/server.md)。

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
