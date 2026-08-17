<template>
  <section>
    <div class="page-head">
      <div>
        <h1>Jobs</h1>
        <p class="muted">Scraped boards plus manual LinkedIn / URL paste.</p>
      </div>
      <button type="button" class="secondary" :disabled="saving" @click="showForm = !showForm">
        {{ showForm ? "Hide form" : "Add job" }}
      </button>
    </div>

    <form v-if="showForm" class="card" style="margin: 1rem 0" @submit.prevent="createJob">
      <h2>Manual job (LinkedIn OK)</h2>
      <div class="form-grid">
        <label>Title <input v-model="form.title" required /></label>
        <label>Company <input v-model="form.company_name" /></label>
        <label>
          Source
          <select v-model="form.source">
            <option value="linkedin">linkedin</option>
            <option value="manual">manual</option>
            <option value="upwork">upwork</option>
          </select>
        </label>
        <label>Location <input v-model="form.location" placeholder="Remote / country" /></label>
        <label>Listed on <input v-model="form.posted_at" type="date" /></label>
        <label>Deadline <input v-model="form.deadline_at" type="date" /></label>
        <label>Salary <input v-model="form.salary_text" placeholder="e.g. $90k–120k" /></label>
        <label>
          Employment
          <select v-model="form.employment_type">
            <option value="">Unknown</option>
            <option value="full-time">full-time</option>
            <option value="part-time">part-time</option>
            <option value="contract">contract</option>
            <option value="freelance">freelance</option>
            <option value="internship">internship</option>
          </select>
        </label>
        <label>Department <input v-model="form.department" /></label>
        <label>Seniority <input v-model="form.seniority" placeholder="mid / senior" /></label>
        <label class="span-2">Tags <input v-model="form.tags" placeholder="python, etl, remote" /></label>
        <label class="span-2">URL <input v-model="form.url" type="url" placeholder="https://…" /></label>
        <label class="span-2">Apply URL <input v-model="form.apply_url" type="url" placeholder="optional" /></label>
        <label class="span-2">
          Description
          <textarea v-model="form.description" required placeholder="Paste the posting" />
        </label>
        <label class="span-2">
          First note
          <textarea v-model="form.notes" placeholder="Optional: why this role, when you saw it" />
        </label>
      </div>
      <div class="row" style="margin-top: 0.8rem">
        <button type="submit" :disabled="saving">
          {{ saving ? "Saving…" : "Save job" }}
        </button>
        <span v-if="saving" class="muted" aria-live="polite">Saving job…</span>
        <span v-else-if="formError" class="flash">{{ formError }}</span>
      </div>
    </form>

    <div class="toolbar">
      <label class="field field-search">
        <span>Search</span>
        <input v-model="q" placeholder="Title or description" @keyup.enter="load" />
      </label>
      <label class="field">
        <span>Status</span>
        <select v-model="status" @change="load">
          <option value="">Active (hide not related)</option>
          <option v-for="item in JOB_STATUSES" :key="item" :value="item">{{ labelize(item) }}</option>
        </select>
      </label>
      <label class="field">
        <span>Source</span>
        <select v-model="source" @change="load">
          <option value="">All sources</option>
          <option value="linkedin">linkedin</option>
          <option value="remoteok">remoteok</option>
          <option value="arbeitnow">arbeitnow</option>
          <option value="greenhouse">greenhouse</option>
          <option value="lever">lever</option>
          <option value="weworkremotely">weworkremotely</option>
          <option value="manual">manual</option>
        </select>
      </label>
      <label class="field">
        <span>Sort</span>
        <select v-model="sortKey" @change="sortDir = defaultSortDir(sortKey)">
          <option value="listed">Listed date</option>
          <option value="added">Added time</option>
          <option value="deadline">Deadline</option>
          <option value="title">Role</option>
          <option value="company">Company</option>
          <option value="source">Source</option>
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
    <div v-if="selectedCount" class="bulk-bar">
      <span>{{ selectedCount }} selected</span>
      <button type="button" class="secondary" @click="clearSelection">Clear</button>
      <button type="button" class="danger" :disabled="bulkMarking" @click="markSelectedNotRelated">
        {{ bulkMarking ? "Saving…" : "Not related" }}
      </button>
    </div>
    <table class="table">
      <thead>
        <tr>
          <th class="check">
            <input
              type="checkbox"
              :checked="allSelected"
              :indeterminate.prop="partialSelected"
              :disabled="!selectableJobs.length"
              aria-label="Select all visible jobs"
              @click.stop
              @change.stop="onSelectAllChange"
            />
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'title' }" @click="toggleSort('title')">
              Role{{ sortMark(sortKey, "title", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'company' }" @click="toggleSort('company')">
              Company{{ sortMark(sortKey, "company", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'listed' }" @click="toggleSort('listed')">
              Listed{{ sortMark(sortKey, "listed", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'added' }" @click="toggleSort('added')">
              Added{{ sortMark(sortKey, "added", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'deadline' }" @click="toggleSort('deadline')">
              Deadline{{ sortMark(sortKey, "deadline", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'source' }" @click="toggleSort('source')">
              Source{{ sortMark(sortKey, "source", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'status' }" @click="toggleSort('status')">
              Status{{ sortMark(sortKey, "status", sortDir) }}
            </button>
          </th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="job in sortedJobs"
          :key="job.id"
          class="clickable"
          :class="{ selected: selected.has(job.id) }"
          @click="onRowClick(job, $event)"
        >
          <td class="check" @click.stop="onCheckCellClick(job, $event)">
            <input
              type="checkbox"
              :checked="selected.has(job.id)"
              :disabled="job.status === 'not_related'"
              :aria-label="`Select ${job.title}`"
              @click.stop
              @change="onCheckChange(job.id, $event)"
            />
          </td>
          <td>
            <div>{{ job.title }}</div>
            <div v-if="job.salary_text" class="mono muted">{{ job.salary_text }}</div>
          </td>
          <td>{{ job.company_name || "—" }}</td>
          <td class="mono">{{ formatDate(job.posted_at) }}</td>
          <td class="mono">{{ formatWhen(job.created_at || job.discovered_at) }}</td>
          <td class="mono" :class="{ flash: isPastDeadline(job.deadline_at) }">
            {{ formatDate(job.deadline_at) }}
          </td>
          <td class="mono">{{ job.source }}</td>
          <td><StatusPill :value="job.status" /></td>
          <td class="actions" @click.stop>
            <button
              v-if="job.status !== 'not_related'"
              type="button"
              class="danger row-action"
              :disabled="marking.has(job.id) || bulkMarking"
              @click="markNotRelated(job)"
            >
              {{ marking.has(job.id) ? "Saving…" : "Not related" }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="!sortedJobs.length" class="muted">No jobs match this filter.</p>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import StatusPill from "../components/StatusPill.vue";
import {
  JOB_STATUSES,
  defaultSortDir,
  formatDate,
  formatWhen,
  isPastDeadline,
  labelize,
  sortBy,
  sortMark,
} from "../constants";

const router = useRouter();
const jobs = ref([]);
const q = ref("");
const status = ref("");
const source = ref("");
const sortKey = ref("listed");
const sortDir = ref("desc");
const error = ref("");
const formError = ref("");
const saving = ref(false);
const showForm = ref(false);
const marking = ref(new Set());
const selected = ref(new Set());
const lastClickedId = ref("");
const bulkMarking = ref(false);
const form = reactive({
  title: "",
  company_name: "",
  source: "linkedin",
  location: "Remote",
  url: "",
  apply_url: "",
  description: "",
  notes: "",
  posted_at: "",
  deadline_at: "",
  salary_text: "",
  employment_type: "",
  department: "",
  seniority: "",
  tags: "",
});

const sortedJobs = computed(() =>
  sortBy(jobs.value, sortKey.value, sortDir.value, {
    listed: (job) => job.posted_at,
    added: (job) => job.created_at || job.discovered_at,
    deadline: (job) => job.deadline_at,
    title: (job) => job.title,
    company: (job) => job.company_name,
    source: (job) => job.source,
    status: (job) => job.status,
  }),
);

const selectableJobs = computed(() =>
  sortedJobs.value.filter((job) => job.status !== "not_related"),
);
const selectedCount = computed(() => selected.value.size);
const allSelected = computed(
  () => selectableJobs.value.length > 0 && selectableJobs.value.every((job) => selected.value.has(job.id)),
);
const partialSelected = computed(
  () => selectedCount.value > 0 && !allSelected.value,
);

function visibleIds() {
  return selectableJobs.value.map((job) => job.id);
}

function pruneSelection(ids) {
  const allowed = new Set(ids);
  selected.value = new Set([...selected.value].filter((id) => allowed.has(id)));
}

function setSelected(jobId, on, event) {
  const next = new Set(selected.value);
  if (event?.shiftKey && lastClickedId.value) {
    const ids = visibleIds();
    const start = ids.indexOf(lastClickedId.value);
    const end = ids.indexOf(jobId);
    if (start >= 0 && end >= 0) {
      const [from, to] = start < end ? [start, end] : [end, start];
      for (const id of ids.slice(from, to + 1)) next.add(id);
      selected.value = next;
      lastClickedId.value = jobId;
      return;
    }
  }
  if (on) next.add(jobId);
  else next.delete(jobId);
  selected.value = next;
  lastClickedId.value = jobId;
}

function onCheckChange(jobId, event) {
  setSelected(jobId, event.target.checked, event);
}

function onCheckCellClick(job, event) {
  if (event.target.closest("input") || job.status === "not_related") return;
  setSelected(job.id, !selected.value.has(job.id), event);
}

function onSelectAllChange(event) {
  selected.value = event.target.checked ? new Set(visibleIds()) : new Set();
}

function clearSelection() {
  selected.value = new Set();
}

function onRowClick(job, event) {
  if (event.target.closest("input, button, a, .actions, .check")) return;
  if (selected.value.size) {
    if (job.status === "not_related") return;
    setSelected(job.id, !selected.value.has(job.id), event);
    return;
  }
  router.push(`/jobs/${job.id}`);
}

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
    return;
  }
  sortKey.value = key;
  sortDir.value = defaultSortDir(key);
}

function toIsoDate(value) {
  if (!value) return null;
  return `${value}T00:00:00Z`;
}

async function load() {
  error.value = "";
  const params = new URLSearchParams();
  if (q.value) params.set("q", q.value);
  if (status.value) params.set("status", status.value);
  if (source.value) params.set("source", source.value);
  const suffix = params.toString() ? `?${params}` : "";
  try {
    const rows = await api(`/api/jobs${suffix}`);
    jobs.value = status.value
      ? rows
      : rows.filter((job) => job.status !== "not_related");
    pruneSelection(jobs.value.map((job) => job.id));
  } catch (err) {
    error.value = err.message;
  }
}

async function markNotRelated(job) {
  const reason = window.prompt("Why is this not related? (optional)");
  if (reason === null) return;
  error.value = "";
  marking.value = new Set(marking.value).add(job.id);
  try {
    await api(`/api/jobs/${job.id}/progress`, {
      method: "POST",
      body: JSON.stringify({
        status: "not_related",
        note: reason.trim() || "Marked not related",
      }),
    });
    jobs.value = jobs.value.filter((row) => row.id !== job.id);
    pruneSelection(jobs.value.map((row) => row.id));
  } catch (err) {
    error.value = err.message;
  } finally {
    const next = new Set(marking.value);
    next.delete(job.id);
    marking.value = next;
  }
}

async function markSelectedNotRelated() {
  const ids = [...selected.value];
  if (!ids.length) return;
  const reason = window.prompt(
    `Mark ${ids.length} job${ids.length === 1 ? "" : "s"} as not related? Optional reason:`,
  );
  if (reason === null) return;
  error.value = "";
  bulkMarking.value = true;
  try {
    const result = await api("/api/jobs/not-related", {
      method: "POST",
      body: JSON.stringify({
        job_ids: ids,
        note: reason.trim() || "Marked not related",
      }),
    });
    const gone = new Set(result.dismissed || []);
    jobs.value = jobs.value.filter((row) => !gone.has(row.id));
    selected.value = new Set();
    if ((result.missing || []).length) {
      error.value = `${result.missing.length} selected job${result.missing.length === 1 ? " was" : "s were"} already gone.`;
    }
  } catch (err) {
    error.value = err.message;
  } finally {
    bulkMarking.value = false;
  }
}

async function createJob() {
  formError.value = "";
  saving.value = true;
  try {
    const tags = form.tags
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify({
        title: form.title,
        company_name: form.company_name || null,
        source: form.source,
        location: form.location || null,
        url: form.url || null,
        apply_url: form.apply_url || null,
        description: form.description,
        notes: form.notes || null,
        posted_at: toIsoDate(form.posted_at),
        deadline_at: toIsoDate(form.deadline_at),
        salary_text: form.salary_text || null,
        employment_type: form.employment_type || null,
        department: form.department || null,
        seniority: form.seniority || null,
        tags,
        remote_type: "remote",
      }),
    });
    Object.assign(form, {
      title: "",
      company_name: "",
      url: "",
      apply_url: "",
      description: "",
      notes: "",
      posted_at: "",
      deadline_at: "",
      salary_text: "",
      employment_type: "",
      department: "",
      seniority: "",
      tags: "",
    });
    showForm.value = false;
    await load();
  } catch (err) {
    formError.value = err.message;
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>
