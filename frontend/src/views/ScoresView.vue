<template>
  <main class="page">
    <h1>我的成绩</h1>
    <p class="hint">同一题、同一语言，取最好一次 AC 的耗时排名。测试运行不计入。</p>
    <p v-if="!rows.length" class="hint">还没有 AC 记录。通过提交（不是测试）后会出现在这里。</p>
    <table v-else>
      <thead>
        <tr>
          <th>题目</th>
          <th>语言</th>
          <th>最好耗时</th>
          <th>名次</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="`${r.slug}-${r.language}`">
          <td>
            <router-link :to="`/problems/${r.slug}`">{{ r.title }}</router-link>
          </td>
          <td>{{ languageLabel(r.language) }}</td>
          <td>{{ r.time_ms }} ms</td>
          <td>第 {{ r.rank }} / {{ r.total }} 名</td>
        </tr>
      </tbody>
    </table>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Scores, type ScoreRow } from "../api";
import { languageLabel } from "../languages";

const rows = ref<ScoreRow[]>([]);

onMounted(async () => {
  rows.value = await Scores.mine();
});
</script>
