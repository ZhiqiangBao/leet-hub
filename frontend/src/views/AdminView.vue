<template>
  <main class="page admin-grid">
    <h1>增加题目 / 测试集</h1>
    <p class="hint">管理员可以把题目写到磁盘上的 `problems/` 目录，也可在此用 JSON 提交。</p>
    <p v-if="message" class="ac">{{ message }}</p>
    <p class="err">{{ error }}</p>
    <div class="row">
      <button class="ghost" type="button" @click="reload">从磁盘重新加载</button>
    </div>
    <label>创建题目 JSON</label>
    <textarea v-model="createJson"></textarea>
    <button class="primary" type="button" @click="create">创建题目</button>
    <label>题目 slug（用于改测试集）</label>
    <input v-model="slug" />
    <label>测试集 JSON 数组</label>
    <textarea v-model="testsJson"></textarea>
    <div class="row">
      <button class="primary" type="button" @click="replace">替换测试集</button>
      <button class="ghost" type="button" @click="append">追加测试集</button>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Admin } from "../api";

const message = ref("");
const error = ref("");
const slug = ref("two-sum");
const createJson = ref(`{
  "slug": "plus-one",
  "title": "加一",
  "difficulty": "easy",
  "time_limit_ms": 2000,
  "memory_limit_mb": 256,
  "tags": ["array"],
  "statement_md": "# 加一\\n\\n给定非负整数数组 digits，表示一个大整数，将该数加一。",
  "signature": {
    "class_name": "Solution",
    "method": "plusOne",
    "params": [{"name": "digits", "type": "List[int]"}],
    "return_type": "List[int]",
    "compare": "exact"
  },
  "starter": {
    "python3": "class Solution:\\n    def plusOne(self, digits: list[int]) -> list[int]:\\n        \\n",
    "cpp17": "class Solution {\\npublic:\\n    vector<int> plusOne(vector<int>& digits) {\\n        \\n    }\\n};\\n"
  },
  "tests": [
    {"args": [[1,2,3]], "expected": [1,2,4], "hidden": false},
    {"args": [[9]], "expected": [1,0], "hidden": true}
  ]
}`);
const testsJson = ref(`[
  {"args": [[0,0], 0], "expected": [0,1], "hidden": true}
]`);

function show(err: unknown) {
  error.value = err instanceof Error ? err.message : String(err);
  message.value = "";
}

async function create() {
  try {
    error.value = "";
    const body = JSON.parse(createJson.value);
    await Admin.create(body);
    message.value = `已创建 ${body.slug}`;
  } catch (err) {
    show(err);
  }
}

async function replace() {
  try {
    error.value = "";
    await Admin.replaceTests(slug.value, JSON.parse(testsJson.value));
    message.value = `已替换 ${slug.value} 测试集`;
  } catch (err) {
    show(err);
  }
}

async function append() {
  try {
    error.value = "";
    await Admin.appendTests(slug.value, JSON.parse(testsJson.value));
    message.value = `已追加到 ${slug.value}`;
  } catch (err) {
    show(err);
  }
}

async function reload() {
  try {
    error.value = "";
    const res = await Admin.reload();
    message.value = `已加载 ${res.count} 题`;
  } catch (err) {
    show(err);
  }
}
</script>
