# 服务端操作

服务端即**评测主机**：安装并运行本仓库的那台 Ubuntu。它提供网页、保存账号与提交、用本机 `/usr/bin/python3`、`/usr/bin/gcc`、`/usr/bin/g++`、`node` 与 `tsc` 判题。GitHub 仓库名是 `leet-hub`；systemd 服务名是 `local-leet`。

浏览器所在电脑不是服务端。客户端说明见 [client.md](client.md)。

## 首次部署

依赖：Ubuntu、`python3`、`gcc`、`g++`、Node.js / npm（构建前端，并作为 JavaScript 评测运行时）。TypeScript 评测另需全局 `tsc`（`setup-ubuntu.sh` 会 `npm install -g typescript`）。

```bash
git clone https://github.com/ZhiqiangBao/leet-hub.git
cd leet-hub
chmod +x scripts/setup-ubuntu.sh scripts/run-ubuntu.sh scripts/update-from-github.sh scripts/serve-window.sh
./scripts/setup-ubuntu.sh
```

脚本安装依赖、创建 `.venv`、构建前端，并将单元安装为 `/etc/systemd/system/local-leet.service`，监听 `0.0.0.0:8080`。

查询局域网 IP：`hostname -I` 或 `ip -4 addr`。若启用 ufw：

```bash
sudo ufw allow 8080/tcp
```

不使用 systemd、当前终端前台运行（关闭终端即停止）：

```bash
./scripts/run-ubuntu.sh
```

弹出独立日志窗口（关闭该窗口即停止整个服务；若 `local-leet` 正在后台跑会先停掉）：

```bash
chmod +x scripts/serve-window.sh
./scripts/serve-window.sh
```

## 查看与控制服务

```bash
systemctl status local-leet
sudo systemctl start local-leet
sudo systemctl stop local-leet
sudo systemctl restart local-leet
sudo systemctl disable --now local-leet
journalctl -u local-leet -e
journalctl -u local-leet -f
```

`status` 中 `active (running)` 表示在运行。本机浏览器打开 `http://127.0.0.1:8080` 应出现登录页。

- **systemd**：`stop` / `disable` 才能关掉。只关 `journalctl -f` 窗口不会停服务。
- **日志窗口** `./scripts/serve-window.sh`：关窗口即停服务。

若提示 `Unit local-leet.service not found`，尚未执行 `./scripts/setup-ubuntu.sh`。

## 从 GitHub 更新

在克隆目录中：

```bash
cd ~/leet-hub
./scripts/update-from-github.sh
```

脚本执行 `git pull`；`backend/requirements.txt` 或 `frontend/` 有变更时会重装依赖或重建前端，然后 `systemctl restart local-leet`。

仅更新了 `problems/` 时也可：

```bash
git pull
sudo systemctl restart local-leet
```

管理员登录后，在「管理」页选择「从磁盘重新加载」可只重扫题库、不重启进程。

## 管理员

账号存在本机 `data/` 的 SQLite 中，与从哪台电脑打开网页无关。

- 该机尚无用户时，第一个在 `http://<本机IP>:8080` 注册的账号成为管理员。
- 或设置环境变量后重启服务：

```bash
sudo systemctl edit local-leet
```

写入：

```ini
[Service]
Environment=LOCAL_LEET_ADMINS=你的用户名
```

```bash
sudo systemctl restart local-leet
```

多个用户名用逗号分隔。用该用户名登录一次即可提升为管理员。

## 接口文档

FastAPI 自动文档（需服务已启动）：

```text
http://127.0.0.1:8080/docs
```

这不是做题界面，只列出 HTTP API。

## 数据备份

SQLite 与评测临时文件在仓库目录下的 `data/`，不纳入 Git。备份或迁移时复制该目录。用户、提交记录不在 GitHub 上。

## 角色（服务端视角）

| 事项 | 位置 |
| --- | --- |
| 网站进程 | systemd `local-leet` |
| 用户与提交 | `data/local-leet.db` |
| 当前题库 | 本机 `problems/`（由 git 拉取或管理员写盘） |
| 判题编译器 | 系统 `python3`、`gcc`、`g++`、`node`；TypeScript 另需全局 `tsc` |

向 GitHub 推送题目在仓库维护端完成，服务端负责 `git pull` 后加载。说明见 [problems.md](problems.md)。

## 接入其他语言（服务端要做什么）

语言分两截，缺一不可：

| | 在评测主机上做 | 在 Git 仓库里做 |
| --- | --- | --- |
| 内容 | 安装运行时：`node`、`go`、`rustc`、`zig` 等 | 实现适配器 `wrap` / `compile` / `run`，补 starter 与前端高亮 |
| 不做则 | `/api/languages` 里 `runtime_detected` 为 false | `implemented` 为 false，提交得 `NA` |
| 如何同步到主机 | 本机 `apt` / 官方安装包，与 GitHub 无关 | 推送到仓库后，主机 `./scripts/update-from-github.sh` |

只在 Ubuntu 上 `apt install golang-go` **不会**让 Go 可以交题。只改仓库、主机没有 `go`，同样不可用。适配器写法见 [adapters.md](adapters.md)。

可在评测主机上直接改 `backend/` 并重启 `local-leet` 做试验。要给家里其他开发者用、或避免被下次 `git pull` 覆盖，仍须把改动推回 GitHub。

## 协同开发

协作面是 GitHub 仓库 https://github.com/ZhiqiangBao/leet-hub，不是评测主机上的网页账号。

- 把协作者加为该仓库的 Collaborator（或使用 Pull Request）。每人克隆、改 `problems/` 或 `backend/`、推送。
- 评测主机只部署：定期 `git pull`（或 `./scripts/update-from-github.sh`）并重启服务。不要把 Ubuntu 当成唯一的 git 工作副本；多人同时在主机上改同一目录会互相覆盖。
- 网站管理员只能改主机磁盘上的题库，不能改适配器代码，也不能代替 GitHub 写权限。
- 用户提交记录在主机 `data/` 里，不进入 Git，互不影响协同。

更新顺序：仓库合并 → 评测主机拉取 → 若新增语言则在主机安装对应编译器 → `systemctl restart local-leet`。
