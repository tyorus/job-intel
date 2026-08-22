<template>
  <form class="card form-card" @submit.prevent="submit">
    <h2>Submit progress</h2>
    <div class="form-body">
    <div class="form-grid">
      <label>
        Status
        <select v-model="status">
          <option v-for="item in statuses" :key="item" :value="item">{{ labelize(item) }}</option>
        </select>
      </label>
      <label class="span-2">
        Note
        <textarea v-model="note" placeholder="What changed, where you applied, next step…" />
      </label>
    </div>
    <div class="form-actions">
      <button type="submit" :disabled="busy">
        {{ busy ? "Saving…" : "Save update" }}
      </button>
      <span v-if="busy" class="muted" aria-live="polite">Saving changes…</span>
      <span v-else-if="saved" class="ok" aria-live="polite">Saved.</span>
      <span v-else-if="error" class="flash">{{ error }}</span>
    </div>
    </div>
  </form>
</template>

<script setup>
import { ref, watch } from "vue";
import { labelize } from "../constants";

const props = defineProps({
  statuses: { type: Array, required: true },
  current: { type: String, default: "new" },
  save: { type: Function, required: true },
});

const status = ref(props.current);
const note = ref("");
const busy = ref(false);
const error = ref("");
const saved = ref(false);
let savedTimer;

watch(
  () => props.current,
  (value) => {
    status.value = value;
  },
);

async function submit() {
  busy.value = true;
  error.value = "";
  saved.value = false;
  try {
    await props.save({ status: status.value, note: note.value || null });
    note.value = "";
    saved.value = true;
    clearTimeout(savedTimer);
    savedTimer = setTimeout(() => {
      saved.value = false;
    }, 4000);
  } catch (err) {
    error.value = err.message || "Failed";
  } finally {
    busy.value = false;
  }
}
</script>
