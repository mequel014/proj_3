import { defineStore } from 'pinia'

export const useCharactersStore = defineStore('characters', () => {
  const list = ref([])
  const mine = ref([])
  const loading = ref(false)

  async function fetchPublic() {
    const { $api } = useNuxtApp()
    loading.value = true
    try {
      list.value = await $api('/characters')
    } finally {
      loading.value = false
    }
  }

  async function fetchMine() {
    const { $api } = useNuxtApp()
    loading.value = true
    try {
      mine.value = await $api('/characters?mine=true')
    } finally {
      loading.value = false
    }
  }

  async function createCharacter(payload) {
    const { $api } = useNuxtApp()
    return await $api('/characters', { method: 'POST', body: payload })
  }

  async function updateCharacter(id, payload) {
    const { $api } = useNuxtApp()
    return await $api(`/characters/${id}`, { method: 'PATCH', body: payload })
  }

  async function uploadPhoto(file) {
    const apiBase = useRuntimeConfig().public.apiBase
    const form = new FormData()
    form.append('file', file)
    const token = localStorage.getItem('auth.token') || ''
    return await $fetch(`${apiBase}/characters/upload/photo`, {
      method: 'POST',
      body: form,
      headers: token ? new Headers({ Authorization: `Bearer ${token}` }) : undefined
    })
  }

  async function voteCharacter(id, value) {
    const { $api } = useNuxtApp()
    const updated = await $api(`/characters/${id}/vote`, {
      method: 'POST',
      body: { value }
    })

    const apply = (arrRef) => {
      const idx = arrRef.value.findIndex(c => c.id === id)
      if (idx !== -1) {
        // мягко обновим объект, чтобы сохранить реактивность
        arrRef.value[idx] = { ...arrRef.value[idx], ...updated }
      }
    }
    apply(list)
    apply(mine)

    return updated
  }

  function getById(id) {
    const n = Number(id)
    return mine.value.find(c => c.id === n) || list.value.find(c => c.id === n)
  }

  return { list, mine, loading, fetchPublic, fetchMine, createCharacter, updateCharacter, uploadPhoto, getById, voteCharacter }
})