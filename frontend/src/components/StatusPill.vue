<template>
  <span class="pill" :class="value">{{ labelize(value) }}</span>
</template>

<script setup>
import { labelize } from "../constants";

defineProps({
  value: { type: String, required: true },
});
</script>
