<template>
  <section v-if="row">
    <p class="mono muted">
      <router-link to="/posts">← Posts</router-link>
    </p>
    <h1>{{ row.title }}</h1>
    <p v-if="row.summary" class="muted">{{ row.summary }}</p>
    <div class="row">
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

    <article class="card">
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
      <div v-if="(row.tags || []).length" class="row">
        <span v-for="tag in row.tags" :key="tag" class="pill">{{ tag }}</span>
      </div>
      <p v-if="row.cover_url">
        <img :src="row.cover_url" alt="" style="max-width: 100%; border-radius: 8px" />
      </p>
      <p v-if="row.notes" style="white-space: pre-wrap">{{ row.notes }}</p>
    </article>

    <form class="card form-card" @submit.prevent="savePost">
      <h2>Edit post</h2>
      <div class="form-body">
        <div class="form-grid">
          <label class="span-2">Title <input v-model="edit.title" required /></label>
          <label class="span-2">Summary <input v-model="edit.summary" /></label>
          <label class="span-2">Body <textarea v-model="edit.body" rows="6" /></label>
          <label>Tags <input v-model="edit.tags" placeholder="career, freelance" /></label>
          <label>Cover URL <input v-model="edit.cover_url" type="url" /></label>
          <label>Canonical URL <input v-model="edit.canonical_url" type="url" /></label>
          <label>Scheduled <input v-model="edit.scheduled_at" type="datetime-local" /></label>
          <fieldset class="span-2">
            <legend>Publish to</legend>
            <div class="row">
              <label v-for="item in POST_CHANNELS" :key="item" class="inline">
                <input v-model="edit.channels" type="checkbox" :value="item" />
                {{ labelize(item) }}
              </label>
            </div>
          </fieldset>
          <label>Web URL <input v-model="edit.web_url" type="url" /></label>
          <label>LinkedIn URL <input v-model="edit.linkedin_url" type="url" /></label>
          <label class="span-2">Notes <textarea v-model="edit.notes" /></label>
        </div>

        <section class="form-section">
          <h3 class="form-section-title">Media</h3>
          <div class="form-media-list">
            <div v-for="(item, index) in edit.media" :key="index" class="form-media-row form-grid">
              <label>
                Kind
                <select v-model="item.kind">
                  <option v-for="kind in MEDIA_KINDS" :key="kind" :value="kind">{{ labelize(kind) }}</option>
                </select>
              </label>
              <label>URL <input v-model="item.url" type="url" /></label>
              <label class="span-2">Caption <input v-model="item.caption" /></label>
            </div>
          </div>
          <button type="button" class="secondary" @click="addMedia">Add media</button>
        </section>

        <div class="form-actions">
          <button type="submit" :disabled="saving">
            {{ saving ? "Saving…" : "Save changes" }}
          </button>
          <span v-if="saving" class="muted" aria-live="polite">Saving changes…</span>
          <span v-else-if="saved" class="ok" aria-live="polite">Saved.</span>
          <span v-else-if="editError" class="flash">{{ editError }}</span>
        </div>
      </div>
    </form>

    <article v-if="(row.media_json || []).length" class="card">
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

    <article class="card">
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
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import DescriptionBody from "../components/DescriptionBody.vue";
import ProgressForm from "../components/ProgressForm.vue";
import StatusPill from "../components/StatusPill.vue";
import { MEDIA_KINDS, POST_CHANNELS, POST_STATUSES, formatWhen, labelize } from "../constants";

const route = useRoute();
const router = useRouter();
const row = ref(null);
const events = ref([]);
const error = ref("");
const editError = ref("");
const saved = ref(false);
const saving = ref(false);
let savedTimer;
const edit = reactive(emptyEdit());

function emptyEdit() {
  return {
    title: "",
    summary: "",
    body: "",
    tags: "",
    cover_url: "",
    canonical_url: "",
    notes: "",
    channels: [],
    web_url: "",
    linkedin_url: "",
    scheduled_at: "",
    media: [{ kind: "image", url: "", caption: "" }],
  };
}

function toDatetimeLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}

function toIso(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function syncEdit(post) {
  edit.title = post.title || "";
  edit.summary = post.summary || "";
  edit.body = post.body || "";
  edit.tags = (post.tags || []).join(", ");
  edit.cover_url = post.cover_url || "";
  edit.canonical_url = post.canonical_url || "";
  edit.notes = post.notes || "";
  edit.channels = [...(post.channels || [])];
  edit.web_url = post.web_url || "";
  edit.linkedin_url = post.linkedin_url || "";
  edit.scheduled_at = toDatetimeLocal(post.scheduled_at);
  const media = (post.media_json || []).map((item) => ({
    kind: item.kind || "image",
    url: item.url || "",
    caption: item.caption || "",
  }));
  edit.media = media.length ? media : [{ kind: "image", url: "", caption: "" }];
}

function addMedia() {
  edit.media.push({ kind: "image", url: "", caption: "" });
}

async function load() {
  const id = route.params.id;
  row.value = await api(`/api/posts/${id}`);
  events.value = await api(`/api/progress?entity_type=post&entity_id=${id}`);
  syncEdit(row.value);
}

async function savePost() {
  saving.value = true;
  editError.value = "";
  saved.value = false;
  try {
    const tags = edit.tags
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const media_json = edit.media
      .filter((item) => item.url.trim())
      .map((item) => ({
        kind: item.kind,
        url: item.url.trim(),
        caption: item.caption.trim() || null,
      }));
    row.value = await api(`/api/posts/${route.params.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        title: edit.title,
        summary: edit.summary || null,
        body: edit.body || null,
        tags,
        cover_url: edit.cover_url || null,
        canonical_url: edit.canonical_url || null,
        notes: edit.notes || null,
        channels: edit.channels,
        web_url: edit.web_url || null,
        linkedin_url: edit.linkedin_url || null,
        scheduled_at: toIso(edit.scheduled_at),
        media_json,
      }),
    });
    syncEdit(row.value);
    saved.value = true;
    clearTimeout(savedTimer);
    savedTimer = setTimeout(() => {
      saved.value = false;
    }, 4000);
  } catch (err) {
    editError.value = err.message;
  } finally {
    saving.value = false;
  }
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
