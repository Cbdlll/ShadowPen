<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps({
  productId: Number
})

const questions = ref([])
const newQuestion = ref({
  author: '',
  content: '',
  productId: props.productId
})

const fetchQuestions = async () => {
  try {
    const response = await axios.get(`/api/questions/product/${props.productId}`)
    questions.value = response.data
  } catch (error) {
    console.error('Error fetching questions:', error)
  }
}

const submitQuestion = async () => {
  try {
    await axios.post('/api/questions', newQuestion.value)
    newQuestion.value = { author: '', content: '', productId: props.productId }
    await fetchQuestions()
  } catch (error) {
    console.error('Error submitting question:', error)
  }
}

onMounted(fetchQuestions)
</script>

<template>
  <div class="questions-section">
    <h2>Customer Questions & Answers</h2>
    
    <div class="question-form">
      <h3>Ask a Question</h3>
      <textarea v-model="newQuestion.content" placeholder="Your Question..."></textarea>
      <button @click="submitQuestion">Post Question</button>
    </div>

    <div class="question-list">
      <div v-for="question in questions" :key="question.id" class="question-item">
        <p class="question-content">{{ question.content }}</p>
        <p class="question-meta">Asked by 
          <span>{{ question.author }}</span> on {{ new Date(question.createdAt).toLocaleDateString() }}
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.questions-section {
  background: white;
  padding: 20px;
  border-radius: 4px;
}

.question-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 30px;
  padding: 20px;
  background: #f9f9f9;
  border: 1px solid #ddd;
}

.question-item {
  border-bottom: 1px solid #eee;
  padding: 15px 0;
}

.author {
  font-weight: bold;
}
</style>
