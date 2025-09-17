<!-- components/Window.vue -->
<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  character: { type: Object, default: null },
  dialogId: { type: [Number, String], default: null }
})

const dialogs = useDialogsStore()
const route = useRoute()
const router = useRouter()

const input = ref('')
const sending = ref(false)
const currentDialogId = ref(props.dialogId ? Number(props.dialogId) : null)

const msgs = computed(() => {
  const id = currentDialogId.value
  return (id ? dialogs.messages[id] : []) || []
})

const charId = computed(() => {
  if (props.character?.id) return Number(props.character.id)
  if (currentDialogId.value) return dialogs.dialogCharacter[currentDialogId.value] || null
  return null
})

const messagesRef = ref(null)
const inputEl = ref(null)
const inputWrapRef = ref(null)
const containerRef = ref(null)

const scrollToBottom = async (smooth = true) => {
  await nextTick()
  const el = messagesRef.value
  if (!el) return

  const target = el.scrollHeight - el.clientHeight
  const supportsSmooth =
    typeof CSS !== 'undefined' &&
    CSS.supports &&
    CSS.supports('scroll-behavior', 'smooth')

  if (smooth && supportsSmooth && typeof el.scrollTo === 'function') {
    el.scrollTo({ top: target, behavior: 'smooth' })
  } else {
    el.scrollTop = target
  }

  // «Дожим» до самого низа на следующий кадр(ы)
  let tries = 0
  const ensure = () => {
    const diff = el.scrollHeight - el.clientHeight - el.scrollTop
    if (diff > 2 && tries++ < 8) {
      el.scrollTop = el.scrollHeight - el.clientHeight
      requestAnimationFrame(ensure)
    }
  }
  requestAnimationFrame(ensure)
}

const updateInputPadding = () => {
  const h = inputWrapRef.value?.offsetHeight || 56
  if (containerRef.value) {
    containerRef.value.style.setProperty('--input-h', `${h}px`)
  }
  // Если высота инпута изменилась (клавиатура, ориентация и т.п.) — доскроллим
  scrollToBottom(false)
}

const focusInput = async () => {
  await nextTick()
  inputEl.value?.focus()

  // На iOS при открытии клавиатуры высота вьюпорта меняется — доскроллим после resize
  if (window.visualViewport) {
    const onVVResize = () => {
      scrollToBottom(false)
    }
    window.visualViewport.addEventListener('resize', onVVResize, { once: true })
  }
}

let ro
onMounted(async () => {
  if (currentDialogId.value) {
    await Promise.all([
      dialogs.fetchMessages(currentDialogId.value),
      dialogs.ensureDialogCharacter(currentDialogId.value)
    ])
  }

  updateInputPadding()

  if ('ResizeObserver' in window) {
    ro = new ResizeObserver(updateInputPadding)
    if (inputWrapRef.value) ro.observe(inputWrapRef.value)
  } else {
    window.addEventListener('resize', updateInputPadding, { passive: true })
    window.addEventListener('orientationchange', updateInputPadding, { passive: true })
  }

  focusInput()
})

onBeforeUnmount(() => {
  if (ro) ro.disconnect()
  window.removeEventListener('resize', updateInputPadding)
  window.removeEventListener('orientationchange', updateInputPadding)
})

async function send() {
  const text = input.value.trim()
  if (!text) return
  sending.value = true
  try {
    let characterId = charId.value
    if (!characterId && currentDialogId.value) {
      characterId = await dialogs.ensureDialogCharacter(currentDialogId.value)
    }
    if (!characterId) {
      throw new Error('character_id неизвестен')
    }

    const newId = await dialogs.sendMessage({
      characterId,
      text,
      dialogId: currentDialogId.value || null
    })
    input.value = ''

    // Возвращаем фокус в инпут
    await focusInput()

    if (!currentDialogId.value && newId) {
      currentDialogId.value = Number(newId)
      if (route.name?.toString().includes('characters-id')) {
        router.replace(`/dialogs/${newId}`)
      } else {
        await dialogs.fetchMessages(newId)
      }
    }

    await scrollToBottom(true)
  } finally {
    sending.value = false
  }
}

// Скролл при изменении количества сообщений (и при первом рендере)
watch(
  () => msgs.value.length,
  () => scrollToBottom(false),
  { immediate: true }
)

// Скролл при смене диалога
watch(
  () => currentDialogId.value,
  () => scrollToBottom(false)
)
</script>

<template>
  <div class="chat-container" ref="containerRef">
    <div class="chat-messages" ref="messagesRef">
      <ChatMessageBubble
        v-if="!currentDialogId && character?.context"
        :message="{ role: 'system', text: character.context }"
      />
      <ChatMessageBubble v-for="(m, i) in msgs" :key="i" :message="m" />
    </div>

    <div class="chat-input" ref="inputWrapRef">
      <div class="field has-addons">
        <div class="control is-expanded">
          <input
            ref="inputEl"
            class="input"
            v-model="input"
            placeholder="Введите сообщение"
            @keydown.enter.exact.prevent="send"
            type="text"
            inputmode="text"
            autocomplete="off"
            autocapitalize="sentences"
            spellcheck="true"
          />
        </div>
        <div class="control">
          <button
            type="button"
            class="button is-primary"
            :class="{ 'is-loading': sending }"
            @click="send"
          >
            Отправить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;

  /* Занимаем весь вьюпорт: сначала обычный vh как фолбэк, затем динамический dvh */
  height: 90vh;
  max-height: 90vh;
  height: 90dvh;
  max-height: 90dvh;

  background: #1b1b1b;
}

.chat-messages {
  flex: 1 1 auto;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;

  /* Сначала фолбэк без safe-area */
  padding-bottom: 12px;
  /* Затем с учётом safe-area (если поддерживается) */
  padding-bottom: calc(12px + env(safe-area-inset-bottom));

  padding-left: 0.25rem;
  padding-right: 0.25rem;
}

/* Инпут приклеен к низу (sticky), но остаётся в потоке, поэтому с отступом снизу
   у .chat-messages нижние сообщения не перекрываются */
.chat-input {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;

  padding: 0.5rem;
  /* Фолбэк */
  padding-bottom: 0.5rem;
  /* Если есть safe-area на iOS, добавим её */
  padding-bottom: calc(0.5rem + env(safe-area-inset-bottom));

  background: #1b1b1b;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.chat-input .field {
  margin-bottom: 0px;
}
</style>