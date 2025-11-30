<!-- Shadow面板组件 -->
<template>
  <div class="shadow-panel">
    <div class="shadow-header">
      <h2>🤖 Shadow Mode</h2>
      <div class="pulse-dot"></div>
    </div>

    <!-- 当前活动 -->
    <div v-if="currentActivity" class="live-activity">
      <div class="activity-header">
        <span class="activity-label">⚡ Live Testing</span>
      </div>
      <div class="activity-content">
        <div class="activity-item">
          <span class="label">Target:</span>
          <span class="value url">{{ truncate(currentActivity.target_url, 30) }}</span>
        </div>
        <div class="activity-item">
          <span class="label">Payload:</span>
          <code class="value payload">{{ truncate(currentActivity.payload, 40) }}</code>
        </div>
      </div>
    </div>

    <!-- AI发现列表 -->
    <div class="notifications">
      <el-empty 
        v-if="notifications.length === 0" 
        description="No AI findings yet..."
        :image-size="100"
      />

      <transition-group name="list">
        <el-card 
          v-for="note in notifications" 
          :key="note.id" 
          class="notification-card"
          shadow="hover"
        >
          <template #header>
            <div class="note-header">
              <el-tag type="danger" effect="dark">VULNERABILITY FOUND</el-tag>
              <el-button size="small" @click="applyPayload(note.payload)">
                Apply
              </el-button>
            </div>
          </template>
          <div class="code-block">{{ note.payload }}</div>
          <p class="note-msg">{{ note.message }}</p>
        </el-card>
      </transition-group>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['apply-payload'])

const currentActivity = ref(null)
const notifications = ref([])
let ws = null

// ApplyPayload
const applyPayload = (payload) => {
  emit('apply-payload', payload)
  ElMessage.info('Payload已Apply到测试区')
}

// 截断字符串
const truncate = (str, len) => {
  if (!str || str.length <= len) return str
  return str.substring(0, len) + '...'
}

// 连接WebSocket
onMounted(() => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/notifications`)
  
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    
    if (msg.type === 'vuln_found') {
      notifications.value.unshift(msg.data)
      ElMessage.error({
        message: 'AI found a valid payload!',
        duration: 5000
      })
    } else if (msg.type === 'shadow_activity') {
      currentActivity.value = msg.data
    }
  }
  
  ws.onopen = () => {
    console.log('Shadow WS Connected')
  }
  
  ws.onerror = (e) => console.error('Shadow WS Error', e)
})

onUnmounted(() => {
  if (ws) ws.close()
})
</script>

<style scoped>
.shadow-panel {
  background-color: #fff;
  border-left: 1px solid #dcdfe6;
  padding: 20px;
  overflow-y: auto;
  height: 100%;
}

.shadow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.shadow-header h2 {
  font-size: 20px;
  margin: 0;
}

.pulse-dot {
  width: 10px;
  height: 10px;
  background-color: #67c23a;
  border-radius: 50%;
  box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.7);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 10px rgba(103, 194, 58, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(103, 194, 58, 0);
  }
}

.live-activity {
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 20px;
  animation: flash 1s;
}

.activity-header {
  margin-bottom: 8px;
  font-weight: bold;
  color: #409eff;
}

.activity-item {
  margin-bottom: 4px;
  font-size: 12px;
}

.activity-item .label {
  color: #606266;
  margin-right: 8px;
  font-weight: bold;
}

.activity-item .value {
  color: #303133;
  word-break: break-all;
}

.activity-item .value.payload {
  background: #fff;
  padding: 2px 4px;
  border-radius: 2px;
  border: 1px solid #dcdfe6;
  font-family: monospace;
  color: #e6a23c;
}

@keyframes flash {
  0% { background-color: #fff; }
  50% { background-color: #ecf5ff; }
  100% { background-color: #ecf5ff; }
}

.notifications {
  margin-top: 20px;
}

.notification-card {
  margin-bottom: 15px;
  border-left: 5px solid #f56c6c;
}

.note-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.code-block {
  background: #f4f4f5;
  padding: 8px;
  border-radius: 4px;
  font-family: monospace;
  margin: 10px 0;
  word-break: break-all;
  font-size: 13px;
}

.note-msg {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

/* 列表过渡 */
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
