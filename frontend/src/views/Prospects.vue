<template>
  <section>
    <div class="row" style="justify-content: space-between">
      <div>
        <h1>Prospects</h1>
        <p class="muted">Services pipeline from the Operational Intelligence Brief offer.</p>
      </div>
      <button type="button" class="secondary" @click="showForm = !showForm">
        {{ showForm ? "Hide form" : "Add prospect" }}
      </button>
    </div>

    <form v-if="showForm" class="card" style="margin: 1rem 0" @submit.prevent="createProspect">
      <h2>New prospect</h2>
      <div class="form-grid">
        <label>Name <input v-model="form.name" required /></label>
        <label>Company <input v-model="form.company" /></label>
        <label>Role <input v-model="form.role" /></label>
        <label>Country <input v-model="form.country" /></label>
        <label>Channel <input v-model="form.channel" placeholder="linkedin / email / upwork" /></label>
        <label>
          Package
          <select v-model="form.package">
            <option v-for="item in PACKAGES" :key="item" :value="item">{{ PACKAGE_LABELS[item] }}</option>
          </select>
        </label>
        <label>Value (USD) <input v-model.number="form.value_estimate_usd" type="number" min="0" /></label>
        <label>Follow-up <input v-model="form.follow_up_date" type="date" /></label>
        <label class="span-2">Pain / problem <input v-model="form.potential_problem" /></label>
        <label class="span-2">Next action <input v-model="form.next_action" /></label>
        <label class="span-2">Notes <textarea v-model="form.notes" /></label>
      </div>
      <div class="row" style="margin-top: 0.8rem">
        <button type="submit">Save prospect</button>
        <span v-if="formError" class="flash">{{ formError }}</span>
      </div>
    </form>

    <div class="toolbar">
      <input v-model="q" placeholder="Search name or company…" @keyup.enter="load" />
      <select v-model="status" @change="load">
        <option value="">Active (hide cancelled)</option>
        <option v-for="item in PROSPECT_STATUSES" :key="item" :value="item">{{ labelize(item) }}</option>
      </select>
      <select v-model="packageFilter" @change="load">
        <option value="">All packages</option>
        <option v-for="item in PACKAGES" :key="item" :value="item">{{ PACKAGE_LABELS[item] }}</option>
      </select>
      <button type="button" class="secondary" @click="load">Filter</button>
    </div>

    <p v-if="error" class="flash">{{ error }}</p>
    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Company</th>
          <th>Package</th>
          <th>Status</th>
          <th>Follow-up</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="row.id"
          class="clickable"
          @click="$router.push(`/prospects/${row.id}`)"
        >
          <td>{{ row.name }}</td>
          <td>{{ row.company || "—" }}</td>
          <td><StatusPill :value="row.package" /></td>
          <td><StatusPill :value="row.status" /></td>
          <td class="mono">{{ row.follow_up_date || "—" }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="muted">No prospects match this filter.</p>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { api } from "../api";
import StatusPill from "../components/StatusPill.vue";
import { PACKAGES, PACKAGE_LABELS, PROSPECT_STATUSES, labelize } from "../constants";

const rows = ref([]);
const q = ref("");
const status = ref("");
const packageFilter = ref("");
const error = ref("");
const formError = ref("");
const showForm = ref(false);
const form = reactive({
  name: "",
  company: "",
  role: "",
  country: "",
  channel: "linkedin",
  package: "unknown",
  value_estimate_usd: null,
  follow_up_date: "",
  potential_problem: "",
  next_action: "",
  notes: "",
});

async function load() {
  error.value = "";
  const params = new URLSearchParams();
  if (q.value) params.set("q", q.value);
  if (status.value) params.set("status", status.value);
  if (packageFilter.value) params.set("package", packageFilter.value);
  const suffix = params.toString() ? `?${params}` : "";
  try {
    const list = await api(`/api/prospects${suffix}`);
    rows.value = status.value
      ? list
      : list.filter((row) => row.status !== "cancelled");
  } catch (err) {
    error.value = err.message;
  }
}

async function createProspect() {
  formError.value = "";
  try {
    await api("/api/prospects", {
      method: "POST",
      body: JSON.stringify({
        ...form,
        follow_up_date: form.follow_up_date || null,
        value_estimate_usd: form.value_estimate_usd || null,
      }),
    });
    Object.assign(form, {
      name: "",
      company: "",
      role: "",
      country: "",
      potential_problem: "",
      next_action: "",
      notes: "",
      follow_up_date: "",
      value_estimate_usd: null,
    });
    showForm.value = false;
    await load();
  } catch (err) {
    formError.value = err.message;
  }
}

onMounted(load);
</script>
