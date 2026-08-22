<template>
  <div class="login-card card">
    <p class="mono muted">personal tracker</p>
    <h1>Tyorus Pipeline</h1>
    <p class="muted">
      Enter the tracker API key. Jobs from public boards land hourly; LinkedIn roles and
      client prospects are logged by hand.
    </p>
    <form class="form-grid" @submit.prevent="unlock">
      <label class="span-2">
        API key
        <input v-model="key" type="password" autocomplete="current-password" required />
      </label>
      <button type="submit">Unlock board</button>
    </form>
    <p v-if="error" class="flash">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, setApiKey } from "../api";

const key = ref("");
const error = ref("");
const router = useRouter();
const route = useRoute();

async function unlock() {
  error.value = "";
  setApiKey(key.value.trim());
  try {
    await api("/api/dashboard");
    router.replace(route.query.next || "/");
  } catch (err) {
    error.value = "Key rejected";
  }
}
</script>
