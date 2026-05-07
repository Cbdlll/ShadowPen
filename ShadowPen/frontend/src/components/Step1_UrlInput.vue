<!-- Step 1: URL Input -->
<template>
  <div class="url-input-step">
    <div class="step-content">
      <div class="welcome-section">
        <h1 class="step-title">🛡️ XSS Security Scan</h1>
        <p class="step-description">Enter the target URL. We will intelligently crawl and discover potential XSS injection points.</p>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" label-position="top" size="large">
        <el-form-item label="Target URL" prop="url">
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

        <!-- Advanced Options -->
        <el-collapse v-model="activeCollapse" class="advanced-options">
          <el-collapse-item title="⚙️ Advanced Options" name="advanced">
            <el-form-item label="Max Crawl Depth">
              <el-slider v-model="form.maxDepth" :min="1" :max="10" show-stops />
              <span class="option-hint">Current: {{ form.maxDepth }} level(s). Greater depth discovers more but takes longer.</span>
            </el-form-item>

            <el-form-item label="Max Pages">
              <el-input-number v-model="form.maxPages" :min="5" :max="100" :step="5" />
              <span class="option-hint">Limit the number of pages to crawl.</span>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>

      <!-- Example URLs -->
      <div class="examples">
        <span class="examples-label">Example URLs:</span>
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

    <!-- Action Bar -->
    <div class="step-actions">
      <el-button size="large" disabled>← Previous</el-button>
      <el-button 
        type="primary" 
        size="large"
        @click="handleStart"
        :loading="starting"
      >
        Start Crawling →
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
    { required: true, message: 'Please enter the target URL', trigger: 'blur' },
    {
      pattern: /^https?:\/\/.+/,
      message: 'URL must start with http:// or https://',
      trigger: 'blur'
    }
  ]
}

const handleStart = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    ElMessage.warning('Please check your input')
    return
  }

  starting.value = true
  
  // Brief delay so user can see loading state
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
