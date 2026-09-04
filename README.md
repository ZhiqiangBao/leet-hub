# Leet Hub

家庭局域网评测站。题目以 LeetCode 函数形式作答（`class Solution`），由一台 Ubuntu 主机提供网页并判题。

仓库：https://github.com/ZhiqiangBao/leet-hub

判题使用 Ubuntu 系统自带的 `/usr/bin/python3` 与 `/usr/bin/g++`。局域网内其他设备通过浏览器访问 `http://<Ubuntu局域网IP>:8080` 登录、读题、提交。答题端无需安装编译器。

JavaScript、Go、Rust、Zig 保留语言适配器接口；未实现评测前，界面显示为接口保留。

## 角色与权限

系统只有一台**评测主机**（Ubuntu）。其余设备都是**浏览器端**：打开网页、登录、做题。账号、题库、评测结果都存在 Ubuntu 上，不存在浏览器所在的那台电脑上。

现在用 Windows 打开 `http://<Ubuntu的IP>:8080` 并注册，注册的是 Ubuntu 上的账号。若当时数据库里还没有用户，该账号即为管理员。此后在 Ubuntu 自带浏览器打开 `http://127.0.0.1:8080`，用同一用户名和密码登录，仍是同一个管理员，不是两套账号。

| | 评测主机（Ubuntu） | 浏览器端（Windows / 手机 / 另一台电脑） |
| --- | --- | --- |
| 作用 | 跑网站、存用户和提交、用本机 `python3`/`g++` 判题、存放 `problems/` | 打开网页：注册、登录、读题、写代码、提交 |
| 账号存在哪 | `data/` 里的 SQLite | 不保存账号；浏览器只持有登录会话 |
| 谁算管理员 | 记在 Ubuntu 数据库里的 `is_admin` | 无独立管理员；顶栏「管理」只是在遥控 Ubuntu |
| 做题 | 本机浏览器访问 8080 同样可以做题 | 任意设备访问 Ubuntu 的 8080 即可 |
| 网页「管理」加题 | 管理员登录后可写本机 `problems/` | 管理员在任意浏览器登录后，请求发到 Ubuntu，同样写 Ubuntu 的 `problems/` |
| GitHub 加题 | `git pull` 后重载或重启，新题生效 | 向本仓库推送 `problems/`（需 GitHub 写权限，与网页管理员不是同一套权限） |

网页管理员与 GitHub 写权限相互独立：

- **网页管理员**：第一个注册用户，或环境变量 `LOCAL_LEET_ADMINS` 中的用户名。用于在网站上改 Ubuntu 磁盘上的题库。
- **GitHub 写权限**：能向 https://github.com/ZhiqiangBao/leet-hub 推送的人。日常出题走这条路径：改 `problems/` → `git push` → Ubuntu 上执行 `./scripts/update-from-github.sh`。

两台机器都可以「加题」，含义不同：浏览器端点「管理」是在改 Ubuntu 本地文件；在开发机改仓库并推送，是改 GitHub，再由 Ubuntu 拉取。不要两套同时改同一题，以免冲突。

## 部署（Ubuntu 主机）

依赖：Ubuntu、`python3`、`g++`、Node.js / npm（用于构建前端）。

```bash
git clone https://github.com/ZhiqiangBao/leet-hub.git
cd leet-hub
chmod +x scripts/setup-ubuntu.sh scripts/run-ubuntu.sh scripts/update-from-github.sh
./scripts/setup-ubuntu.sh
```

`setup-ubuntu.sh` 会安装 `python3`、`g++`、`nodejs`/`npm`，创建虚拟环境，构建前端，并安装 systemd 服务 `local-leet`，监听 `0.0.0.0:8080`。

局域网访问：

```text
http://<Ubuntu局域网IP>:8080
```

查询本机 IP：`hostname -I` 或 `ip -4 addr`。若启用 ufw：`sudo ufw allow 8080/tcp`。

不使用 systemd 的前台运行：

```bash
./scripts/run-ubuntu.sh
```

第一个在该评测主机上注册的用户为管理员（账号写在 Ubuntu 的数据库中，与从哪台电脑打开网页无关）。也可通过环境变量指定：

```bash
export LOCAL_LEET_ADMINS=alice,bob
```

## 使用

注册并登录后，打开题目，在编辑器中实现 `Solution` 指定方法并提交。

判定结果：`AC`、`WA`、`TLE`、`MLE`、`RE`、`CE`。隐藏测例失败时不回显输入、期望与输出。

## 题库

题库目录为 `problems/`，与代码一并纳入 Git。GitHub 为题库真源：在仓库中新增或修改题目并推送后，Ubuntu 主机拉取即可。

从 GitHub 更新（在 Ubuntu 克隆目录中执行）：

```bash
cd ~/leet-hub
./scripts/update-from-github.sh
```

脚本执行 `git pull`；若依赖或前端有变更则重建，然后 `systemctl restart local-leet`。仅变更 `problems/` 时等价于：

```bash
git pull
sudo systemctl restart local-leet
```

管理员登录后，也可在「管理」页选择「从磁盘重新加载」，无需重启进程。

请勿以网页管理作为日常出题方式。网页写入的是主机本地 `problems/`，与远程仓库不一致时，`git pull` 可能冲突或覆盖。

### 题目目录

每题一个目录 `problems/<slug>/`。`slug` 仅含小写字母、数字与连字符，例如 `two-sum`。

| 文件 | 说明 |
| --- | --- |
| `meta.yaml` | 标题、难度（`easy` / `medium` / `hard`）、时限（毫秒）、内存（MB）、标签 |
| `statement.md` | 题面（Markdown） |
| `signature.yaml` | 类名、方法名、参数类型、返回类型、比较方式 |
| `tests.jsonl` | 测试集，每行一个 JSON 对象 |
| `starter/python3.py` | Python 初始代码 |
| `starter/cpp17.cpp` | C++ 初始代码 |
| `starter/javascript.js` 等 | 可选占位；对应语言尚未实现评测 |

`signature.yaml` 示例：

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

`compare` 取值：`exact`（逐位相等）；`any_order`（列表元素顺序无关，适用于返回下标等）。

`tests.jsonl` 示例。`args` 顺序须与 `params` 一致：

```json
{"args":[[2,7,11,15],9],"expected":[0,1],"hidden":false}
{"args":[[1,2,3,4,5,6,7,8,9,10],19],"expected":[8,9],"hidden":true}
```

- `hidden: false`：失败时向提交者展示输入、期望与实际输出。
- `hidden: true`：仅提示测例序号，不展示数据。正式数据使用隐藏测例。

支持的类型：`int`、`float`、`bool`、`str`、嵌套 `List[T]`（如 `List[List[int]]`）。链表与二叉树尚未支持。

样例题目：[`problems/two-sum/`](problems/two-sum/)。

### 管理接口

管理员账号：首次注册用户，或 `LOCAL_LEET_ADMINS` 中列出的用户名。登录后顶栏显示「管理」。

页面功能：创建题目、整表替换测试集、追加测试集、从磁盘重新加载。请求写入本机 `problems/`。若需与 GitHub 保持一致，将改动提交并推送到本仓库。

HTTP 接口（需管理员会话 cookie）：

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `POST` | `/api/admin/problems` | 创建题目 |
| `PUT` | `/api/admin/problems/{slug}` | 修改题面、签名或 starter |
| `PUT` | `/api/admin/problems/{slug}/tests` | 替换测试集 |
| `POST` | `/api/admin/problems/{slug}/tests:append` | 追加测例 |
| `POST` | `/api/admin/reload` | 从磁盘重载题库 |

## 开发环境

开发机用于修改本仓库，不作为家庭局域网评测机。Python 判题逻辑可在开发机自测；C++ 以 Ubuntu 上的 `g++` 为准。

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

前端热更新：另开终端执行 `cd frontend && npm run dev`。Vite 将 `/api` 代理到 `8080`。

## 数据

SQLite 与评测临时文件位于 `data/`，不纳入版本库。备份时复制该目录。
