<template>
  <section>
    <div class="page-head">
      <div>
        <h1>Posts</h1>
        <p class="muted">Articles and media published to the web or LinkedIn.</p>
      </div>
      <button type="button" class="secondary" @click="showForm = !showForm">
        {{ showForm ? "Hide form" : "Add post" }}
      </button>
    </div>

    <form v-if="showForm" class="card" style="margin: 1rem 0" @submit.prevent="createPost">
      <h2>New post</h2>
      <div class="form-grid">
        <label>Title <input v-model="form.title" required /></label>
        <label>
          Status
          <select v-model="form.status">
            <option v-for="item in POST_STATUSES" :key="item" :value="item">{{ labelize(item) }}</option>
          </select>
        </label>
        <label class="span-2">Summary <input v-model="form.summary" /></label>
        <label class="span-2">Body <textarea v-model="form.body" rows="6" /></label>
        <label>Tags <input v-model="form.tags" placeholder="career, freelance" /></label>
        <label>Cover URL <input v-model="form.cover_url" type="url" /></label>
        <label>Canonical URL <input v-model="form.canonical_url" type="url" /></label>
        <label>Scheduled <input v-model="form.scheduled_at" type="datetime-local" /></label>
        <fieldset class="span-2">
          <legend>Publish to</legend>
          <div class="row">
            <label v-for="item in POST_CHANNELS" :key="item" class="inline">
              <input v-model="form.channels" type="checkbox" :value="item" />
              {{ labelize(item) }}
            </label>
          </div>
        </fieldset>
        <label>Web URL <input v-model="form.web_url" type="url" /></label>
        <label>LinkedIn URL <input v-model="form.linkedin_url" type="url" /></label>
        <label class="span-2">Notes <textarea v-model="form.notes" /></label>
      </div>

      <h3 style="margin: 1rem 0 0.5rem">Media</h3>
      <div v-for="(item, index) in form.media" :key="index" class="form-grid" style="margin-bottom: 0.6rem">
        <label>
          Kind
          <select v-model="item.kind">
            <option v-for="kind in MEDIA_KINDS" :key="kind" :value="kind">{{ labelize(kind) }}</option>
          </select>
        </label>
        <label>URL <input v-model="item.url" type="url" /></label>
        <label class="span-2">Caption <input v-model="item.caption" /></label>
      </div>
      <button type="button" class="secondary" @click="addMedia">Add media</button>

      <div class="row" style="margin-top: 0.8rem">
        <button type="submit">Save post</button>
        <span v-if="formError" class="flash">{{ formError }}</span>
      </div>
    </form>

    <div class="toolbar">
      <label class="field field-search">
        <span>Search</span>
        <input v-model="q" placeholder="Title or summary" @keyup.enter="load" />
      </label>
      <label class="field">
        <span>Status</span>
        <select v-model="status" @change="load">
          <option value="">Active (hide archived)</option>
          <option v-for="item in POST_STATUSES" :key="item" :value="item">{{ labelize(item) }}</option>
        </select>
      </label>
      <label class="field">
        <span>Channel</span>
        <select v-model="channel" @change="load">
          <option value="">All channels</option>
          <option v-for="item in POST_CHANNELS" :key="item" :value="item">{{ labelize(item) }}</option>
        </select>
      </label>
      <label class="field">
        <span>Sort</span>
        <select v-model="sortKey" @change="sortDir = defaultSortDir(sortKey)">
          <option value="updated">Updated</option>
          <option value="published">Published</option>
          <option value="title">Title</option>
          <option value="status">Status</option>
        </select>
      </label>
      <label class="field">
        <span>Order</span>
        <select v-model="sortDir">
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </label>
      <div class="field field-actions">
        <span>&nbsp;</span>
        <button type="button" class="secondary" @click="load">Filter</button>
      </div>
    </div>

    <p v-if="error" class="flash">{{ error }}</p>
    <table class="table">
      <thead>
        <tr>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'title' }" @click="toggleSort('title')">
              Title{{ sortMark(sortKey, "title", sortDir) }}
            </button>
          </th>
          <th>Channels</th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'status' }" @click="toggleSort('status')">
              Status{{ sortMark(sortKey, "status", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'published' }" @click="toggleSort('published')">
              Published{{ sortMark(sortKey, "published", sortDir) }}
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in sortedRows"
          :key="row.id"
          class="clickable"
          @click="$router.push(`/posts/${row.id}`)"
        >
          <td>{{ row.title }}</td>
          <td>{{ (row.channels || []).join(" · ") || "—" }}</td>
          <td><StatusPill :value="row.status" /></td>
          <td class="mono">{{ formatWhen(row.published_at) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!sortedRows.length" class="muted">No posts match this filter.</p>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import StatusPill from "../components/StatusPill.vue";
import {
  MEDIA_KINDS,
  POST_CHANNELS,
  POST_STATUSES,
  defaultSortDir,
  formatWhen,
  labelize,
  sortBy,
  sortMark,
} from "../constants";

const rows = ref([]);
const q = ref("");
const status = ref("");
const channel = ref("");
const sortKey = ref("updated");
const sortDir = ref("desc");
const error = ref("");
const formError = ref("");
const showForm = ref(false);
const form = reactive(emptyForm());

const sortedRows = computed(() =>
  sortBy(rows.value, sortKey.value, sortDir.value, {
    updated: (row) => row.updated_at,
    published: (row) => row.published_at,
    title: (row) => row.title,
    status: (row) => row.status,
  }),
);

function emptyForm() {
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
    status: "idea",
    media: [{ kind: "image", url: "", caption: "" }],
  };
}

function addMedia() {
  form.media.push({ kind: "image", url: "", caption: "" });
}

function toIso(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
    return;
  }
  sortKey.value = key;
  sortDir.value = defaultSortDir(key);
}

async function load() {
  error.value = "";
  const params = new URLSearchParams();
  if (q.value) params.set("q", q.value);
  if (status.value) params.set("status", status.value);
  if (channel.value) params.set("channel", channel.value);
  const suffix = params.toString() ? `?${params}` : "";
  try {
    const list = await api(`/api/posts${suffix}`);
    rows.value = status.value ? list : list.filter((row) => row.status !== "archived");
  } catch (err) {
    error.value = err.message;
  }
}

async function createPost() {
  formError.value = "";
  try {
    const tags = form.tags
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const media_json = form.media
      .filter((item) => item.url.trim())
      .map((item) => ({
        kind: item.kind,
        url: item.url.trim(),
        caption: item.caption.trim() || null,
      }));
    await api("/api/posts", {
      method: "POST",
      body: JSON.stringify({
        title: form.title,
        summary: form.summary || null,
        body: form.body || null,
        tags,
        cover_url: form.cover_url || null,
        canonical_url: form.canonical_url || null,
        notes: form.notes || null,
        channels: form.channels,
        web_url: form.web_url || null,
        linkedin_url: form.linkedin_url || null,
        scheduled_at: toIso(form.scheduled_at),
        status: form.status,
        media_json,
      }),
    });
    Object.assign(form, emptyForm());
    showForm.value = false;
    await load();
  } catch (err) {
    formError.value = err.message;
  }
}

onMounted(load);
</script>
