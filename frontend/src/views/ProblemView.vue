<template>
  <div class="workspace" v-if="problem">
    <section class="statement">
      <div class="tabs">
        <button type="button" :class="{ on: leftTab === 'desc' }" @click="leftTab = 'desc'">题目</button>
        <button type="button" :class="{ on: leftTab === 'rank' }" @click="leftTab = 'rank'">排行</button>
      </div>
      <template v-if="leftTab === 'desc'">
        <h1>{{ problem.title }}</h1>
        <div class="meta">
          <span :class="problem.difficulty">{{ difficultyLabel(problem.difficulty) }}</span>
          <span>{{ problem.time_limit_ms }} ms</span>
          <span>{{ problem.memory_limit_mb }} MB</span>
          <span v-if="problem.solved" class="ac">已通过</span>
          <span v-for="t in problem.tags" :key="t" class="chip">{{ tagLabel(t) }}</span>
        </div>
        <div class="md" v-html="html"></div>
      </template>
      <div class="rank-box" v-else-if="ranking">
        <p class="hint" v-if="ranking.mine">
          当前语言你第 {{ ranking.mine.rank }} / {{ ranking.total }} 名 · 最好 {{ ranking.mine.time_ms }} ms
        </p>
        <p class="hint" v-else>当前语言还没有 AC，提交通过后计入排行（测试不计成绩）。</p>
        <table v-if="ranking.entries.length">
          <thead>
            <tr>
              <th>名次</th>
              <th>用户</th>
              <th>最好耗时</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in ranking.entries" :key="e.username" :class="{ me: e.is_me }">
              <td>{{ e.rank }}</td>
              <td>{{ e.username }}{{ e.is_me ? "（我）" : "" }}</td>
              <td>{{ e.time_ms }} ms</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="editor-pane">
      <CodeEditor v-model="source" :language="language" />
      <div class="console" v-if="result">
        <div class="console-head">
          <span v-if="resultKind === 'test'" class="muted">测试结果（不计成绩）</span>
          <span v-else class="muted">提交结果</span>
          <span :class="(result.verdict || result.status || '').toLowerCase()">
            {{ result.verdict || result.status }}
          </span>
          <span v-if="result.time_ms != null" class="muted">{{ result.time_ms }} ms</span>
        </div>
        <pre v-if="result.compile_log">{{ result.compile_log }}</pre>
        <div v-if="details?.message">{{ details.message }}</div>
        <ul v-if="Array.isArray(details?.cases)">
          <li v-for="c in cases" :key="c.index">
            Case {{ Number(c.index) + 1 }} {{ c.passed ? "通过" : "失败" }}
            <span v-if="c.hidden">（隐藏测例）</span>
            <span v-else-if="c.args">
              输入 {{ JSON.stringify(c.args) }} 期望 {{ JSON.stringify(c.expected) }}
              <template v-if="!c.passed && c.got !== undefined"> 实际 {{ JSON.stringify(c.got) }}</template>
            </span>
          </li>
        </ul>
      </div>
      <div class="editor-bar">
        <select v-model="language">
          <option v-for="lang in languages" :key="lang.id" :value="lang.id" :disabled="!lang.available">
            {{ languageLabel(lang.id, lang.display_name) }}{{ lang.available ? "" : lang.implemented ? "（未安装编译器）" : "（接口保留）" }}
          </option>
        </select>
        <span class="draft-hint muted">{{ draftHint }}</span>
        <span class="spacer" />
        <button class="ghost" type="button" :disabled="!!busy" @click="resetStarter">重置</button>
        <button class="btn-run" type="button" :disabled="!!busy" @click="runTests">
          {{ busy === "test" ? "测试中…" : "测试" }}
        </button>
        <button class="btn-submit" type="button" :disabled="!!busy" @click="submit">
          {{ busy === "submit" ? "评测中…" : "提交" }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import CodeEditor from "../components/CodeEditor.vue";
import { renderStatement } from "../markdown";
import {
  Languages,
  Problems,
  Submissions,
  type Language,
  type ProblemDetail,
  type Ranking,
  type RunResult,
  type Submission,
} from "../api";
import { tagLabel } from "../tags";
import { languageLabel } from "../languages";

const route = useRoute();
const problem = ref<ProblemDetail | null>(null);
const languages = ref<Language[]>([]);
const language = ref("python3");
const source = ref("");
const busy = ref<"test" | "submit" | null>(null);
const resultKind = ref<"test" | "submit">("submit");
const result = ref<(Submission | RunResult) | null>(null);
const ranking = ref<Ranking | null>(null);
const leftTab = ref<"desc" | "rank">("desc");
const draftHint = ref("草稿会自动保存");
const ready = ref(false);
let lastSaved = "";
let saveTimer = 0;

const details = computed(() => (result.value?.details || null) as Record<string, unknown> | null);
const cases = computed(
  () => (Array.isArray(details.value?.cases) ? details.value?.cases : []) as Array<Record<string, unknown>>,
);
const html = computed(() => renderStatement(problem.value?.statement_md || ""));

onMounted(async () => {
  languages.value = await Languages.list();
  const available = languages.value.find((l) => l.available);
  if (available) language.value = available.id;
  await load();
});

onBeforeUnmount(() => {
  void flushDraft();
});

watch(() => route.params.slug, load);
watch(language, async (next, prev) => {
  if (!ready.value || !problem.value) return;
  await flushDraft(prev);
  await loadSource(next);
  await loadRanking();
});
watch(source, () => {
  if (!ready.value) return;
  window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => {
    void flushDraft();
  }, 1200);
});

function difficultyLabel(d: string) {
  return d === "easy" ? "Easy" : d === "medium" ? "Medium" : d === "hard" ? "Hard" : d;
}

function starterOf(lang: string) {
  if (!problem.value) return "";
  return problem.value.starter[lang] || Object.values(problem.value.starter)[0] || "";
}

async function loadSource(lang: string) {
  if (!problem.value) return;
  try {
    const draft = await Problems.getDraft(problem.value.slug, lang);
    source.value = draft.source;
    lastSaved = draft.source;
    draftHint.value = draft.from_starter ? "使用模板，编辑后自动保存" : "已恢复上次离开时的代码";
  } catch {
    source.value = starterOf(lang);
    lastSaved = source.value;
  }
}

async function flushDraft(lang = language.value) {
  if (!problem.value) return;
  if (lang === language.value && source.value === lastSaved) return;
  try {
    await Problems.saveDraft(problem.value.slug, lang, source.value);
    if (lang === language.value) lastSaved = source.value;
    draftHint.value = "草稿已保存";
  } catch {
    draftHint.value = "草稿保存失败";
  }
}

async function resetStarter() {
  source.value = starterOf(language.value);
  await flushDraft();
  draftHint.value = "已恢复模板";
}

async function load() {
  ready.value = false;
  const slug = String(route.params.slug);
  problem.value = await Problems.get(slug);
  result.value = null;
  leftTab.value = "desc";
  await loadSource(language.value);
  await loadRanking();
  ready.value = true;
}

async function loadRanking() {
  if (!problem.value) return;
  try {
    ranking.value = await Problems.ranking(problem.value.slug, language.value);
  } catch {
    ranking.value = null;
  }
}

async function runTests() {
  if (!problem.value) return;
  await flushDraft();
  busy.value = "test";
  result.value = null;
  resultKind.value = "test";
  try {
    result.value = await Problems.run(problem.value.slug, language.value, source.value);
  } catch (err) {
    result.value = {
      kind: "test",
      verdict: "NA",
      details: { message: err instanceof Error ? err.message : "测试失败" },
      compile_log: null,
      time_ms: null,
      public_count: 0,
    };
  } finally {
    busy.value = null;
  }
}

async function submit() {
  if (!problem.value) return;
  await flushDraft();
  busy.value = "submit";
  result.value = null;
  resultKind.value = "submit";
  try {
    let current = await Problems.submit(problem.value.slug, language.value, source.value);
    result.value = current;
    for (let i = 0; i < 80 && (current.status === "queued" || current.status === "running"); i++) {
      await new Promise((r) => setTimeout(r, 350));
      current = await Submissions.get(current.id);
      result.value = current;
    }
    problem.value = await Problems.get(problem.value.slug);
    await loadRanking();
  } catch (err) {
    result.value = {
      id: 0,
      problem_slug: problem.value.slug,
      language: language.value,
      status: "done",
      verdict: "NA",
      details: { message: err instanceof Error ? err.message : "提交失败" },
      compile_log: null,
      time_ms: null,
      created_at: "",
      judged_at: null,
    };
  } finally {
    busy.value = null;
  }
}
</script>
