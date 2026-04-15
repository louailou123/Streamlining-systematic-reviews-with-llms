<template>
  <div class="flex flex-column gap-3">
    <Textarea
      :model-value="modelValue"
      auto-resize
      rows="4"
      :placeholder="placeholder"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <p class="m-0 text-sm muted-copy line-height-3">
      {{ helperText }}
    </p>
  </div>
</template>

<script setup lang="ts">
import Textarea from 'primevue/textarea';

withDefaults(
  defineProps<{
    modelValue: string;
    placeholder?: string;
    helperText?: string;
  }>(),
  {
    placeholder: 'Add concise guidance for improving this step output.',
    helperText: 'Use this only when you want the current step rerun with your guidance.',
  },
);

defineEmits<{
  'update:modelValue': [value: string];
}>();
</script>
