<template>
  <div v-if="isLogin" class="auth-shell">
    <router-view />
  </div>
  <div v-else>
    <header class="topbar">
      <router-link class="brand" to="/">LOCAL LEET</router-link>
      <nav>
        <router-link to="/">题目</router-link>
        <router-link to="/scores">成绩</router-link>
        <router-link to="/submissions">提交记录</router-link>
        <router-link v-if="user?.is_admin" to="/admin">管理</router-link>
      </nav>
      <span class="spacer" />
      <span v-if="user" class="user">{{ user.username }}</span>
      <button class="ghost" @click="logout">退出</button>
    </header>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Auth, type User } from "./api";

const route = useRoute();
const router = useRouter();
const user = ref<User | null>(null);
const isLogin = computed(() => route.path === "/login");

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
