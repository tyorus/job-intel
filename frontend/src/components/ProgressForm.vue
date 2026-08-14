<template>
  <form class="card" @submit.prevent="submit">
    <h2>Submit progress</h2>
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
    <div class="row" style="margin-top: 0.8rem">
      <button type="submit" :disabled="busy">Save update</button>
      <span v-if="error" class="flash">{{ error }}</span>
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

watch(
  () => props.current,
  (value) => {
    status.value = value;
  },
);

async function submit() {
  busy.value = true;
  error.value = "";
  try {
    await props.save({ status: status.value, note: note.value || null });
    note.value = "";
  } catch (err) {
    error.value = err.message || "Failed";
  } finally {
    busy.value = false;
  }
}
</script>
