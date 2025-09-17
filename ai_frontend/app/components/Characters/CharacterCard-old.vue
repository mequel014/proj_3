<script setup>
const props = defineProps({
  character: { type: Object, required: true },
  mine: { type: Boolean, default: false }
})
const router = useRouter()
const config = useRuntimeConfig()

function normalizeUrl(u) {
  if (!u) return ''
  const clean = u.replaceAll('\\', '/')
  if (clean.startsWith('http')) return clean
  // Добавляем базовый URL бэка (http://localhost:8000)
  return `${config.public.apiBase}${clean}`
}

// function normalizeUrl(u) {
//   if (!u) return ''
//   const clean = String(u).replaceAll('\\', '/').trim()

//   // Абсолютный URL
//   if (/^https?:\/\//i.test(clean)) {
//     try {
//       const url = new URL(clean)
//       const isLocalBackend =
//         (url.hostname === 'localhost' && url.port === '8000') ||
//         (url.hostname === '127.0.0.1' && url.port === '8000') ||
//         url.hostname === 'backend'

//       // Переводим локальные http://localhost:8000/... на прокси /api/...
//       if (isLocalBackend) {
//         return `/api${url.pathname}${url.search}${url.hash}`
//       }

//       // Для прочих http-ссылок пробуем апгрейдить на https
//       if (url.protocol === 'http:') {
//         url.protocol = 'https:'
//         return url.toString()
//       }
//       return clean
//     } catch {
//       // падать не будем — обработаем ниже как относительный путь
//     }
//   }

//   // Относительные пути к uploads ведём через /api
//   if (clean.startsWith('/static/uploads/')) return `/api${clean}`
//   if (clean.startsWith('static/uploads/')) return `/api/${clean}`

//   // Иначе просто делаем абсолютным путём от текущего origin
//   return clean.startsWith('/') ? clean : `/${clean}`
// }

// function normalizeUrl(u) {
//   if (!u) return ''

//   const clean = String(u).replaceAll('\\', '/').trim()

//   // data:/blob: — как есть
//   if (/^(data|blob):/i.test(clean)) return clean

//   // Определяем: локальный дев-оригин (vite/nuxt dev) — напр. http://localhost:3000
//   const isClient = typeof window !== 'undefined'
//   const isDevOrigin =
//     isClient &&
//     /^(localhost|127\.0\.0\.1)$/i.test(window.location.hostname) &&
//     window.location.port &&
//     !['', '80', '443'].includes(window.location.port)

//   // Пытаемся достать apiBase из runtimeConfig; иначе дефолт для локалки
//   let apiBase = ''
//   try {
//     const cfg = typeof useRuntimeConfig === 'function' ? useRuntimeConfig() : undefined
//     apiBase = cfg?.public?.apiBase || ''
//   } catch {}
//   if (!apiBase) apiBase = 'http://localhost:8000'

//   // Абсолютные URL
//   if (/^https?:\/\//i.test(clean)) {
//     try {
//       const url = new URL(clean)

//       const isLocalBackend =
//         ((url.hostname === 'localhost' || url.hostname === '127.0.0.1') && url.port === '8000') ||
//         url.hostname === 'backend'

//       if (isLocalBackend) {
//         // В dev лучше ходить напрямую (иначе /api перехватит Nuxt и даст 404)
//         if (isDevOrigin) {
//           // Если backend указан как 'backend', на клиенте такое имя не резолвится — подменим на apiBase
//           if (url.hostname === 'backend') {
//             return `${apiBase}${url.pathname}${url.search}${url.hash}`
//           }
//           return clean
//         }
//         // В проде — через прокси /api
//         return `/api${url.pathname}${url.search}${url.hash}`
//       }

//       // Прочие абсолютные ссылки — возвращаем как есть
//       return clean
//     } catch {
//       // падать не будем — обработаем ниже как относительный путь
//     }
//   }

//   // Относительные пути
//   let path = clean.startsWith('/') ? clean : `/${clean}`

//   // Что считаем "медией" бэкенда
//   const isUploadPath =
//     path.startsWith('/static/uploads/') ||
//     path.startsWith('/media/') ||
//     path.startsWith('/uploads/')

//   if (isUploadPath) {
//     // В dev — на прямой backend (apiBase); в проде — через /api
//     return isDevOrigin ? `${apiBase}${path}` : `/api${path}`
//   }

//   // Всё остальное — просто нормализуем к абсолютному пути
//   return path
// }

const photoSrc = computed(() => normalizeUrl(props.character.photo_url))

function openChat() {
  router.push(`/characters/${props.character.id}`)
}
function edit() {
  router.push(`/characters/${props.character.id}/edit`)
}
</script>

<template>
  <div class="card">
    <div class="card-content">
      <div class="media">
        <div class="media-left" v-if="photoSrc">
          <figure class="image is-64x64">
            <img :src="photoSrc" :alt="character.name" style="object-fit: cover;">
          </figure>
        </div>
        <div class="media-content">
          <p class="title has-text-white is-5">{{ character.name }}</p>
          <p class="subtitle is-6">
            <span class="tag is-dark">{{ character.gender || '—' }}</span>
            
            <span class="tag is-link ml-2">⭐ {{ character.rating ?? '—' }}</span>
            <span class="tag is-warning ml-2" v-if="character.is_public === false">private</span>
          </p>
        </div>
      </div>
      <div class="content">
        <div class="tags">
          <span class="tag" v-for="tag in character.interests || []" :key="tag">{{ tag }}</span>
        </div>
      </div>
      <div class="buttons">
        <button class="button is-primary" @click="openChat">Чат</button>
        <button class="button" v-if="mine" @click="edit">Редактировать</button>
      </div>
    </div>
  </div>
</template>