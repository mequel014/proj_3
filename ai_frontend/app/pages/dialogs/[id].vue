<script setup>
const route = useRoute()
const dialogId = computed(() => Number(route.params.id))
</script>

<template>
  <div class="container">
    <!-- <h1 class="title is-4">Диалог #{{ dialogId }}</h1> -->
    <ChatWindow :dialog-id="dialogId" />
  </div>
</template>