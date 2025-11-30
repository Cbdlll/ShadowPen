<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps({
  productId: Number
})

const reviews = ref([])
const newReview = ref({
  author: '',
  title: '',
  content: '',
  rating: 5,
  productId: props.productId
})

const fetchReviews = async () => {
  try {
    const response = await axios.get(`/api/reviews/product/${props.productId}`)
    reviews.value = response.data
  } catch (error) {
    console.error('Error fetching reviews:', error)
  }
}

const submitReview = async () => {
  try {
    await axios.post('/api/reviews', newReview.value)
    newReview.value = { author: '', title: '', content: '', rating: 5, productId: props.productId }
    await fetchReviews()
  } catch (error) {
    console.error('Error submitting review:', error)
  }
}

onMounted(fetchReviews)
</script>

<template>
  <div class="reviews-section">
    <h2>Customer Reviews</h2>
    
    <div class="review-form">
      <h3>Write a Review</h3>
      <input v-model="newReview.author" placeholder="Your Name" />
      <input v-model="newReview.title" placeholder="Review Title" />
      <textarea v-model="newReview.content" placeholder="Write your review here..."></textarea>
      <select v-model="newReview.rating">
        <option v-for="n in 5" :key="n" :value="n">{{ n }} Stars</option>
      </select>
      <button @click="submitReview">Submit Review</button>
    </div>

    <div class="review-list">
      <div v-for="review in reviews" :key="review.id" class="review-item">
        <div class="review-header">
          <span class="author">{{ review.author }}</span>
          <span class="rating">
            <span v-for="n in 5" :key="n" class="star" :class="{ filled: n <= review.rating }">★</span>
          </span>
        </div>
        <h4>{{ review.title }}</h4>
        <p class="review-content">{{ review.content }}</p>
        
        <div v-if="review.sellerReply" class="seller-reply">
          <strong>Seller Reply:</strong>
          <p>{{ review.sellerReply }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reviews-section {
  background: white;
  padding: 20px;
  border-radius: 4px;
}

.review-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 30px;
  padding: 20px;
  background: #f9f9f9;
  border: 1px solid #ddd;
}

.review-item {
  border-bottom: 1px solid #eee;
  padding: 15px 0;
}

.author {
  font-weight: bold;
  margin-right: 10px;
}

.seller-reply {
    margin-top: 10px;
    padding: 10px;
    background-color: #f0f8ff;
    border-left: 3px solid #007bff;
}
</style>
