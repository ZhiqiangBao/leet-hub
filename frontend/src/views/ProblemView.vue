<template>
  <div class="workspace" v-if="problem">
    <section class="statement">
      <h1>{{ problem.title }}</h1>
      <div class="meta">
        <span :class="problem.difficulty">{{ problem.difficulty }}</span>
        <span>{{ problem.time_limit_ms }} ms</span>
        <span>{{ problem.memory_limit_mb }} MB</span>
        <span v-if="problem.solved" class="ac">已通过</span>
      </div>
      <div class="md" v-html="html"></div>
    </section>
    <section class="editor-pane">
      <div class="editor-bar">
        <select v-model="language">
          <option v-for="lang in languages" :key="lang.id" :value="lang.id" :disabled="!lang.available">
            {{ lang.display_name }}{{ lang.available ? "" : lang.implemented ? "（未安装编译器）" : "（接口保留）" }}
          </option>
        </select>
        <button class="primary" :disabled="busy" @click="submit">{{ busy ? "评测中…" : "提交" }}</button>
      </div>
      <CodeEditor v-model="source" :language="language" />
      <div class="result" v-if="result">
        <div>
          结果：<span :class="(result.verdict || result.status || '').toLowerCase()">
            {{ result.verdict || result.status }}
          </span>
          <span v-if="result.time_ms != null"> · {{ result.time_ms }} ms</span>
        </div>
        <pre v-if="result.compile_log">{{ result.compile_log }}</pre>
        <div v-if="details?.message">{{ details.message }}</div>
        <ul v-if="Array.isArray(details?.cases)">
          <li v-for="c in cases" :key="c.index">
            #{{ c.index }} {{ c.passed ? "通过" : "失败" }}
            <span v-if="c.hidden">（隐藏测例）</span>
            <span v-else-if="!c.passed && c.args">
              输入 {{ JSON.stringify(c.args) }} 期望 {{ JSON.stringify(c.expected) }} 实际 {{ JSON.stringify(c.got) }}
            </span>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { marked } from "marked";
import CodeEditor from "../components/CodeEditor.vue";
import { Languages, Problems, Submissions, type Language, type ProblemDetail, type Submission } from "../api";

const route = useRoute();
const problem = ref<ProblemDetail | null>(null);
const languages = ref<Language[]>([]);
const language = ref("python3");
const source = ref("");
const busy = ref(false);
const result = ref<Submission | null>(null);
const details = computed(() => (result.value?.details || null) as Record<string, unknown> | null);
const cases = computed(() => (Array.isArray(details.value?.cases) ? details.value?.cases : []) as Array<Record<string, unknown>>);
const html = computed(() => marked.parse(problem.value?.statement_md || "") as string);

onMounted(async () => {
  languages.value = await Languages.list();
  const available = languages.value.find((l) => l.available);
  if (available) language.value = available.id;
  await load();
});

watch(() => route.params.slug, load);
watch(language, () => {
  if (!problem.value) return;
  source.value = problem.value.starter[language.value] || source.value;
});

async function load() {
  const slug = String(route.params.slug);
  problem.value = await Problems.get(slug);
  source.value = problem.value.starter[language.value] || Object.values(problem.value.starter)[0] || "";
  result.value = null;
}

async function submit() {
  if (!problem.value) return;
  busy.value = true;
  result.value = null;
  try {
    let current = await Problems.submit(problem.value.slug, language.value, source.value);
    result.value = current;
    for (let i = 0; i < 80 && (current.status === "queued" || current.status === "running"); i++) {
      await new Promise((r) => setTimeout(r, 350));
      current = await Submissions.get(current.id);
      result.value = current;
    }
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
    busy.value = false;
  }
}
</script>
