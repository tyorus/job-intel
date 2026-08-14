import { createRouter, createWebHistory } from "vue-router";
import { getApiKey } from "./api";
import Login from "./views/Login.vue";
import Dashboard from "./views/Dashboard.vue";
import Jobs from "./views/Jobs.vue";
import JobDetail from "./views/JobDetail.vue";
import Prospects from "./views/Prospects.vue";
import ProspectDetail from "./views/ProspectDetail.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: Login, meta: { public: true } },
    { path: "/", component: Dashboard },
    { path: "/jobs", component: Jobs },
    { path: "/jobs/:id", component: JobDetail },
    { path: "/prospects", component: Prospects },
    { path: "/prospects/:id", component: ProspectDetail },
  ],
});

router.beforeEach((to) => {
  if (!to.meta.public && !getApiKey()) {
    return { path: "/login", query: { next: to.fullPath } };
  }
  return true;
});

export default router;
