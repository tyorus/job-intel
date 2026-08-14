<template>
  <section>
    <div class="row" style="justify-content: space-between">
      <div>
        <h1>Jobs</h1>
        <p class="muted">Scraped boards plus manual LinkedIn / URL paste.</p>
      </div>
      <button type="button" class="secondary" @click="showForm = !showForm">
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
        <button type="submit">Save job</button>
        <span v-if="formError" class="flash">{{ formError }}</span>
      </div>
    </form>

    <div class="toolbar">
      <input v-model="q" placeholder="Search title…" @keyup.enter="load" />
      <select v-model="status" @change="load">
        <option value="">Active (hide not related)</option>
        <option v-for="item in JOB_STATUSES" :key="item" :value="item">{{ labelize(item) }}</option>
      </select>
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
      <button type="button" class="secondary" @click="load">Filter</button>
    </div>

    <p v-if="error" class="flash">{{ error }}</p>
    <table class="table">
      <thead>
        <tr>
          <th>Role</th>
          <th>Company</th>
          <th>Listed</th>
          <th>Deadline</th>
          <th>Source</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="job in jobs" :key="job.id" class="clickable" @click="$router.push(`/jobs/${job.id}`)">
          <td>
            <div>{{ job.title }}</div>
            <div v-if="job.salary_text" class="mono muted">{{ job.salary_text }}</div>
          </td>
          <td>{{ job.company_name || "—" }}</td>
          <td class="mono">{{ formatDate(job.posted_at || job.discovered_at) }}</td>
          <td class="mono" :class="{ flash: isPastDeadline(job.deadline_at) }">
            {{ formatDate(job.deadline_at) }}
          </td>
          <td class="mono">{{ job.source }}</td>
          <td><StatusPill :value="job.status" /></td>
        </tr>
      </tbody>
    </table>
    <p v-if="!jobs.length" class="muted">No jobs match this filter.</p>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { api } from "../api";
import StatusPill from "../components/StatusPill.vue";
import { JOB_STATUSES, formatDate, isPastDeadline, labelize } from "../constants";

const jobs = ref([]);
const q = ref("");
const status = ref("");
const source = ref("");
const error = ref("");
const formError = ref("");
const showForm = ref(false);
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
  } catch (err) {
    error.value = err.message;
  }
}

async function createJob() {
  formError.value = "";
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
  }
}

onMounted(load);
</script>
