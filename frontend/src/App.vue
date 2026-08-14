<template>
  <div v-if="isLogin" class="login-wrap">
    <div class="top-actions" style="position: absolute; top: 1rem; right: 1rem">
      <button class="ghost theme-toggle" type="button" :title="themeTitle" @click="toggleTheme">
        {{ themeIcon }}
      </button>
    </div>
    <router-view />
  </div>
  <div v-else class="shell">
    <header class="topbar">
      <div class="brand">
        <strong>Tyorus Pipeline</strong>
        <span>jobs · services prospects</span>
      </div>
      <nav>
        <router-link to="/">Board</router-link>
        <router-link to="/jobs">Jobs</router-link>
        <router-link to="/prospects">Prospects</router-link>
      </nav>
      <div class="top-actions">
        <button class="ghost theme-toggle" type="button" :title="themeTitle" @click="toggleTheme">
          {{ themeIcon }}
        </button>
        <button class="ghost" type="button" @click="logout">Lock</button>
      </div>
    </header>
    <main class="page">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearApiKey } from "./api";
import {
  applyTheme,
  cycleTheme,
  getStoredTheme,
} from "./theme";

const route = useRoute();
const router = useRouter();
const isLogin = computed(() => route.path === "/login");
const preference = ref(getStoredTheme());
const resolved = ref(applyTheme(preference.value));

const themeIcon = computed(() => {
  if (preference.value === "system") return "◐";
  return resolved.value === "light" ? "☀" : "☾";
});

const themeTitle = computed(() => {
  if (preference.value === "system") return "Theme: system";
  return `Theme: ${resolved.value}`;
});

function toggleTheme() {
  const next = cycleTheme(preference.value);
  preference.value = next.preference;
  resolved.value = next.resolved;
}

function logout() {
  clearApiKey();
  router.push("/login");
}

function onSystemChange() {
  if (preference.value === "system") {
    resolved.value = applyTheme("system");
  }
}

let media;
onMounted(() => {
  media = window.matchMedia("(prefers-color-scheme: light)");
  media.addEventListener("change", onSystemChange);
});
onUnmounted(() => {
  media?.removeEventListener("change", onSystemChange);
});
</script>
