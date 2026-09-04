# Leet Hub

家庭局域网评测站。题目以 LeetCode 函数形式作答（`class Solution`），由一台 Ubuntu 主机提供网页并判题。

仓库：https://github.com/ZhiqiangBao/leet-hub

判题使用 Ubuntu 系统自带的 `/usr/bin/python3` 与 `/usr/bin/g++`。局域网内其他设备通过浏览器访问 `http://<Ubuntu局域网IP>:8080` 登录、读题、提交。答题端无需安装编译器。

JavaScript、Go、Rust、Zig 保留语言适配器接口；未实现评测前，界面显示为接口保留。

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

## 角色与权限

三套身份不要混在一张表的同一列里。同一台 Windows 可以既当浏览器端，又当仓库维护端，但权限来源不同。

**评测主机**：跑服务的那台 Ubuntu。用户库、提交记录、正在使用的 `problems/` 以及 `python3`/`g++` 判题都在这里。

**浏览器端**：任何打开 `http://<Ubuntu局域网IP>:8080` 的设备（包括 Ubuntu 本机浏览器）。只操作网站；账号不写在这台设备上。

**仓库维护端**：能向 GitHub 仓库推送的电脑。改 `problems/` 源文件并 `git push`。与网页是否登录管理员无关。

| | 评测主机 | 浏览器端 | 仓库维护端 |
| --- | --- | --- | --- |
| 典型位置 | Ubuntu 笔记本 | 打开 8080 的任意设备 | 能 `git push` 的电脑 |
| 作用 | 网站、数据库、判题、存放当前题库 | 注册、登录、做题；管理员可开「管理」页 | 向 GitHub 提交题面与测试集 |
| 账号 | 存在本机 `data/` | 不存账号，只有会话 cookie | 用的是 GitHub 账号，不是网站账号 |
| 管理员 | `is_admin` 记在本机数据库 | 顶栏「管理」把请求发到评测主机 | 无网站管理员含义 |
| 网页加题 | 收到请求后写入本机 `problems/` | 管理员在网页上填写，结果落在评测主机 | 不经过网页 |
| Git 加题 | `git pull` 后重载或重启 | 不参与 | 改 `problems/` 后 `git push` |

从浏览器端注册（地址必须是评测主机的 8080）：用户写入评测主机。该机尚无用户时，第一人即为网页管理员。换一台设备用同一用户名密码登录，仍是该账号。

网页管理员与 GitHub 写权限相互独立。日常题库以 GitHub 为真源：仓库维护端推送，评测主机执行 `./scripts/update-from-github.sh`。不要同时用网页「管理」和 Git 改同一题。

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
