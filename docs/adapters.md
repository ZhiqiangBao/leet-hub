# 编写语言适配器

适配器把用户提交的源码变成「可读测试、可调用函数、可输出判定」的一次运行。评测循环在 [`engine.py`](../backend/app/judge/engine.py)：

1. `wrap(user_code, signature)` → 写入 `workdir / source_filename`
2. `compile(workdir)` → 失败则 `CE`
3. `run_limited(run_argv(workdir), stdin=tests.jsonl, …)` → 解析 stdout 最后一行 JSON

基类：[`backend/app/judge/base.py`](../backend/app/judge/base.py)。  
已实现：[`python3.py`](../backend/app/judge/languages/python3.py)、[`c11.py`](../backend/app/judge/languages/c11.py)、[`cpp17.py`](../backend/app/judge/languages/cpp17.py)。  
桩：[`stubs.py`](../backend/app/judge/languages/stubs.py)（`javascript` / `go` / `rust` / `zig`）。

工具链装在评测主机；适配器代码进 Git 后由主机拉取。见 [server.md](server.md)。题目格式见 [problems.md](problems.md)。

## 接口

```python
class LanguageAdapter:
    id: str                 # 与 starter 文件名、提交 language 字段一致，如 "go"
    display_name: str
    source_filename: str    # wrap 结果写入的文件名
    implemented: bool       # False 时提交直接 NA，即使 detect() 为真

    def detect(self) -> bool: ...
    def wrap(self, user_code: str, signature: dict) -> str: ...
    def compile(self, workdir: str) -> CompileResult: ...
    def run_argv(self, workdir: str) -> list[str]: ...
```

`available()` = `implemented and detect()`。`reason()`：`adapter_stub` 或 `compiler_missing`。

`signature` 为 `signature.yaml` 的字典，例如：

```python
{
    "class_name": "Solution",
    "method": "twoSum",
    "params": [{"name": "nums", "type": "List[int]"}, {"name": "target", "type": "int"}],
    "return_type": "List[int]",
    "compare": "any_order",  # 或 "exact"
}
```

类型：`int`、`long`、`float`、`bool`、`str`、嵌套 `List[T]`。默认 `int`；少数题用 `long`（C/C++ `long long`）。

## wrap

生成完整源码：用户代码 + 驱动。驱动必须：

1. 从 **stdin** 按行读取 JSON（即 `tests.jsonl`）。
2. 构造 `class_name` 的实例（或语言等价物），调用 `method`，参数为该行 `args`，顺序与 `params` 相同。
3. 按 `compare` 比较返回值与 `expected`。
4. 向 **stdout** 打印 **一行** JSON（引擎取 stdout 中最后一行合法 JSON 对象）。

用户代码里不要依赖 `main`（C / C++ 驱动自带 `main`）。不要在驱动里访问网络。

## 驱动输出

| 情况 | JSON |
| --- | --- |
| 全部通过 | `{"verdict":"AC","passed":N,"total":N}` |
| 第 i 个测例答案错误（0 起算） | `{"verdict":"WA","failed_index":i,"got":<实际值>,"passed":i,"total":N}` |
| 运行时错误 | `{"verdict":"RE","failed_index":i,"message":"...","passed":i,"total":N}` |

`got` 须能被 JSON 序列化。`any_order` 只对顶层列表打乱顺序后比较。浮点用相对/绝对误差约 `1e-6`。

进程被杀、超时、超内存由沙箱判定为 `TLE`/`MLE`，驱动不必处理。非 0 退出且没有合法 JSON 时，引擎记为 `RE`。

## compile 与 run_argv

- **解释型**（Python、Node）：`compile` 可语法检查或返回 `CompileResult(ok=True)`；`run_argv` 为解释器命令，cwd 为 `workdir`。
- **编译型**：在 `workdir` 调编译器，产物名固定（如 `program`）。失败时 `CompileResult(ok=False, log=编译器输出)`。
- 编译请使用 `run_limited(..., for_compile=True)`，避免桌面用户进程数限制导致 `g++` 起不来 `cc1plus`。运行用户程序不要设 `for_compile`。
- 评测无外网。禁止 `cargo add`、`go get`、`npm install`。JSON 用标准库，或把单文件解析器 `copy` 进 `workdir`（C 的 `json.h`、C++ 的 `mini_json.hpp`）。

## 登记清单

1. 实现类：`implemented = True`，写好 `detect` / `wrap` / `compile` / `run_argv`。可从 `stubs.py` 拆到 `backend/app/judge/languages/<id>.py`。
2. 在 [`languages/__init__.py`](../backend/app/judge/languages/__init__.py) 的 `ADAPTERS` 中注册（桩已占位，替换类即可）。
3. [`_starter_ext`](../backend/app/services/problems.py) 已有 `.js` / `.go` / `.rs` / `.zig`。新语言 id 在此补后缀。
4. 各题 `problems/<slug>/starter/<id>.<后缀>`。
5. [`CodeEditor.vue`](../frontend/src/components/CodeEditor.vue) 的 `monacoLang`：`javascript`→`javascript`，`go`→`go`，`rust`→`rust`，`zig` 可用 `plaintext`。
6. 推送仓库；评测主机 `./scripts/update-from-github.sh`（改了 frontend 会重建）。主机安装对应编译器。
7. `GET /api/languages` 中该项 `implemented`、`runtime_detected`、`available` 均为 true。用两数之和提交 AC、WA 各一次。`scripts/selftest.py` 可加用例；开发机无编译器则跳过。

## 各语言要点

对照 Python：用户 `class Solution`，驱动拼接在同一文件末尾，`python3 -I solution.py`。  
对照 C：力扣式自由函数（无 `class Solution`），`List[int]` 展开为 `int* nums, int numsSize`，返回数组时再加 `int* returnSize`；`gcc -O2 -std=gnu11`，语言 id 为 `c`，starter 为 `starter/c.c`。  
对照 C++：`#include <bits/stdc++.h>` 与 JSON 头，用户 `class Solution`，生成 `main` 调方法；`g++ -O2 -std=c++20`（含 `std::ranges`）。语言 id 仍为 `cpp17`，与 `starter/cpp17.cpp` 文件名一致。

### JavaScript（`javascript`）

- `detect`：`shutil.which("node")`。主机：`sudo apt install nodejs`。
- `source_filename`：`solution.js`。`compile`：`node --check solution.js`。`run_argv`：`[node, "solution.js"]`。
- 用户：`class Solution { twoSum(nums, target) { ... } }`。驱动 `JSON.parse` 每行，`new Solution()` 后调用 `signature.method`。
- 不要 `require` 外部 npm 包。

### Go（`go`）

- `detect`：`shutil.which("go")`。主机：`sudo apt install golang-go`。
- 在 `workdir` 写最小 `go.mod`（`module solution`），`go build -o program solution.go`，`GOPROXY=off`。
- `package main`。驱动用 `encoding/json`。方法若要导出须大写，驱动里写死对 `signature.method` 的调用。
- `go.mod` 不引用外部 module。

### Rust（`rust`）

- `detect`：`shutil.which("rustc")`。安装 `rustc`，不要每次判题 `cargo add`。
- `rustc -O -o program solution.rs`。不能依赖 crates.io 的 `serde`。在 `backend/app/judge/runtimes/` 放小型 JSON，或只解码本题类型。

### Zig（`zig`）

- `detect`：`shutil.which("zig")`。将 `zig` 加入 PATH。
- `zig build-exe solution.zig -O ReleaseFast -femit-bin=program`（随版本改参数）。
- 驱动用 `std.json`。API 随 Zig 版本变化，按评测主机上的版本编写。

## 最小骨架

```python
import shutil
from pathlib import Path
from ..base import CompileResult, LanguageAdapter
from ..sandbox import run_limited

class GoAdapter(LanguageAdapter):
    id = "go"
    display_name = "Go"
    source_filename = "solution.go"
    implemented = True

    def detect(self) -> bool:
        return shutil.which("go") is not None

    def wrap(self, user_code: str, signature: dict) -> str:
        return user_code.rstrip() + "\n\n" + _go_harness(signature)

    def compile(self, workdir: str) -> CompileResult:
        Path(workdir, "go.mod").write_text("module solution\n\ngo 1.22\n", encoding="utf-8")
        result = run_limited(
            ["go", "build", "-o", "program", "solution.go"],
            cwd=Path(workdir),
            stdin="",
            time_ms=30000,
            memory_mb=4096,
            for_compile=True,
        )
        if result.returncode != 0:
            return CompileResult(ok=False, log=(result.stderr or result.stdout)[-8000:])
        return CompileResult(ok=True)

    def run_argv(self, workdir: str) -> list[str]:
        return [str(Path(workdir) / "program")]
```

`_go_harness` 须按上文生成 `main` 与 JSON 驱动；不要把未实现的 `wrap` 直接上线。
