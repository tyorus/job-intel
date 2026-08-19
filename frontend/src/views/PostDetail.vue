<template>
  <section v-if="row">
    <p class="mono muted">
      <router-link to="/posts">← Posts</router-link>
    </p>
    <h1>{{ row.title }}</h1>
    <p v-if="row.summary" class="muted">{{ row.summary }}</p>
    <div class="row" style="margin: 0.6rem 0 1rem">
      <StatusPill :value="row.status" />
      <span v-for="item in row.channels || []" :key="item" class="pill">{{ labelize(item) }}</span>
      <a v-if="row.web_url" class="btn secondary" :href="row.web_url" target="_blank" rel="noreferrer">Open web</a>
      <a
        v-if="row.linkedin_url"
        class="btn secondary"
        :href="row.linkedin_url"
        target="_blank"
        rel="noreferrer"
      >
        Open LinkedIn
      </a>
      <button
        v-if="row.status !== 'archived'"
        type="button"
        class="danger"
        @click="markArchived"
      >
        Archive
      </button>
    </div>

    <article class="card" style="margin-bottom: 1rem">
      <h2>Metadata</h2>
      <div class="meta-grid">
        <div>
          <p class="mono muted">Scheduled</p>
          <p>{{ formatWhen(row.scheduled_at) }}</p>
        </div>
        <div>
          <p class="mono muted">Published</p>
          <p>{{ formatWhen(row.published_at) }}</p>
        </div>
        <div>
          <p class="mono muted">Updated</p>
          <p>{{ formatWhen(row.updated_at) }}</p>
        </div>
        <div>
          <p class="mono muted">Canonical</p>
          <p>
            <a v-if="row.canonical_url" :href="row.canonical_url" target="_blank" rel="noreferrer">
              {{ row.canonical_url }}
            </a>
            <span v-else>—</span>
          </p>
        </div>
      </div>
      <div v-if="(row.tags || []).length" class="row" style="margin-top: 0.8rem">
        <span v-for="tag in row.tags" :key="tag" class="pill">{{ tag }}</span>
      </div>
      <p v-if="row.cover_url" style="margin-top: 0.8rem">
        <img :src="row.cover_url" alt="" style="max-width: 100%; border-radius: 8px" />
      </p>
      <p v-if="row.notes" style="white-space: pre-wrap; margin-top: 0.8rem">{{ row.notes }}</p>
    </article>

    <article v-if="(row.media_json || []).length" class="card" style="margin-bottom: 1rem">
      <h2>Media</h2>
      <ul>
        <li v-for="(item, index) in row.media_json" :key="index">
          <StatusPill :value="item.kind" />
          <a :href="item.url" target="_blank" rel="noreferrer">{{ item.url }}</a>
          <span v-if="item.caption" class="muted"> — {{ item.caption }}</span>
        </li>
      </ul>
    </article>

    <DescriptionBody v-if="row.body" :text="row.body" />

    <ProgressForm :statuses="POST_STATUSES" :current="row.status" :save="onProgress" />

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
import DescriptionBody from "../components/DescriptionBody.vue";
import ProgressForm from "../components/ProgressForm.vue";
import StatusPill from "../components/StatusPill.vue";
import { POST_STATUSES, formatWhen, labelize } from "../constants";

const route = useRoute();
const router = useRouter();
const row = ref(null);
const events = ref([]);
const error = ref("");

async function load() {
  const id = route.params.id;
  row.value = await api(`/api/posts/${id}`);
  events.value = await api(`/api/progress?entity_type=post&entity_id=${id}`);
}

async function onProgress(payload) {
  const id = route.params.id;
  await api(`/api/posts/${id}/progress`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await load();
}

async function markArchived() {
  const reason = window.prompt("Why archive this post?") ?? "";
  if (!reason.trim()) return;
  await onProgress({
    status: "archived",
    note: reason.trim(),
  });
  router.push("/posts");
}

onMounted(async () => {
  try {
    await load();
  } catch (err) {
    error.value = err.message;
  }
});
</script>
