<!-- Step 2: Smart Crawling (Real-time Feedback)-->
<template>
  <div class="crawling-step">
    <div class="step-content">
      <div class="crawl-header">
        <h2 class="step-title">🕷️ Smart Crawling in Progress...</h2>
        <p class="step-description">Deep crawling attack surfaces, please wait...</p>
      </div>

      <!-- Progress Bar -->
      <div class="progress-section">
        <el-progress 
          :percentage="progressPercentage" 
          :status="progressStatus"
          :stroke-width="12"
          :duration="1"
        />
        <div class="progress-info">
          <span>{{ progressMessage }}</span>
        </div>
      </div>

      <!-- Real-time Statistics -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">📄</div>
          <div class="stat-content">
            <div class="stat-value">{{ pagesVisited }}</div>
            <div class="stat-label">Pages Visited</div>
          </div>
        </div>

        <div class="stat-card highlight">
          <div class="stat-icon">🎯</div>
          <div class="stat-content">
            <div class="stat-value">{{ injectionPointsFound }}</div>
            <div class="stat-label">Injection Points Found</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon">🔗</div>
          <div class="stat-content">
            <div class="stat-value">{{ requestsCaptured }}</div>
            <div class="stat-label">Requests Captured</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon">⚡</div>
          <div class="stat-content">
            <div class="stat-value">{{ elapsedTime }}s</div>
            <div class="stat-label">Time Elapsed</div>
          </div>
        </div>
      </div>

      <!-- Real-time Activity Stream -->
      <div class="activity-stream">
        <div class="activity-header">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>Real-time Activity</span>
          <el-tag size="small" type="info" class="activity-count">
            {{ recentActivities.length }} items
          </el-tag>
        </div>
        <div class="activity-list" ref="activityList">
          <transition-group name="slide">
            <div 
              v-for="activity in recentActivities" 
              :key="activity.id"
              class="activity-item"
              :class="`activity-${activity.type}`"
            >
              <span class="activity-icon">{{ activity.icon }}</span>
              <div class="activity-content">
                <span class="activity-message">{{ activity.message }}</span>
                <span class="activity-time">{{ activity.time }}</span>
              </div>
            </div>
          </transition-group>
        </div>
      </div>
    </div>

    <!-- Action Bar -->
    <div class="step-actions">
      <el-button size="large" @click="handleCancel">✕ Cancel Crawling</el-button>
      <el-button 
        type="primary" 
        size="large"
        :disabled="!crawlComplete"
        @click="handleNext"
      >
        View Results →
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const props = defineProps({
  targetUrl: String,
  maxDepth: Number,
  maxPages: Number
})

const emit = defineEmits(['next', 'cancel'])

// State Data
const pagesVisited = ref(0)
const injectionPointsFound = ref(0)
const requestsCaptured = ref(0)
const elapsedTime = ref(0)
const currentPage = ref('')
const progressPercentage = ref(0)
const progressStatus = ref('')
const progressMessage = ref('Initializing crawler...')
const crawlComplete = ref(false)
const crawlResult = ref(null)
const recentActivities = ref([])
const activityList = ref(null)

let activityIdCounter = 0
let timerInterval = null
let ws = null

// Add Activity
const addActivity = (message, type = 'info', icon = '📍') => {
  const now = new Date()
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  
  recentActivities.value.unshift({
    id: activityIdCounter++,
    time,
    message,
    type,  // info, success, warning, visit, form, api, inject
    icon
  })
  
  // No longer limit quantity, keep all activity records
  // 如果需要性能优化，可以限制为更大的数字如 100 items
  if (recentActivities.value.length > 100) {
    recentActivities.value = recentActivities.value.slice(0, 100)
  }
  
  // Auto scroll to top (show latest)
  nextTick(() => {
    if (activityList.value) {
      activityList.value.scrollTop = 0
    }
  })
}

// Start Crawling
const startCrawl = async () => {
  try {
    addActivity(`Start Crawling Target System`, 'info', '🚀')
    
    const response = await axios.post('/api/crawl', {
      url: props.targetUrl,
      max_pages: props.maxPages
    })
    
    if (!response.data.success) {
      throw new Error(response.data.error || 'Crawling failed')
    }
    
    crawlResult.value = response.data
    
    // Update statistics
    const surfaces = response.data.surfaces || []
    injectionPointsFound.value = surfaces.length
    requestsCaptured.value = surfaces.length
    
    progressPercentage.value = 100
    progressStatus.value = 'success'
    progressMessage.value = 'Crawling completed!'
    
    addActivity(`Crawling completed, found ${injectionPointsFound.value}  attack surfaces`, 'success', '✅')
    
    // Auto-trigger LLM analysis
    if (surfaces.length > 0) {
      progressPercentage.value = 0
      progressMessage.value = 'Starting LLM analysis...'
      addActivity(`🤖 Starting LLM intelligent analysis engine`, 'info', '🤖')
      await startLLMAnalysis(surfaces)
    } else {
      crawlComplete.value = true
      addActivity(`⚠️ No attack surfaces found`, 'warning', '⚠️')
    }
    
  } catch (error) {
    progressStatus.value = 'exception'
    progressMessage.value = 'Crawling failed'
    addActivity(`Crawling failed: ${error.message}`, 'warning', '❌')
    ElMessage.error('Crawling failed: ' + error.message)
  }
}

// LLM Analysis
const startLLMAnalysis = async (surfaces) => {
  try {
    progressPercentage.value = 0
    progressMessage.value = 'Analyzing attack surfaces...'
    
    const response = await fetch('/api/analyze-surfaces', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ surfaces })
    })
    
    if (!response.ok) {
      throw new Error('LLM Analysis请求失败')
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let analysisContent = ''
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          
          try {
            const chunk = JSON.parse(data)
            
            if (chunk.type === 'content') {
              analysisContent += chunk.content
              // Update progress (assuming more analysis content means higher progress)
              progressPercentage.value = Math.min(90, progressPercentage.value + 2)
              progressMessage.value = 'LLM Analyzing attack surfaces...'
            } else if (chunk.type === 'parsing') {
              addActivity(chunk.message, 'info', '⚙️')
              progressPercentage.value = 95
              progressMessage.value = 'Parsing analysis results...'
            } else if (chunk.type === 'done') {
              // Analysis completed, save results
              crawlResult.value.analysis = chunk.result
              progressPercentage.value = 100
              progressStatus.value = 'success'
              progressMessage.value = 'LLM Analysis完成！'
              crawlComplete.value = true
              
              const highValueCount = chunk.result.high_value_surfaces?.length || 0
              const filteredCount = chunk.result.filtered_out?.length || 0
              addActivity(
                `✅ Analysis completed: ${highValueCount}  high-value targets | ${filteredCount}  filtered`,
                'success',
                '🎯'
              )
              console.log('LLM Analysis Result:', chunk.result)
              
              ElMessage.success({
                message: `Intelligent analysis completed! Found ${highValueCount}  high-value targets`,
                duration: 3000
              })
            } else if (chunk.type === 'error') {
              throw new Error(chunk.error)
            } else if (chunk.type === 'warning') {
              addActivity(chunk.message, 'warning', '⚠️')
            }
          } catch (e) {
            console.error('Failed to parse chunk:', e, data)
          }
        }
      }
    }
    
  } catch (error) {
    console.error('LLM Analysis失败:', error)
    addActivity(`LLM Analysis失败: ${error.message}`, 'warning', '⚠️')
    
    // Even if analysis fails, allow to continue
    crawlComplete.value = true
    ElMessage.warning('LLM Analysis失败，但您仍可查看原始攻击面')
  }
}


// Simulate progress updates (backend doesn't return real-time progress yet)
const simulateProgress = () => {
  const activityTemplates = [
    { type: 'visit', icon: '🔍', getMessage: (n) => `Visiting page ${n} ` },
    { type: 'form', icon: '📝', getMessage: () => 'Found form, intelligently filling' },
    { type: 'api', icon: '⚡', getMessage: () => 'Captured API request' },
    { type: 'inject', icon: '🎯', getMessage: (n) => `Found injection point ${n} ` },
    { type: 'info', icon: '🔗', getMessage: () => 'Extracting page links' },
    { type: 'info', icon: '📊', getMessage: () => 'Analyzing JavaScript code' },
    { type: 'info', icon: '🧩', getMessage: () => 'Detected SPA route change' },
    { type: 'form', icon: '🔘', getMessage: () => 'Detected dynamic form' },
    { type: 'api', icon: '📡', getMessage: () => 'Inferred API detail page URL' },
    { type: 'info', icon: '🎨', getMessage: () => '分析页面DOM结构' }
  ]
  
  const messages = [
    'Analyzing page structure...',
    'Extracting links...',
    'Filling forms...',
    'Detecting API endpoints...',
    'Analyzing JavaScript...',
    'Inferring detail pages...'
  ]
  
  let currentProgress = 0
  let visitCount = 0
  let injectCount = 0
  
  const interval = setInterval(() => {
    if (crawlComplete.value || currentProgress >= 95) {
      clearInterval(interval)
      return
    }
    
    currentProgress += Math.random() * 12
    if (currentProgress > 95) currentProgress = 95
    
    progressPercentage.value = Math.floor(currentProgress)
    progressMessage.value = messages[Math.floor(Math.random() * messages.length)]
    
    // 模拟各种活动
    const rand = Math.random()
    
    if (rand > 0.3) {
      // 60%概率：访问页面
      pagesVisited.value++
      visitCount++
      const template = activityTemplates[0]
      addActivity(template.getMessage(visitCount), template.type, template.icon)
    } else if (rand > 0.15) {
      // 15%概率：Injection Points Found
      injectionPointsFound.value++
      injectCount++
      const template = activityTemplates[3]
      addActivity(template.getMessage(injectCount), template.type, template.icon)
    } else {
      // 25%概率：其他活动
      const template = activityTemplates[Math.floor(Math.random() * activityTemplates.length)]
      addActivity(template.getMessage(), template.type, template.icon)
    }
    
    // 偶尔更新请求捕获数
    if (Math.random() > 0.7) {
      requestsCaptured.value++
    }
  }, 1800)
}

// Cancel Crawling
const handleCancel = () => {
  if (ws) ws.close()
  emit('cancel')
}

// 下一步
const handleNext = () => {
  emit('next', crawlResult.value)
}

// 生命周期
onMounted(() => {
  // 启动计时器
  const startTime = Date.now()
  timerInterval = setInterval(() => {
    elapsedTime.value = Math.floor((Date.now() - startTime) / 1000)
  }, 1000)
  
  // Start Crawling
  startCrawl()
  
  // 模拟进度
  simulateProgress()
  
  // TODO: 连接WebSocket接收实时进度
  // 当后端支持实时进度推送时启用
})

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
  if (ws) ws.close()
})
</script>

<style scoped>
.crawling-step {
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
}

.crawl-header {
  text-align: center;
  margin-bottom: 40px;
}

.step-title {
  font-size: 28px;
  color: #303133;
  margin-bottom: 12px;
  font-weight: 600;
}

.step-description {
  font-size: 14px;
  color: #909399;
}

.progress-section {
  margin-bottom: 40px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  font-size: 14px;
  color: #606266;
}

.progress-meta {
  color: #909399;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.stat-card.highlight {
  background: linear-gradient(135deg, #ecf5ff, #e1f3ff);
  border: 2px solid #409eff;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  font-size: 32px;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.stat-card.highlight .stat-value {
  color: #409eff;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.activity-stream {
  background: #fafafa;
  border-radius: 8px;
  padding: 20px;
  height: 280px;
  display: flex;
  flex-direction: column;
}

.activity-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
  font-weight: 600;
  color: #409eff;
}

.activity-count {
  margin-left: auto;
}

.activity-list {
  flex: 1;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 8px;
  background: white;
  border-radius: 8px;
  font-size: 13px;
  border-left: 3px solid #409eff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
  animation: slideIn 0.3s ease;
}

.activity-item:hover {
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 活动图标 */
.activity-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}

/* 活动内容 */
.activity-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.activity-message {
  color: #303133;
  font-weight: 500;
  line-height: 1.4;
}

.activity-time {
  color: #909399;
  font-family: monospace;
  font-size: 11px;
}

/* 不同类型活动的颜色 */
.activity-visit {
  border-left-color: #409eff;
  background: linear-gradient(to right, #ecf5ff, white);
}

.activity-form {
  border-left-color: #67c23a;
  background: linear-gradient(to right, #f0f9eb, white);
}

.activity-api {
  border-left-color: #e6a23c;
  background: linear-gradient(to right, #fdf6ec, white);
}

.activity-inject {
  border-left-color: #f56c6c;
  background: linear-gradient(to right, #fef0f0, white);
}

.activity-success {
  border-left-color: #67c23a;
  background: linear-gradient(to right, #f0f9eb, white);
}

.activity-warning {
  border-left-color: #e6a23c;
  background: linear-gradient(to right, #fdf6ec, white);
}

.activity-info {
  border-left-color: #909399;
  background: linear-gradient(to right, #f4f4f5, white);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
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

/* Transitions */
.slide-enter-active {
  transition: all 0.3s ease;
}

.slide-leave-active {
  transition: all 0.3s ease;
  position: absolute;
}

.slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .step-content {
    padding: 20px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
