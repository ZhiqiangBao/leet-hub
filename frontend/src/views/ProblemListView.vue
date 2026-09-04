<template>
  <main class="page">
    <h1>题库</h1>
    <p class="hint">判题在 Ubuntu 主机上执行，使用系统 python3 / gcc / g++。</p>
    <table>
      <thead>
        <tr>
          <th>状态</th>
          <th>题目</th>
          <th>难度</th>
          <th>标签</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in problems" :key="p.slug">
          <td>
            <span v-if="p.solved" class="ac">AC</span>
            <span v-else-if="p.attempted" class="wa">—</span>
            <span v-else class="muted">·</span>
          </td>
          <td>
            <router-link :to="`/problems/${p.slug}`">{{ p.title }}</router-link>
          </td>
          <td :class="p.difficulty">{{ p.difficulty }}</td>
          <td>{{ p.tags.join(", ") }}</td>
        </tr>
      </tbody>
    </table>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Problems, type ProblemMeta } from "../api";

const problems = ref<ProblemMeta[]>([]);

onMounted(async () => {
  problems.value = await Problems.list();
});
</script>
