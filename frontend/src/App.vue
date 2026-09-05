<template>
  <div v-if="isLogin" class="auth-shell">
    <button class="ghost theme-fab" type="button" @click="onToggleTheme">
      {{ theme === "light" ? "深色背景" : "浅色背景" }}
    </button>
    <router-view />
  </div>
  <div v-else>
    <header class="topbar">
      <router-link class="brand" to="/">Leet Hub</router-link>
      <nav>
        <router-link to="/">题目</router-link>
        <router-link to="/scores">成绩</router-link>
        <router-link to="/submissions">提交记录</router-link>
        <router-link v-if="user?.is_admin" to="/admin">管理</router-link>
      </nav>
      <span class="spacer" />
      <span v-if="user" class="user">{{ user.username }}</span>
      <button class="ghost" type="button" @click="onToggleTheme">
        {{ theme === "light" ? "深色" : "浅色" }}
      </button>
      <button class="ghost" @click="logout">退出</button>
    </header>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Auth, type User } from "./api";
import { readTheme, toggleTheme, type Theme } from "./theme";

const route = useRoute();
const router = useRouter();
const user = ref<User | null>(null);
const isLogin = computed(() => route.path === "/login");
const theme = ref<Theme>(readTheme());

function onToggleTheme() {
  theme.value = toggleTheme();
}

async function refresh() {
  if (isLogin.value) {
    user.value = null;
    return;
  }
  try {
    user.value = await Auth.me();
  } catch {
    user.value = null;
  }
}

async function logout() {
  await Auth.logout();
  user.value = null;
  await router.push("/login");
}

onMounted(refresh);
watch(() => route.path, refresh);
</script>
