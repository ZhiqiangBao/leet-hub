import { createRouter, createWebHistory } from "vue-router";
import { Auth } from "./api";
import LoginView from "./views/LoginView.vue";
import ProblemListView from "./views/ProblemListView.vue";
import ProblemView from "./views/ProblemView.vue";
import SubmissionsView from "./views/SubmissionsView.vue";
import ScoresView from "./views/ScoresView.vue";
import AdminView from "./views/AdminView.vue";
import AdminStatsView from "./views/AdminStatsView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView, meta: { public: true } },
    { path: "/", component: ProblemListView },
    { path: "/problems/:slug", component: ProblemView },
    { path: "/scores", component: ScoresView },
    { path: "/submissions", component: SubmissionsView },
    { path: "/admin", component: AdminStatsView },
    { path: "/admin/problems", component: AdminView },
  ],
});

router.beforeEach(async (to) => {
  if (to.meta.public) return true;
  try {
    await Auth.me();
    return true;
  } catch {
    return { path: "/login", query: { next: to.fullPath } };
  }
});

export default router;
