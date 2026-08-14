<template>
  <section v-if="row">
    <p class="mono muted">
      <router-link to="/prospects">← Prospects</router-link>
    </p>
    <h1>{{ row.name }}</h1>
    <p class="muted">{{ row.company || "—" }} · {{ row.role || "no role" }} · {{ row.country || "" }}</p>
    <div class="row" style="margin: 0.6rem 0 1rem">
      <StatusPill :value="row.status" />
      <StatusPill :value="row.package" />
      <span v-if="row.value_estimate_usd" class="mono">${{ row.value_estimate_usd }}</span>
      <button
        v-if="row.status !== 'cancelled'"
        type="button"
        class="danger"
        @click="markCancelled"
      >
        Cancel prospect
      </button>
    </div>

    <article class="card" style="margin-bottom: 1rem">
      <h2>Details</h2>
      <p><strong>Channel</strong> · {{ row.channel || "—" }}</p>
      <p><strong>Pain</strong> · {{ row.potential_problem || "—" }}</p>
      <p><strong>Next</strong> · {{ row.next_action || "—" }}</p>
      <p><strong>Follow-up</strong> · {{ row.follow_up_date || "—" }}</p>
      <p v-if="row.notes" style="white-space: pre-wrap">{{ row.notes }}</p>
    </article>

    <ProgressForm :statuses="PROSPECT_STATUSES" :current="row.status" :save="onProgress" />

    <article class="card" style="margin-top: 1rem">
      <h2>Timeline</h2>
      <div class="timeline">
        <div v-for="event in events" :key="event.id" class="event">
          <div class="row">
            <StatusPill :value="event.status" />
            <span class="muted">{{ formatWhen(event.created_at) }}</span>
          </div>
          <p v-if="event.note">{{ event.note }}</p>
        </div>
        <p v-if="!events.length" class="muted">No progress yet.</p>
      </div>
    </article>
  </section>
  <p v-else-if="error" class="flash">{{ error }}</p>
  <p v-else class="muted">Loading…</p>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import ProgressForm from "../components/ProgressForm.vue";
import StatusPill from "../components/StatusPill.vue";
import { PROSPECT_STATUSES, formatWhen } from "../constants";

const route = useRoute();
const router = useRouter();
const row = ref(null);
const events = ref([]);
const error = ref("");

async function load() {
  const id = route.params.id;
  row.value = await api(`/api/prospects/${id}`);
  events.value = await api(`/api/progress?entity_type=prospect&entity_id=${id}`);
}

async function onProgress(payload) {
  const id = route.params.id;
  await api(`/api/prospects/${id}/progress`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await load();
}

async function markCancelled() {
  const reason = window.prompt("Why cancel this prospect?") ?? "";
  if (!reason.trim()) return;
  await onProgress({
    status: "cancelled",
    note: reason.trim(),
  });
  router.push("/prospects");
}

onMounted(async () => {
  try {
    await load();
  } catch (err) {
    error.value = err.message;
  }
});
</script>
