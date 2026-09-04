<template>
  <main class="page">
    <h1>后台统计</h1>
    <p class="hint">全站提交只读。测试按钮的运行不会出现在这里。</p>
    <p v-if="error" class="err">{{ error }}</p>
    <div class="stats" v-if="stats">
      <div class="stat">
        <div class="n">{{ stats.users }}</div>
        <div class="l">用户</div>
      </div>
      <div class="stat">
        <div class="n">{{ stats.submissions }}</div>
        <div class="l">提交次数</div>
      </div>
      <div class="stat">
        <div class="n">{{ stats.accepted }}</div>
        <div class="l">AC 次数</div>
      </div>
      <div class="stat">
        <div class="n">{{ stats.problems }}</div>
        <div class="l">题目</div>
      </div>
    </div>
    <h2>各题提交</h2>
    <table v-if="stats">
      <thead>
        <tr>
          <th>题目</th>
          <th>提交</th>
          <th>AC</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in stats.by_problem" :key="p.slug">
          <td>
            <router-link :to="`/problems/${p.slug}`">{{ p.title }}</router-link>
          </td>
          <td>{{ p.submissions }}</td>
          <td>{{ p.accepted }}</td>
        </tr>
      </tbody>
    </table>
    <h2>全部提交</h2>
    <div class="filters">
      <input v-model="slug" placeholder="题目 slug" />
      <input v-model="username" placeholder="用户名" />
      <input v-model="language" placeholder="语言，如 C++20 / python3" />
      <button class="ghost" type="button" @click="loadSubs">筛选</button>
    </div>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>用户</th>
          <th>题目</th>
          <th>语言</th>
          <th>结果</th>
          <th>耗时</th>
          <th>时间</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="s in rows"
          :key="s.id"
          class="clickable"
          :class="{ open: openId === s.id }"
          @click="toggle(s.id)"
        >
          <td>{{ s.id }}</td>
          <td>{{ s.username }}</td>
          <td>
            <router-link :to="`/problems/${s.problem_slug}`" @click.stop>{{ s.problem_slug }}</router-link>
          </td>
          <td>{{ languageLabel(s.language) }}</td>
          <td :class="(s.verdict || s.status).toLowerCase()">{{ s.verdict || s.status }}</td>
          <td>{{ s.time_ms ?? "—" }}</td>
          <td>{{ s.created_at }}</td>
        </tr>
      </tbody>
    </table>
    <pre class="source" v-if="openSource">{{ openSource }}</pre>
    <p class="admin-links">
      <router-link to="/admin/problems">增题 / 改测试集</router-link>
    </p>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Admin, type AdminStats, type Submission } from "../api";
import { languageLabel, languageQueryId } from "../languages";

const stats = ref<AdminStats | null>(null);
const rows = ref<Submission[]>([]);
const slug = ref("");
const username = ref("");
const language = ref("");
const error = ref("");
const openId = ref<number | null>(null);
const openSource = ref("");

onMounted(async () => {
  try {
    stats.value = await Admin.stats();
    await loadSubs();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  }
});

async function loadSubs() {
  error.value = "";
  rows.value = await Admin.submissions({
    slug: slug.value.trim() || undefined,
    username: username.value.trim() || undefined,
    language: languageQueryId(language.value) || undefined,
  });
  openId.value = null;
  openSource.value = "";
}

async function toggle(id: number) {
  if (openId.value === id) {
    openId.value = null;
    openSource.value = "";
    return;
  }
  openId.value = id;
  const detail = await Admin.submission(id);
  openSource.value = detail.source || "（无源码）";
}
</script>
