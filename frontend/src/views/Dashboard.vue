<template>
  <section>
    <h1>Board</h1>
    <p class="muted">Hourly public scrape plus manual LinkedIn and client-prospect updates.</p>
    <div v-if="error" class="flash">{{ error }}</div>
    <div class="grid-stats" style="margin: 1rem 0 1.4rem">
      <article class="card">
        <p class="mono muted">Jobs</p>
        <h2>{{ data.jobs_total || 0 }}</h2>
      </article>
      <article class="card">
        <p class="mono muted">Prospects</p>
        <h2>{{ data.prospects_total || 0 }}</h2>
      </article>
      <article class="card">
        <p class="mono muted">Applied / interview</p>
        <h2>{{ (data.jobs_by_status?.applied || 0) + (data.jobs_by_status?.interview || 0) }}</h2>
      </article>
      <article class="card">
        <p class="mono muted">Active conversations</p>
        <h2>{{ activeProspects }}</h2>
      </article>
    </div>

    <div class="card" style="margin-bottom: 1rem">
      <h2>Jobs by status</h2>
      <div class="row">
        <span v-for="(count, status) in data.jobs_by_status || {}" :key="status" class="pill" :class="status">
          {{ labelize(status) }} · {{ count }}
        </span>
        <span v-if="!Object.keys(data.jobs_by_status || {}).length" class="muted">No jobs yet.</span>
      </div>
    </div>

    <div class="card" style="margin-bottom: 1rem">
      <h2>Prospects by status</h2>
      <div class="row">
        <span v-for="(count, status) in data.prospects_by_status || {}" :key="status" class="pill" :class="status">
          {{ labelize(status) }} · {{ count }}
        </span>
        <span v-if="!Object.keys(data.prospects_by_status || {}).length" class="muted">No prospects yet.</span>
      </div>
    </div>

    <div class="card">
      <h2>Recent progress</h2>
      <div class="timeline">
        <router-link
          v-for="event in data.recent_progress || []"
          :key="event.id"
          :to="progressPath(event)"
          class="event clickable"
        >
          <div class="row">
            <StatusPill :value="event.status" />
            <span class="event-title">{{ event.title || fallbackTitle(event) }}</span>
            <span class="mono muted">{{ event.entity_type }}</span>
            <span class="muted">{{ formatWhen(event.created_at) }}</span>
          </div>
          <p v-if="event.company_name" class="muted">{{ event.company_name }}</p>
          <p v-if="event.note">{{ event.note }}</p>
        </router-link>
        <p v-if="!(data.recent_progress || []).length" class="muted">No updates logged.</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import StatusPill from "../components/StatusPill.vue";
import { formatWhen, labelize } from "../constants";

const router = useRouter();
const data = ref({});
const error = ref("");

const activeProspects = computed(() => {
  const counts = data.value.prospects_by_status || {};
  return ["contacted", "replied", "call_booked", "proposal"].reduce(
    (sum, key) => sum + (counts[key] || 0),
    0,
  );
});

function progressPath(event) {
  if (event.entity_type === "prospect") return `/prospects/${event.entity_id}`;
  return `/jobs/${event.entity_id}`;
}

function fallbackTitle(event) {
  return event.entity_type === "prospect" ? "Untitled prospect" : "Untitled job";
}

onMounted(async () => {
  try {
    data.value = await api("/api/dashboard");
  } catch (err) {
    if (err.status === 401) {
      router.push("/login");
      return;
    }
    error.value = err.message;
  }
});
</script>
