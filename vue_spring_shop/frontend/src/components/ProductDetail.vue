<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'
import ReviewList from './ReviewList.vue'
import QuestionList from './QuestionList.vue'
import AdBanner from './AdBanner.vue'

const route = useRoute()
const router = useRouter()
const product = ref(null)
const loading = ref(true)

onMounted(async () => {
  const productId = route.params.id || 1
  try {
    const response = await axios.get(`/api/products/${productId}`)
    product.value = response.data
  } catch (error) {
    console.error('Error fetching product:', error)
  } finally {
    loading.value = false
  }
})

const addToCart = () => {
  const currentCart = JSON.parse(localStorage.getItem('cart') || '[]')
  currentCart.push(product.value)
  localStorage.setItem('cart', JSON.stringify(currentCart))
  alert('Product added to cart!')
  router.push('/cart')
}
</script>

<template>
  <div class="product-page-container">
    <div v-if="loading" class="loading-state">Loading product details...</div>
    
    <div v-else-if="product" class="product-content">
      <AdBanner />
      
      <div class="product-main-card">
        <div class="product-image-section">
          <img :src="product.imageUrl" :alt="product.name" />
        </div>
        
        <div class="product-info-section">
          <h1 class="product-title">{{ product.name }}</h1>
          <div class="product-price">${{ product.price.toFixed(2) }}</div>
          <div class="product-description">
            <h3>About this item</h3>
            <p>{{ product.description }}</p>
          </div>
          
          <div class="action-buttons">
            <button class="add-to-cart-btn" @click="addToCart">Add to Cart</button>
            <button class="buy-now-btn" @click="addToCart">Buy Now</button>
          </div>
        </div>
      </div>

      <div class="product-sections">
        <ReviewList :productId="product.id" />
        <QuestionList :productId="product.id" />
      </div>
    </div>
    
    <div v-else class="error-state">Product not found</div>
  </div>
</template>

<style scoped>
.product-page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.loading-state, .error-state {
  text-align: center;
  font-size: 1.5rem;
  color: #666;
  margin-top: 4rem;
}

.product-main-card {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  background: white;
  padding: 2rem;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  margin-bottom: 2rem;
}

.product-image-section {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f8f9fa;
  border-radius: 12px;
  padding: 2rem;
}

.product-image-section img {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  transition: transform 0.3s ease;
}

.product-image-section img:hover {
  transform: scale(1.05);
}

.product-info-section {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.product-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 1rem 0;
  line-height: 1.2;
}

.product-price {
  font-size: 2rem;
  color: #2c3e50;
  font-weight: 600;
  margin-bottom: 1.5rem;
}

.product-description {
  margin-bottom: 2rem;
  color: #4a4a4a;
  line-height: 1.6;
}

.product-description h3 {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  margin-top: auto;
}

.add-to-cart-btn, .buy-now-btn {
  flex: 1;
  padding: 1rem;
  border-radius: 30px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.add-to-cart-btn {
  background-color: #f0f2f5;
  color: #1a1a1a;
}

.add-to-cart-btn:hover {
  background-color: #e4e6e9;
}

.buy-now-btn {
  background-color: #0071e3;
  color: white;
}

.buy-now-btn:hover {
  background-color: #005bb5;
  box-shadow: 0 4px 12px rgba(0, 113, 227, 0.3);
}

.product-sections {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

@media (max-width: 768px) {
  .product-main-card {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
  
  .product-title {
    font-size: 1.8rem;
  }
}
</style>
