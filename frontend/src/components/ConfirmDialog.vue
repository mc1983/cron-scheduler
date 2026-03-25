<template>
  <div class="modal-backdrop" @click="$emit('cancel')">
    <div class="modal-box modal-box-sm" @click.stop>
      <p class="confirm-message">{{ message }}</p>
      <div class="form-actions">
        <button class="btn-secondary" @click="$emit('cancel')">Cancel</button>
        <button class="btn-danger" @click="$emit('confirm')">Confirm</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ message: String })
defineEmits(['confirm', 'cancel'])
</script>
