<!-- 步骤指示器组件 -->
<template>
  <div class="step-indicator">
    <div 
      v-for="(step, index) in steps" 
      :key="index"
      class="step-item"
      :class="{ 
        active: currentStep === index + 1,
        completed: currentStep > index + 1 
      }"
    >
      <div class="step-circle">
        <el-icon v-if="currentStep > index + 1"><Check /></el-icon>
        <span v-else>{{ index + 1 }}</span>
      </div>
      <div class="step-label">{{ step.label }}</div>
      <div v-if="index < steps.length - 1" class="step-line"></div>
    </div>
  </div>
</template>

<script setup>
import { Check } from '@element-plus/icons-vue'

defineProps({
  currentStep: {
    type: Number,
    required: true
  }
})

const steps = [
  { label: '输入URL' },
  { label: 'Smart Crawling' },
  { label: 'Select Injection Point' },
  { label: 'XSS测试' }
]
</script>

<style scoped>
.step-indicator {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30px 60px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 30px;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
}

.step-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #e4e7ed;
  color: #909399;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 18px;
  transition: all 0.3s ease;
  z-index: 2;
}

.step-item.active .step-circle {
  background: linear-gradient(135deg, #409eff, #3a8ee6);
  color: white;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  transform: scale(1.1);
}

.step-item.completed .step-circle {
  background: #67c23a;
  color: white;
}

.step-label {
  margin-top: 12px;
  font-size: 14px;
  color: #909399;
  font-weight: 500;
  transition: all 0.3s ease;
}

.step-item.active .step-label {
  color: #409eff;
  font-weight: 600;
}

.step-item.completed .step-label {
  color: #67c23a;
}

.step-line {
  position: absolute;
  top: 24px;
  left: calc(50% + 24px);
  width: calc(100% - 48px);
  height: 2px;
  background: #e4e7ed;
  z-index: 1;
  transition: all 0.3s ease;
}

.step-item.completed .step-line {
  background: #67c23a;
}

@media (max-width: 768px) {
  .step-indicator {
    padding: 20px 15px;
  }
  
  .step-circle {
    width: 36px;
    height: 36px;
    font-size: 14px;
  }
  
  .step-label {
    font-size: 12px;
  }
}
</style>
