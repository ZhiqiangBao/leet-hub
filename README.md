# Local Leet

家庭局域网里的 LeetCode 式刷题站。

**判题只发生在 Ubuntu 主机上**，使用那台机器系统自带的 `python3` 和 `g++`。局域网里其他电脑无论是 Windows 还是 macOS，都只通过浏览器访问 `http://<Ubuntu的IP>:8080` 写代码、提交；答题电脑不需要安装编译器。

本仓库可以在 Windows 上编写和检查前端/后端逻辑，但不要把 Windows 当成评测机。把代码推到 GitHub 后，在 Ubuntu 笔记本上 clone 并启动服务。

## 角色

| 机器 | 作用 |
| --- | --- |
| Ubuntu 笔记本 | 网站服务器 + 评测机（`python3` / `g++`） |
| 家庭局域网其他电脑 | 浏览器答题 |
| 当前 Windows 开发机 | 写这个仓库，不负责给家里人判题 |

JS / Go / Rust / Zig 已留语言适配器接口。Ubuntu 上即使安装了 `node` / `go` / `rustc` / `zig`，这些语言在补全适配器之前会显示为「接口保留」。

## 在 Ubuntu 主机上部署

需要：Ubuntu、`python3`、`g++`、以及构建前端用的 Node.js/npm。

```bash
git clone <本仓库 URL>
cd local-leet
chmod +x scripts/setup-ubuntu.sh scripts/run-ubuntu.sh scripts/update-from-github.sh
./scripts/setup-ubuntu.sh
```

脚本会：

1. 安装 `python3`、`g++`、`nodejs`/`npm`
2. 创建 `.venv` 并安装后端依赖
3. 构建前端
4. 安装并启动 `local-leet` systemd 服务，监听 `0.0.0.0:8080`

然后在其他电脑浏览器打开：

```text
http://<Ubuntu局域网IP>:8080
```

查看 IP：`hostname -I` 或 `ip -4 addr`。若开了 ufw：`sudo ufw allow 8080/tcp`。

前台调试（不用 systemd）：

```bash
./scripts/run-ubuntu.sh
```

第一个注册的用户会成为管理员。也可以设置：

```bash
export LOCAL_LEET_ADMINS=alice,bob
```

## 使用

- 注册 / 登录后打开题目，在编辑器里填写 `class Solution`，提交。
- 评测结果：`AC` / `WA` / `TLE` / `MLE` / `RE` / `CE`。隐藏测例失败时不回显输入。

## 怎么加题目（推荐：GitHub 为真源）

**题库在仓库的 `problems/` 目录里，跟代码一起放在 GitHub 上。** 在 Cursor 里让我出题、写测试集并推送；Ubuntu 主机 `git pull` 后重启服务即可出现新题。不要在 Ubuntu 网页里当日常出题入口——网页写入的本地文件下次 `git pull` 可能被覆盖或产生冲突。

日常流程：

1. 在 Cursor 里说清楚要出的题，例如：  
   「在 `problems/` 加一道中等题：最长回文子串。Python/C++ starter，公开 3 组测例、隐藏 4 组，比较方式 exact。」
2. 我会写好题面、函数签名、starter、`tests.jsonl`，需要的话再帮你提交并推到 GitHub。
3. 到 Ubuntu 主机执行：

```bash
cd ~/local-leet          # 改成你 clone 的路径
chmod +x scripts/update-from-github.sh
./scripts/update-from-github.sh
```

该脚本会 `git pull`，必要时重装依赖/重建前端，然后 `systemctl restart local-leet`，新题目立刻可做。只改了 `problems/`、没改前后端时，等价于：

```bash
git pull
sudo systemctl restart local-leet
```

也可以登录管理员账号，打开「管理」页点 **从磁盘重新加载**（不必重启）。效果相同：重新扫描 `problems/`。

### 一道题要哪些文件

在 `problems/<slug>/` 下（`slug` 只能是小写字母、数字和连字符，如 `two-sum`）：

| 文件 | 作用 |
| --- | --- |
| `meta.yaml` | 标题、难度 `easy/medium/hard`、时限 ms、内存 MB、标签 |
| `statement.md` | Markdown 题面 |
| `signature.yaml` | LeetCode 式函数签名（类名、方法名、参数类型、返回类型、比较方式） |
| `tests.jsonl` | 测试集，一行一个 JSON |
| `starter/python3.py` | Python 初始代码 |
| `starter/cpp17.cpp` | C++ 初始代码 |
| `starter/javascript.js` 等 | 可选；对应语言尚未实现评测时只作占位 |

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
compare: any_order    # 或 exact；any_order 用于「返回下标顺序无所谓」
```

`tests.jsonl` 示例（参数列表必须和 `params` 顺序一致）：

```json
{"args":[[2,7,11,15],9],"expected":[0,1],"hidden":false}
{"args":[[1,2,3,4,5,6,7,8,9,10],19],"expected":[8,9],"hidden":true}
```

- `hidden: false`：做错时网页会显示输入、期望、你的输出。
- `hidden: true`：只显示第几号测例失败，不泄漏数据。正式数据请放隐藏测例。

当前支持的类型：`int` / `float` / `bool` / `str` / 嵌套 `List[T]`（如 `List[List[int]]`）。链表、二叉树尚未支持。

完整样例见 [`problems/two-sum/`](problems/two-sum/)。

### 网页管理（应急，不推荐当主流程）

第一个注册用户（或 `LOCAL_LEET_ADMINS` 里的账号）登录后，顶栏会出现 **管理**：

- **创建题目**：把整道题的 JSON 贴进去提交，会写入本机 `problems/<slug>/`。
- **替换测试集 / 追加测试集**：针对已有 `slug` 改 `tests.jsonl`。
- **从磁盘重新加载**：扫描 `problems/`，用于 Git 拉取之后刷新题库。

对应 HTTP 接口（需已登录管理员 cookie）：

- `POST /api/admin/problems` 创建
- `PUT /api/admin/problems/{slug}` 改题面/签名/starter
- `PUT /api/admin/problems/{slug}/tests` 整表替换测试集
- `POST /api/admin/problems/{slug}/tests:append` 追加测例
- `POST /api/admin/reload` 从磁盘重载

这些接口适合临时改一题。改完若希望家里 Ubuntu 和 GitHub 长期一致，仍应把 `problems/` 的改动提交回仓库。

## 开发机说明（Windows）

仅用于改代码。可运行前端和 Python 自测，C++ 以 Ubuntu 上的 `g++` 为准。

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
cd frontend; npm install; npm run build
$env:PYTHONPATH = "$PWD\backend"
$env:LOCAL_LEET_ROOT = "$PWD"
.\.venv\Scripts\python scripts\selftest.py
$env:PYTHONPATH = "$PWD\backend"
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8080
```

开发时也可同时开 `cd frontend && npm run dev`（Vite 把 `/api` 代理到 8080）。

## 数据

SQLite 和评测临时文件在 `data/`（已 gitignore）。备份时拷贝该目录即可。
