---
name: write-starters
description: >-
  根据 signature.yaml 生成 problems/<slug>/starter 空函数体。author 用，不要手写 starter。
disable-model-invocation: true
priority: 20
---

# 生成空 starter

只跑脚本，不要 `read_file` 本文件或 `write-starters.py` 源码，不要手写 `starter/`。

签名必须已经落在 `problems/<slug>/signature.yaml`。

```powershell
python "scripts/write-starters.py" --slug <slug>
```

默认写出全部语言（Python / C / C++ / JS / TS / Go / Rust / Zig）。一行 JSON：`ok`、`wrote`。`ok` 为 true 即可。不要把 starter 正文贴进对话。

只要三语时加 `--core`。改了签名必须重跑，不要手改生成结果。
