<template>
  <div class="ai-chat-panel">
    <div class="chat-header">
      <span class="chat-icon">🤖</span>
      <span class="chat-title">AI 健身助手</span>
    </div>
    <div class="chat-messages" ref="msgContainer">
      <div v-if="messages.length === 0" class="chat-empty">
        <p>问我任何关于训练的问题</p>
        <div class="suggestion-chips">
          <span v-for="s in suggestions" :key="s" class="chip" @click="sendMessage(s)">{{ s }}</span>
        </div>
      </div>
      <div v-for="(msg, i) in messages" :key="i" class="msg-row" :class="msg.role">
        <div class="msg-bubble">{{ msg.content }}</div>
      </div>
      <div v-if="loading" class="msg-row ai">
        <div class="msg-bubble typing">思考中...</div>
      </div>
    </div>
    <div class="chat-input-row">
      <a-input
        v-model:value="inputText"
        placeholder="问 AI 关于训练的问题..."
        size="small"
        @press-enter="sendMessage(inputText)"
      >
        <template #suffix>
          <a-button type="text" size="small" :disabled="!inputText.trim() || loading" @click="sendMessage(inputText)">发送</a-button>
        </template>
      </a-input>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'

const inputText = ref('')
const loading = ref(false)
const msgContainer = ref<HTMLElement | null>(null)
const messages = ref<{ role: string; content: string }[]>([])

const suggestions = ['今天练什么？', '这个动作怎么做？', '帮我调整计划']

function sendMessage(text: string) {
  if (!text.trim() || loading.value) return
  const msg = text.trim()
  inputText.value = ''
  messages.value.push({ role: 'user', content: msg })
  loading.value = true
  scrollToBottom()

  // 模拟 AI 回复（后续对接实际 AI 接口）
  setTimeout(() => {
    loading.value = false
    messages.value.push({
      role: 'ai',
      content: 'AI 功能开发中，后续将接入智能问答 🤖',
    })
    scrollToBottom()
  }, 800)
}

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.ai-chat-panel {
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: var(--shadow-card-lg);
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.chat-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.chat-icon { font-size: 16px; }
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}
.chat-empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 12px 0;
}
.chat-empty p { margin: 0 0 10px 0; }
.suggestion-chips { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.chip {
  padding: 4px 12px;
  background: var(--brand-orange-subtle);
  color: var(--brand-orange);
  border-radius: 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.chip:hover { background: var(--brand-orange); color: #fff; }
.msg-row { display: flex; }
.msg-row.user { justify-content: flex-end; }
.msg-row.ai { justify-content: flex-start; }
.msg-bubble {
  max-width: 85%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}
.msg-row.user .msg-bubble {
  background: var(--brand-orange);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-row.ai .msg-bubble {
  background: var(--bg-subtle);
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
}
.msg-bubble.typing { color: var(--text-muted); }
.chat-input-row {
  padding: 8px 14px 10px;
  border-top: 1px solid var(--border-subtle);
}
</style>
