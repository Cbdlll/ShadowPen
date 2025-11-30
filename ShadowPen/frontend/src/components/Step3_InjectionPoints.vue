<!-- 步骤3：注入点选择（LLM智能分析版） -->
<template>
  <div class="injection-points-step">
    <div class="step-content">
      <div class="points-header">
        <div>
          <h2 class="step-title">🎯 Intelligent attack surface analysis results</h2>
          <p class="step-description">
            <template v-if="hasAnalysis">
              Analyzed <strong>{{ totalSurfaces }}</strong> attack surfaces,
              discovered <strong>{{ analyzedSurfaces.length }}</strong> targets
            </template>
            <template v-else>
              Discovered <strong>{{ allSurfaces.length }}</strong> attack surfaces
            </template>
          </p>
        </div>
        
        <!-- 筛选和排序 -->
        <div class="filters">
          <el-select v-model="filterPriority" placeholder="Priority" size="default" style="width: 140px">
            <el-option label="All Priorities" value="all" />
            <el-option label="High Priority" value="high" />
            <el-option label="Medium Priority" value="medium" />
            <el-option label="Low Priority" value="low" />
          </el-select>
          
          <el-select v-model="filterMethod" placeholder="Methods" size="default" style="width: 120px">
            <el-option label="All Methods" value="all" />
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
          </el-select>
        </div>
      </div>

      <!-- 分析摘要 -->
      <el-alert 
        v-if="hasAnalysis && analysis.summary" 
        :title="analysis.summary"
        type="info"
        :closable="false"
        show-icon
        class="analysis-summary"
      />

      <!-- 高价值攻击面卡片 -->
      <div class="injection-points-grid" v-if="filteredSurfaces.length > 0">
        <el-card 
          v-for="(surface, index) in filteredSurfaces" 
          :key="index"
          class="injection-card"
          :class="{ 
            selected: selectedSurface?.index === surface.index,
            'high-priority': surface.priority === 'high',
            'medium-priority': surface.priority === 'medium'
          }"
          shadow="hover"
          @click="selectSurface(surface)"
        >
          <!-- 卡片头部 -->
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <el-tag 
                  :type="getMethodColor(surface.method)"
                  effect="dark"
                  size="large"
                >
                  {{ surface.method }}
                </el-tag>
                <el-tag 
                  :type="getPriorityColor(surface.priority)" 
                  size="small"
                  v-if="surface.priority"
                >
                  {{ getPriorityLabel(surface.priority) }}
                </el-tag>
              </div>
              
              <!-- Risk Score -->
              <div class="risk-score" v-if="surface.risk_score">
                <el-tooltip content="Risk Score" placement="top">
                  <div class="score-badge" :class="getScoreClass(surface.risk_score)">
                    {{ surface.risk_score }}/10
                  </div>
                </el-tooltip>
              </div>
            </div>
          </template>

          <!-- URL -->
          <div class="card-url" :title="surface.url">
            <el-icon><Link /></el-icon>
            <span>{{ truncateUrl(surface.url, 60) }}</span>
          </div>

          <!-- 参数信息 -->
          <div class="card-param">
            <el-icon><Edit /></el-icon>
            <strong>{{ surface.param_name }}</strong>
            <el-tag size="small" type="info" effect="plain">
              {{ surface.param_location }}
            </el-tag>
          </div>

          <!-- LLM Analysis Reason -->
          <div class="analysis-reason" v-if="surface.reason">
            <div class="reason-title">
              <el-icon><InfoFilled /></el-icon>
              Analysis Reason
            </div>
            <div class="reason-text">{{ surface.reason }}</div>
          </div>

          <!-- Recommended Payload -->
          <div class="recommended-payloads" v-if="surface.recommended_payloads && surface.recommended_payloads.length > 0">
            <div class="payloads-title">
              <el-icon><Tools /></el-icon>
              Recommended Payload
            </div>
            <div class="payload-list">
              <el-tag 
                v-for="(payload, idx) in surface.recommended_payloads.slice(0, 2)" 
                :key="idx"
                size="small"
                type="warning"
                effect="plain"
                class="payload-tag"
              >
                {{ payload }}
              </el-tag>
            </div>
          </div>

          <!-- Testing Tips -->
          <div class="test-tips" v-if="surface.test_tips">
            <el-icon><Notification /></el-icon>
            <span>{{ surface.test_tips }}</span>
          </div>

          <!-- 选中指示 -->
          <div v-if="selectedSurface?.index === surface.index" class="selected-indicator">
            <el-icon><CircleCheck /></el-icon>
            <span>Selected</span>
          </div>
        </el-card>
      </div>

      <!-- 空状态 -->
      <el-empty 
        v-else
        description="No matching attack surfaces found"
        :image-size="120"
      >
        <el-button type="primary" @click="resetFilters">Reset Filters</el-button>
      </el-empty>

      <!-- 被过滤掉的攻击面（可折叠） -->
      <el-collapse v-if="hasAnalysis && filteredOutSurfaces.length > 0" class="filtered-section">
        <el-collapse-item>
          <template #title>
            <span class="filtered-title">
              <el-icon><Filter /></el-icon>
              Filtered Low-Value Attack Surfaces ({{ filteredOutSurfaces.length }})
            </span>
          </template>
          <div class="filtered-list">
            <div 
              v-for="(item, idx) in filteredOutSurfaces" 
              :key="idx"
              class="filtered-item"
            >
              <el-tag size="small" type="info">{{ idx + 1 }}</el-tag>
              <span class="filtered-reason">{{ item.reason }}</span>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- 操作栏 -->
    <div class="step-actions">
      <el-button size="large" @click="$emit('prev')">← Re-crawl</el-button>
      <el-button 
        type="primary" 
        size="large"
        :disabled="!selectedSurface"
        @click="handleNext"
      >
        Start Testing →
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  Link, Edit, CircleCheck, InfoFilled, Tools, Filter, Notification 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  crawlResult: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['next', 'prev'])

// 状态
const selectedSurface = ref(null)
const filterPriority = ref('all')
const filterMethod = ref('all')

// 解析爬取结果
const hasAnalysis = computed(() => {
  return props.crawlResult?.analysis?.high_value_surfaces
})

const analysis = computed(() => {
  return props.crawlResult?.analysis || {}
})

const allSurfaces = computed(() => {
  return props.crawlResult?.surfaces || []
})

const totalSurfaces = computed(() => {
  return allSurfaces.value.length
})

// 分析后的攻击面（包含所有优先级）
const analyzedSurfaces = computed(() => {
  if (!hasAnalysis.value) {
    // 如果没有 LLM 分析，显示所有攻击面
    return allSurfaces.value.map((surface, index) => ({
      index,
      ...surface,
      url: surface.request_url || surface.url,
      priority: 'unknown'
    }))
  }
  
  // 使用 LLM 分析结果（显示所有优先级）
  return (analysis.value.high_value_surfaces || []).map(surface => ({
    ...surface,
    // 补充原始数据
    ...allSurfaces.value[surface.index]
  }))
})

// 保持兼容性
const highValueSurfaces = analyzedSurfaces

// 被过滤的攻击面
const filteredOutSurfaces = computed(() => {
  return analysis.value.filtered_out || []
})

// 筛选后的攻击面
const filteredSurfaces = computed(() => {
  let surfaces = [...analyzedSurfaces.value]
  
  // 按优先级筛选
  if (filterPriority.value !== 'all') {
    surfaces = surfaces.filter(s => s.priority === filterPriority.value)
  }
  
  // 按方法筛选
  if (filterMethod.value !== 'all') {
    surfaces = surfaces.filter(s => s.method === filterMethod.value)
  }
  
  return surfaces
})

// 选择攻击面
const selectSurface = (surface) => {
  selectedSurface.value = surface
  ElMessage.success(`Selected: ${surface.method} ${surface.param_name}`)
}

// 下一步
const handleNext = () => {
  if (!selectedSurface.value) {
    ElMessage.warning('Please select an attack surface first')
    return
  }
  
  // 从原始 surface 数据获取完整信息
  const originalSurface = allSurfaces.value[selectedSurface.value.index] || selectedSurface.value
  
  // 构造测试目标，添加 injection_points
  const testTarget = {
    url: selectedSurface.value.url || originalSurface.request_url,
    method: selectedSurface.value.method,
    param_name: selectedSurface.value.param_name,
    param_location: selectedSurface.value.param_location,
    recommended_payloads: selectedSurface.value.recommended_payloads || [],
    test_tips: selectedSurface.value.test_tips,
    resource_type: originalSurface.param_location || 'unknown',
    headers: originalSurface.headers || {},
    post_data: originalSurface.post_data || {},
    // 构建 injection_points 数组供 Step4 使用
    injection_points: [
      {
        name: selectedSurface.value.param_name,
        type: selectedSurface.value.param_location || 'unknown',
        sample_value: originalSurface.sample_payload || ''
      }
    ]
  }
  
  emit('next', testTarget)
}

// Reset Filters
const resetFilters = () => {
  filterPriority.value = 'all'
  filterMethod.value = 'all'
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

const getPriorityColor = (priority) => {
  const colors = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'info'
  }
  return colors[priority] || ''
}

const getPriorityLabel = (priority) => {
  const labels = {
    'high': 'High Priority',
    'medium': 'Medium Priority',
    'low': 'Low Priority'
  }
  return labels[priority] || '未知'
}

const getScoreClass = (score) => {
  if (score >= 8) return 'score-high'
  if (score >= 5) return 'score-medium'
  return 'score-low'
}

const truncateUrl = (url, maxLength = 60) => {
  if (!url) return ''
  if (url.length <= maxLength) return url
  return url.substring(0, maxLength) + '...'
}
</script>

<style scoped>
.injection-points-step {
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

.points-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.step-title {
  font-size: 28px;
  color: #303133;
  margin-bottom: 8px;
  font-weight: 600;
}

.step-description {
  font-size: 14px;
  color: #606266;
}

.step-description strong {
  color: #409eff;
  font-size: 18px;
}

.filters {
  display: flex;
  gap: 12px;
}

.analysis-summary {
  margin-bottom: 24px;
  font-size: 14px;
}

.injection-points-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 16px;
  margin-bottom: 30px;
}

.injection-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.injection-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.injection-card.selected {
  border-color: #409eff;
  background: linear-gradient(to bottom, #ecf5ff, white);
}

.injection-card.high-priority {
  border-color: #f56c6c;
  background: linear-gradient(to bottom, #fef0f0, white);
}

.injection-card.medium-priority {
  border-color: #e6a23c;
  background: linear-gradient(to bottom, #fdf6ec, white);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  gap: 8px;
  align-items: center;
}

.risk-score {
  font-weight: bold;
}

.score-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
}

.score-high {
  background: #fef0f0;
  color: #f56c6c;
}

.score-medium {
  background: #fdf6ec;
  color: #e6a23c;
}

.score-low {
  background: #f0f9ff;
  color: #409eff;
}

.card-url {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  font-size: 12px;
  color: #606266;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 12px;
  font-family: 'Monaco', 'Courier New', monospace;
}

.card-url .el-icon {
  color: #909399;
  flex-shrink: 0;
}

.card-param {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 14px;
}

.card-param .el-icon {
  color: #409eff;
}

.analysis-reason {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 12px;
}

.reason-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 6px;
}

.reason-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

.recommended-payloads {
  margin-bottom: 12px;
}

.payloads-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #e6a23c;
  margin-bottom: 8px;
}

.payload-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.payload-tag {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 11px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.test-tips {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: #67c23a;
  padding: 8px;
  background: #f0f9eb;
  border-radius: 4px;
  margin-bottom: 8px;
}

.test-tips .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.selected-indicator {
  margin-top: 12px;
  padding: 8px 12px;
  background: #409eff;
  color: white;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
}

.filtered-section {
  margin-top: 30px;
}

.filtered-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #909399;
}

.filtered-list {
  max-height: 300px;
  overflow-y: auto;
}

.filtered-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  margin-bottom: 8px;
  background: #fafafa;
  border-radius: 4px;
  font-size: 13px;
}

.filtered-reason {
  color: #606266;
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

@media (max-width: 1200px) {
  .injection-points-grid {
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  }
}

@media (max-width: 768px) {
  .step-content {
    padding: 20px;
  }
  
  .points-header {
    flex-direction: column;
    gap: 15px;
  }
  
  .injection-points-grid {
    grid-template-columns: 1fr;
  }
  
  .step-actions {
    padding: 15px 20px;
  }
}
</style>
