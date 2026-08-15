<template>
  <section v-if="job">
    <p class="mono muted">
      <router-link to="/jobs">← Jobs</router-link>
    </p>
    <h1>{{ job.title }}</h1>
    <p class="muted">{{ job.company_name || "Unknown company" }} · {{ job.location || "—" }}</p>
    <div class="row" style="margin: 0.6rem 0 1rem">
      <StatusPill :value="job.status" />
      <span class="pill">{{ job.source }}</span>
      <span v-if="job.remote_type" class="pill">{{ labelize(job.remote_type) }}</span>
      <a v-if="job.url" class="btn secondary" :href="job.url" target="_blank" rel="noreferrer">Open posting</a>
      <a
        v-if="job.apply_url"
        class="btn secondary"
        :href="job.apply_url"
        target="_blank"
        rel="noreferrer"
      >
        Apply link
      </a>
      <button
        v-if="job.status !== 'not_related'"
        type="button"
        class="danger"
        @click="markNotRelated"
      >
        Not related
      </button>
    </div>

    <article class="card" style="margin-bottom: 1rem">
      <h2>Listing metadata</h2>
      <div class="meta-grid">
        <div>
          <p class="mono muted">Listed / posted</p>
          <p>{{ formatWhen(job.posted_at) }}</p>
        </div>
        <div>
          <p class="mono muted">Discovered</p>
          <p>{{ formatWhen(job.discovered_at) }}</p>
        </div>
        <div>
          <p class="mono muted">Deadline</p>
          <p :class="{ flash: isPastDeadline(job.deadline_at) }">{{ formatWhen(job.deadline_at) }}</p>
        </div>
        <div>
          <p class="mono muted">Updated</p>
          <p>{{ formatWhen(job.updated_at) }}</p>
        </div>
        <div>
          <p class="mono muted">Salary</p>
          <p>{{ job.salary_text || "—" }}</p>
        </div>
        <div>
          <p class="mono muted">Employment</p>
          <p>{{ job.employment_type || "—" }}</p>
        </div>
        <div>
          <p class="mono muted">Department</p>
          <p>{{ job.department || "—" }}</p>
        </div>
        <div>
          <p class="mono muted">Seniority</p>
          <p>{{ job.seniority || "—" }}</p>
        </div>
        <div>
          <p class="mono muted">Country</p>
          <p>{{ job.country || "—" }}</p>
        </div>
        <div>
          <p class="mono muted">Source job ID</p>
          <p class="mono">{{ job.source_job_id || "—" }}</p>
        </div>
      </div>
      <div v-if="(job.tags || []).length" class="row" style="margin-top: 0.8rem">
        <span v-for="tag in job.tags" :key="tag" class="pill">{{ tag }}</span>
      </div>
      <details v-if="hasExtraMeta" style="margin-top: 0.9rem">
        <summary class="muted">Source extras</summary>
        <pre class="mono meta-json">{{ prettyMeta }}</pre>
      </details>
    </article>

    <form class="card" style="margin-bottom: 1rem" @submit.prevent="saveMeta">
      <h2>Edit dates &amp; metadata</h2>
      <div class="form-grid">
        <label>Listed on <input v-model="edit.posted_at" type="date" /></label>
        <label>Deadline <input v-model="edit.deadline_at" type="date" /></label>
        <label>Salary <input v-model="edit.salary_text" /></label>
        <label>Employment <input v-model="edit.employment_type" /></label>
        <label>Department <input v-model="edit.department" /></label>
        <label>Seniority <input v-model="edit.seniority" /></label>
        <label class="span-2">Tags <input v-model="edit.tags" placeholder="comma separated" /></label>
        <label class="span-2">Apply URL <input v-model="edit.apply_url" type="url" /></label>
      </div>
      <div class="row" style="margin-top: 0.8rem">
        <button type="submit" :disabled="saving">Save metadata</button>
        <span v-if="metaError" class="flash">{{ metaError }}</span>
      </div>
    </form>

    <ProgressForm :statuses="JOB_STATUSES" :current="job.status" :save="onProgress" />

    <article class="card" style="margin: 1rem 0">
      <h2>Timeline</h2>
      <div class="timeline">
        <div v-for="event in events" :key="event.id" class="event">
          <div class="row">
            <StatusPill :value="event.status" />
            <span class="muted">{{ formatWhen(event.created_at) }}</span>
          </div>
          <p v-if="event.note">{{ event.note }}</p>
        </div>
        <p v-if="!events.length" class="muted">No progress yet — submit an update above.</p>
      </div>
    </article>

    <DescriptionBody :text="job.description" />
  </section>
  <p v-else-if="error" class="flash">{{ error }}</p>
  <p v-else class="muted">Loading…</p>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import DescriptionBody from "../components/DescriptionBody.vue";
import ProgressForm from "../components/ProgressForm.vue";
import StatusPill from "../components/StatusPill.vue";
import {
  JOB_STATUSES,
  formatWhen,
  isPastDeadline,
  labelize,
} from "../constants";

const route = useRoute();
const router = useRouter();
const job = ref(null);
const events = ref([]);
const error = ref("");
const metaError = ref("");
const saving = ref(false);
const edit = reactive({
  posted_at: "",
  deadline_at: "",
  salary_text: "",
  employment_type: "",
  department: "",
  seniority: "",
  tags: "",
  apply_url: "",
});

const hasExtraMeta = computed(() => {
  const meta = job.value?.metadata_json || {};
  return Object.keys(meta).length > 0;
});

const prettyMeta = computed(() => JSON.stringify(job.value?.metadata_json || {}, null, 2));

function toDateInput(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 10);
}

function toIsoDate(value) {
  if (!value) return null;
  return `${value}T00:00:00Z`;
}

function syncEdit(row) {
  edit.posted_at = toDateInput(row.posted_at);
  edit.deadline_at = toDateInput(row.deadline_at);
  edit.salary_text = row.salary_text || "";
  edit.employment_type = row.employment_type || "";
  edit.department = row.department || "";
  edit.seniority = row.seniority || "";
  edit.tags = (row.tags || []).join(", ");
  edit.apply_url = row.apply_url || "";
}

async function load() {
  const id = route.params.id;
  job.value = await api(`/api/jobs/${id}`);
  events.value = await api(`/api/progress?entity_type=job&entity_id=${id}`);
  syncEdit(job.value);
}

async function onProgress(payload) {
  const id = route.params.id;
  await api(`/api/jobs/${id}/progress`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await router.push("/jobs");
}

async function saveMeta() {
  saving.value = true;
  metaError.value = "";
  try {
    const tags = edit.tags
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    job.value = await api(`/api/jobs/${route.params.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        posted_at: toIsoDate(edit.posted_at),
        deadline_at: toIsoDate(edit.deadline_at),
        salary_text: edit.salary_text || null,
        employment_type: edit.employment_type || null,
        department: edit.department || null,
        seniority: edit.seniority || null,
        apply_url: edit.apply_url || null,
        tags,
      }),
    });
    syncEdit(job.value);
  } catch (err) {
    metaError.value = err.message;
  } finally {
    saving.value = false;
  }
}

async function markNotRelated() {
  const reason = window.prompt("Why is this not related? (optional)") ?? "";
  await onProgress({
    status: "not_related",
    note: reason.trim() || "Marked not related",
  });
}

onMounted(async () => {
  try {
    await load();
  } catch (err) {
    error.value = err.message;
  }
});
</script>
