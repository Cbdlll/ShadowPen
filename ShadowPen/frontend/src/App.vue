<template>
  <div class="xss-scanner-app">
    <!-- 顶部Header -->
    <el-header class="app-header">
      <div class="header-left">
        <h1>🛡️ ShadowPen</h1>
      </div>
      <div class="header-right">
        <span class="status-label">LLM Status:</span>
        <el-tag :type="llmConfigured ? 'success' : 'danger'" effect="dark">
          {{ llmConfigured ? `Active (${llmModel})` : 'Inactive' }}
        </el-tag>
      </div>
    </el-header>

    <!-- 主容器 -->
    <el-container class="main-container">
      <!-- 左侧：主工作区 -->
      <el-main class="work-area">
        <!-- 步骤指示器 -->
        <StepIndicator :current-step="currentStep" />

        <!-- 步骤内容区（动态切换）-->
        <transition name="fade" mode="out-in">
          <component 
            :is="currentStepComponent" 
            v-bind="currentStepProps"
            @next="handleStepNext"
            @prev="handleStepPrev"
            @cancel="handleCancel"
            @reset="handleReset"
          />
        </transition>
      </el-main>

      <!-- 右侧：Shadow面板 -->
      <el-aside width="400px" class="shadow-aside">
        <ShadowPanel @apply-payload="handleApplyPayload" />
      </el-aside>
    </el-container>

    <!-- Chat悬浮按钮 -->
    <el-badge :value="unreadChatCount" :hidden="unreadChatCount === 0" class="chat-badge">
      <el-button 
        class="chat-fab"
        circle
        type="primary"
        size="large"
        @click="chatDrawerVisible = true"
      >
        <el-icon :size="24"><ChatDotRound /></el-icon>
      </el-button>
    </el-badge>

    <!-- Chat抽屉 -->
    <ChatDrawer v-model="chatDrawerVisible" />

    <!-- 日志悬浮按钮 -->
    <el-button class="log-fab" circle @click="logDrawerVisible = true">
      <el-icon :size="20"><Document /></el-icon>
    </el-button>

    <!-- 日志抽屉 -->
    <el-drawer v-model="logDrawerVisible" title="System Logs" size="50%" direction="rtl">
      <template #header>
        <div class="drawer-header">
          <span>System Logs</span>
          <el-button size="small" @click="logs = []">Clear</el-button>
        </div>
      </template>
      <div class="log-container" ref="logContainer">
        <div v-if="logs.length === 0" class="log-empty">
          <span>📊</span>
          <p>No logs</p>
        </div>
        <div v-for="(log, index) in logs" :key="index" class="log-entry" :class="log.level">
          <span class="log-badge" :class="log.level">{{ getLevelIcon(log.level) }}</span>
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-msg">{{ log.message }}</span>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ChatDotRound, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// 导入组件
import StepIndicator from './components/StepIndicator.vue'
import Step1_UrlInput from './components/Step1_UrlInput.vue'
import Step2_Crawling from './components/Step2_Crawling.vue'
import Step3_InjectionPoints from './components/Step3_InjectionPoints.vue'
import Step4_Testing from './components/Step4_Testing.vue'
import ChatDrawer from './components/ChatDrawer.vue'
import ShadowPanel from './components/ShadowPanel.vue'

// 工作流状态
const currentStep = ref(1)
const workflow = ref({
  targetUrl: '',
  maxDepth: 3,
  maxPages: 20,
  crawlResult: null,
  selectedPoint: null
})

// UI状态
const chatDrawerVisible = ref(false)
const logDrawerVisible = ref(false)
const unreadChatCount = ref(0)
const llmConfigured = ref(false)
const llmModel = ref('')
const logs = ref([])
const logContainer = ref(null)

// 当前步骤组件
const currentStepComponent = computed(() => {
  const components = {
    1: Step1_UrlInput,
    2: Step2_Crawling,
    3: Step3_InjectionPoints,
    4: Step4_Testing
  }
  return components[currentStep.value]
})

// 当前步骤的props
const currentStepProps = computed(() => {
  if (currentStep.value === 2) {
    return {
      targetUrl: workflow.value.targetUrl,
      maxDepth: workflow.value.maxDepth,
      maxPages: workflow.value.maxPages
    }
  } else if (currentStep.value === 3) {
    return {
      crawlResult: workflow.value.crawlResult
    }
  } else if (currentStep.value === 4) {
    return {
      selectedPoint: workflow.value.selectedPoint
    }
  }
  return {}
})

// 步骤导航处理
const handleStepNext = (data) => {
  if (currentStep.value === 1) {
    // 步骤1 → 步骤2
    workflow.value.targetUrl = data.url
    workflow.value.maxDepth = data.maxDepth
    workflow.value.maxPages = data.maxPages
    currentStep.value = 2
    addLog('info', `Started crawling: ${data.url}`)
  } else if (currentStep.value === 2) {
    // 步骤2 → 步骤3
    workflow.value.crawlResult = data
    currentStep.value = 3
    const surfaceCount = data.surfaces?.length || 0
    const highValueCount = data.analysis?.high_value_surfaces?.length || surfaceCount
    addLog('success', `Crawling completed, found ${surfaceCount} attack surfaces, ${highValueCount} high-value targets`)
  } else if (currentStep.value === 3) {
    // 步骤3 → 步骤4
    workflow.value.selectedPoint = data
    currentStep.value = 4
    addLog('info', `Selected injection point: ${data.method} ${data.param_name || data.url}`)
  }
}

const handleStepPrev = () => {
  if (currentStep.value > 1) {
    currentStep.value--
    addLog('info', `Returned to step ${currentStep.value}`)
  }
}

const handleCancel = () => {
  currentStep.value = 1
  workflow.value = {
    targetUrl: '',
    maxDepth: 3,
    maxPages: 20,
    crawlResult: null,
    selectedPoint: null
  }
  addLog('warning', 'Crawling cancelled')
  ElMessage.warning('Crawling cancelled')
}

const handleReset = () => {
  currentStep.value = 1
  workflow.value = {
    targetUrl: '',
    maxDepth: 3,
    maxPages: 20,
    crawlResult: null,
    selectedPoint: null
  }
  addLog('info', 'Reset to initial state')
  ElMessage.success('Testing complete, reset')
}

// 应用Payload（从Shadow面板）
const handleApplyPayload = (payload) => {
  // 这里可以通过事件总线或状态管理传递给Step4
  // 暂时只显示消息
  ElMessage.info('Payload applied')
}

// 添加日志
const addLog = (level, message) => {
  logs.value.push({
    level,
    message,
    timestamp: Date.now()
  })
}

// 日志图标
const getLevelIcon = (level) => {
  const icons = {
    info: 'ℹ️',
    success: '✓',
    warning: '⚠',
    error: '✗',
    danger: '🔥'
  }
  return icons[level] || 'ℹ️'
}

// 格式化时间
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

// 检查LLM状态
const checkLLMStatus = async () => {
  try {
    const res = await axios.get('/api/llm-status')
    llmConfigured.value = res.data.configured
    llmModel.value = res.data.model
    addLog('success', `LLM configured: ${res.data.model}`)
  } catch (e) {
    console.error('Failed to check LLM status', e)
    addLog('warning', 'LLM status check failed')
  }
}

// 自动滚动日志
watch(logs, () => {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}, { deep: true })

// 生命周期
onMounted(() => {
  checkLLMStatus()
  addLog('success', 'ShadowPen started - Intelligent XSS Scanner')
})
</script>

<style scoped>
.xss-scanner-app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.app-header {
  background: linear-gradient(135deg, #1e293b, #334155);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-left h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.version-tag {
  font-size: 11px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-label {
  font-size: 14px;
  color: #e2e8f0;
}

.main-container {
  flex: 1;
  overflow: hidden;
}

.work-area {
  padding: 30px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.shadow-aside {
  background: white;
  border-left: 1px solid #e4e7ed;
  overflow-y: auto;
}

/* 悬浮按钮 */
.chat-fab {
  position: fixed;
  right: 30px;
  bottom: 30px;
  width: 64px;
  height: 64px;
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.4);
  z-index: 999;
  animation: float 3s ease-in-out infinite;
}

.chat-badge {
  position: fixed;
  right: 30px;
  bottom: 30px;
  z-index: 1000;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

.log-fab {
  position: fixed;
  right: 110px;
  bottom: 30px;
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  z-index: 998;
  transition: all 0.3s ease;
}

.log-fab:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

/* 日志抽屉 */
.drawer-header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-container {
  height: 100%;
  overflow-y: auto;
  padding: 15px;
}

.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #909399;
}

.log-empty span {
  font-size: 48px;
  margin-bottom: 10px;
}

.log-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 10px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}

.log-entry:hover {
  background: #f0f2f5;
  transform: translateX(2px);
}

.log-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 14px;
  flex-shrink: 0;
}

.log-badge.info {
  background: rgba(64, 158, 255, 0.2);
  color: #409eff;
}

.log-badge.success {
  background: rgba(103, 194, 58, 0.2);
  color: #67c23a;
}

.log-badge.warning {
  background: rgba(230, 162, 60, 0.2);
  color: #e6a23c;
}

.log-badge.error {
  background: rgba(245, 108, 108, 0.2);
  color: #f56c6c;
}

.log-time {
  color: #909399;
  font-size: 12px;
  font-family: monospace;
  min-width: 70px;
  flex-shrink: 0;
}

.log-msg {
  color: #303133;
  font-size: 13px;
  flex: 1;
}

.log-entry.info {
  border-left-color: #409eff;
}

.log-entry.success {
  border-left-color: #67c23a;
}

.log-entry.warning {
  border-left-color: #e6a23c;
}

.log-entry.error {
  border-left-color: #f56c6c;
}

/* 过渡动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* 响应式 */
@media (max-width: 1200px) {
  .shadow-aside {
    display: none;
  }
}

@media (max-width: 768px) {
  .work-area {
    padding: 15px;
  }
  
  .app-header {
    padding: 0 15px;
  }
  
  .header-left h1 {
    font-size: 18px;
  }
}
</style>
