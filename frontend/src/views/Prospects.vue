<template>
  <section>
    <div class="page-head">
      <div>
        <h1>Prospects</h1>
        <p class="muted">Services pipeline from the Operational Intelligence Brief offer.</p>
      </div>
      <button type="button" class="secondary" @click="showForm = !showForm">
        {{ showForm ? "Hide form" : "Add prospect" }}
      </button>
    </div>

    <form v-if="showForm" class="card form-card" @submit.prevent="createProspect">
      <h2>New prospect</h2>
      <div class="form-body">
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
      <div class="form-actions">
        <button type="submit">Save prospect</button>
        <span v-if="formError" class="flash">{{ formError }}</span>
      </div>
      </div>
    </form>

    <div class="toolbar">
      <label class="field field-search">
        <span>Search</span>
        <input v-model="q" placeholder="Name or company" @keyup.enter="load" />
      </label>
      <label class="field">
        <span>Status</span>
        <select v-model="status" @change="load">
          <option value="">Active (hide cancelled)</option>
          <option v-for="item in PROSPECT_STATUSES" :key="item" :value="item">{{ labelize(item) }}</option>
        </select>
      </label>
      <label class="field">
        <span>Package</span>
        <select v-model="packageFilter" @change="load">
          <option value="">All packages</option>
          <option v-for="item in PACKAGES" :key="item" :value="item">{{ PACKAGE_LABELS[item] }}</option>
        </select>
      </label>
      <label class="field">
        <span>Sort</span>
        <select v-model="sortKey" @change="sortDir = defaultSortDir(sortKey)">
          <option value="updated">Updated</option>
          <option value="follow_up">Follow-up</option>
          <option value="name">Name</option>
          <option value="company">Company</option>
          <option value="package">Package</option>
          <option value="status">Status</option>
          <option value="value">Value</option>
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
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'name' }" @click="toggleSort('name')">
              Name{{ sortMark(sortKey, "name", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'company' }" @click="toggleSort('company')">
              Company{{ sortMark(sortKey, "company", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'package' }" @click="toggleSort('package')">
              Package{{ sortMark(sortKey, "package", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'status' }" @click="toggleSort('status')">
              Status{{ sortMark(sortKey, "status", sortDir) }}
            </button>
          </th>
          <th>
            <button type="button" class="sort-btn" :class="{ active: sortKey === 'follow_up' }" @click="toggleSort('follow_up')">
              Follow-up{{ sortMark(sortKey, "follow_up", sortDir) }}
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in sortedRows"
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
    <p v-if="!sortedRows.length" class="muted">No prospects match this filter.</p>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import StatusPill from "../components/StatusPill.vue";
import {
  PACKAGES,
  PACKAGE_LABELS,
  PROSPECT_STATUSES,
  defaultSortDir,
  labelize,
  sortBy,
  sortMark,
} from "../constants";

const rows = ref([]);
const q = ref("");
const status = ref("");
const packageFilter = ref("");
const sortKey = ref("updated");
const sortDir = ref("desc");
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

const sortedRows = computed(() =>
  sortBy(rows.value, sortKey.value, sortDir.value, {
    updated: (row) => row.updated_at,
    follow_up: (row) => row.follow_up_date,
    name: (row) => row.name,
    company: (row) => row.company,
    package: (row) => row.package,
    status: (row) => row.status,
    value: (row) => row.value_estimate_usd,
  }),
);

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
