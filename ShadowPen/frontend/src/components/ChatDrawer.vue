<!-- Chat抽屉组件 -->
<template>
  <el-drawer
    v-model="visible"
    title="AI 专家对话"
    direction="rtl"
    size="500px"
    :close-on-click-modal="false"
  >
    <div class="chat-drawer-content">
      <!-- Chat消息区 -->
      <div class="chat-messages" ref="chatMessages">
        <div v-if="chatHistory.length === 0" class="chat-empty">
          <span>💬</span>
          <p>与 AI 专家对话，询问 XSS 相关问题</p>
        </div>

        <div 
          v-for="(msg, index) in chatHistory" 
          :key="index" 
          class="chat-message" 
          :class="msg.role"
        >
          <div class="message-bubble">
            <div class="message-header">
              <span class="message-role">
                {{ msg.role === 'user' ? '👤 You' : '🤖 AI Expert' }}
              </span>
            </div>

            <!-- 思考过程 -->
            <div v-if="msg.thinking && msg.role === 'assistant'" class="message-thinking">
              <div class="thinking-header">💭 思考过程</div>
              <div class="thinking-content">{{ msg.thinking }}</div>
            </div>

            <!-- 消息内容 -->
            <div class="message-content">{{ msg.content }}</div>
          </div>
        </div>

        <!-- Loading状态 -->
        <div v-if="chatLoading" class="chat-message assistant">
          <div class="message-bubble loading">
            <span class="typing-indicator">
              <span></span><span></span><span></span>
            </span>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input-area">
        <el-input
          v-model="chatInput"
          type="textarea"
          :rows="3"
          placeholder="询问 XSS 相关问题..."
          @keydown.ctrl.enter="sendChat"
        />
        <div class="chat-actions">
          <el-button size="small" @click="clearChat">Clear Chat</el-button>
          <el-button 
            type="primary" 
            @click="sendChat" 
            :loading="chatLoading"
          >
            Send (Ctrl+Enter)
          </el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const chatHistory = ref([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatMessages = ref(null)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

// Send Message
const sendChat = async () => {
  if (!chatInput.value.trim() || chatLoading.value) return
  
  const userMessage = chatInput.value.trim()
  chatInput.value = ''
  
  // 添加用户消息
  chatHistory.value.push({ role: 'user', content: userMessage })
  
  chatLoading.value = true
  
  // 添加空的AI消息用于流式更新
  const assistantMsgIndex = chatHistory.value.length
  chatHistory.value.push({ 
    role: 'assistant', 
    content: '', 
    thinking: ''
  })
  
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: userMessage,
        history: chatHistory.value.slice(0, assistantMsgIndex)
      })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      
      // 处理完整的SSE消息
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          
          try {
            const data = JSON.parse(dataStr)
            
            if (data.type === 'thinking') {
              if (chatHistory.value[assistantMsgIndex]) {
                chatHistory.value[assistantMsgIndex].thinking += data.content
              }
            } else if (data.type === 'content') {
              if (chatHistory.value[assistantMsgIndex]) {
                chatHistory.value[assistantMsgIndex].content += data.content
              }
            } else if (data.type === 'error') {
              ElMessage.error('Chat error: ' + data.error)
              if (chatHistory.value[assistantMsgIndex]) {
                chatHistory.value.splice(assistantMsgIndex, 1)
              }
              break
            } else if (data.type === 'done') {
              break
            }
            
            // 自动滚动
            setTimeout(() => scrollToBottom(), 50)
            
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
    
    // 如果没有收到内容，移除空消息
    if (!chatHistory.value[assistantMsgIndex].content && !chatHistory.value[assistantMsgIndex].thinking) {
      chatHistory.value.splice(assistantMsgIndex, 1)
      chatHistory.value.pop()
      ElMessage.error('No response received from AI')
    }
    
  } catch (error) {
    ElMessage.error('Chat failed: ' + error.message)
    if (chatHistory.value[assistantMsgIndex]) {
      chatHistory.value.splice(assistantMsgIndex, 1)
    }
    chatHistory.value.pop()
  } finally {
    chatLoading.value = false
  }
}

// Clear Chat
const clearChat = () => {
  chatHistory.value = []
  ElMessage.info('对话已清空')
}

// 滚动到底部
const scrollToBottom = () => {
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-drawer-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f7fa;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.chat-empty span {
  font-size: 48px;
  margin-bottom: 10px;
}

.chat-message {
  display: flex;
  margin-bottom: 15px;
}

.chat-message.user {
  justify-content: flex-end;
}

.chat-message.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chat-message.user .message-bubble {
  background: linear-gradient(135deg, #409eff, #3a8ee6);
  color: white;
  border-bottom-right-radius: 4px;
}

.chat-message.assistant .message-bubble {
  background: white;
  color: #303133;
  border-bottom-left-radius: 4px;
}

.message-bubble.loading {
  padding: 16px 24px;
  background: white;
}

.message-header {
  font-size: 12px;
  margin-bottom: 6px;
  opacity: 0.9;
  font-weight: 500;
}

.message-thinking {
  background: rgba(0, 0, 0, 0.05);
  padding: 8px 10px;
  border-radius: 6px;
  margin-bottom: 10px;
  font-size: 12px;
}

.thinking-header {
  font-weight: 600;
  margin-bottom: 4px;
  color: #909399;
}

.thinking-content {
  color: #606266;
  line-height: 1.5;
  white-space: pre-wrap;
}

.message-content {
  line-height: 1.6;
  white-space: pre-wrap;
}

.typing-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #409eff;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-10px);
  }
}

.chat-input-area {
  padding: 15px;
  background: white;
  border-top: 1px solid #e4e7ed;
}

.chat-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}
</style>
