<!-- 步骤1：URL输入 -->
<template>
  <div class="url-input-step">
    <div class="step-content">
      <div class="welcome-section">
        <h1 class="step-title">🛡️ 开始XSS安全扫描</h1>
        <p class="step-description">Enter Target URL网站URL，我们将智能爬取并发现潜在的XSS注入点</p>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" label-position="top" size="large">
        <el-form-item label="目标URL" prop="url">
          <el-input
            v-model="form.url"
            placeholder="https://example.com"
            @keyup.enter="handleStart"
          >
            <template #prefix>
              <el-icon><Link /></el-icon>
            </template>
          </el-input>
          <template #error="{ error }">
            <div class="error-tip">
              <el-icon><Warning /></el-icon>
              {{ error }}
            </div>
          </template>
        </el-form-item>

        <!-- 高级选项 -->
        <el-collapse v-model="activeCollapse" class="advanced-options">
          <el-collapse-item title="⚙️ 高级选项" name="advanced">
            <el-form-item label="最大爬取深度">
              <el-slider v-model="form.maxDepth" :min="1" :max="10" show-stops />
              <span class="option-hint">当前：{{ form.maxDepth }} 层（深度越大，发现越多，但耗时越长）</span>
            </el-form-item>

            <el-form-item label="最大页面数">
              <el-input-number v-model="form.maxPages" :min="5" :max="100" :step="5" />
              <span class="option-hint">限制爬取页面数量，避免过度爬取</span>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>

      <!-- 示例URL -->
      <div class="examples">
        <span class="examples-label">示例URL：</span>
        <el-tag 
          v-for="example in examples" 
          :key="example"
          class="example-tag"
          @click="form.url = example"
        >
          {{ example }}
        </el-tag>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="step-actions">
      <el-button size="large" disabled>← 上一步</el-button>
      <el-button 
        type="primary" 
        size="large"
        @click="handleStart"
        :loading="starting"
      >
        开始爬取 →
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Link, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['next'])

const formRef = ref(null)
const activeCollapse = ref([])
const starting = ref(false)

const form = reactive({
  url: '',
  maxDepth: 3,
  maxPages: 20
})

const examples = [
  'http://testphp.vulnweb.com',
  'http://127.0.0.1:3000'
]

const rules = {
  url: [
    { required: true, message: '请Enter Target URLURL', trigger: 'blur' },
    { 
      pattern: /^https?:\/\/.+/, 
      message: 'URL必须以http://或https://开头', 
      trigger: 'blur' 
    }
  ]
}

const handleStart = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    ElMessage.warning('请检查输入')
    return
  }

  starting.value = true
  
  // 延迟一点让用户看到loading状态
  setTimeout(() => {
    emit('next', {
      url: form.url,
      maxDepth: form.maxDepth,
      maxPages: form.maxPages
    })
    starting.value = false
  }, 300)
}
</script>

<style scoped>
.url-input-step {
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

.welcome-section {
  text-align: center;
  margin-bottom: 40px;
}

.step-title {
  font-size: 32px;
  color: #303133;
  margin-bottom: 16px;
  font-weight: 600;
}

.step-description {
  font-size: 16px;
  color: #606266;
  line-height: 1.8;
}

.error-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f56c6c;
}

.advanced-options {
  margin: 30px 0;
  border: none;
}

.option-hint {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.examples {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.examples-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.example-tag {
  cursor: pointer;
  transition: all 0.3s ease;
}

.example-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
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

@media (max-width: 768px) {
  .step-content {
    padding: 20px;
  }
  
  .step-title {
    font-size: 24px;
  }
  
  .step-actions {
    padding: 15px 20px;
  }
}
</style>
