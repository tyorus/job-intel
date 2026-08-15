<template>
  <article class="card job-description-card">
    <h2>Description</h2>
    <div v-if="blocks.length" class="job-description">
      <template v-for="(block, index) in blocks" :key="index">
        <h3 v-if="block.type === 'h2'">{{ block.text }}</h3>
        <h4 v-else-if="block.type === 'h3'">{{ block.text }}</h4>
        <ul v-else-if="block.type === 'ul'">
          <li v-for="(item, itemIndex) in block.items" :key="itemIndex">{{ item }}</li>
        </ul>
        <p v-else>{{ block.text }}</p>
      </template>
    </div>
    <p v-else class="muted">No description.</p>
  </article>
</template>

<script setup>
import { computed } from "vue";
import { parseDescription } from "../description";

const props = defineProps({
  text: { type: String, default: "" },
});

const blocks = computed(() => parseDescription(props.text));
</script>
