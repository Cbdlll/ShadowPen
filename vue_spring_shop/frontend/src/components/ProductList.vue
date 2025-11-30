<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const products = ref([])
const loading = ref(true)
const router = useRouter()
const route = useRoute()

onMounted(async () => {
  try {
    const response = await fetch('/api/products')
    products.value = await response.json()
  } catch (error) {
    console.error('Failed to fetch products:', error)
  } finally {
    loading.value = false
  }
})

const goToDetail = (id) => {
  router.push(`/product/${id}`)
}
</script>

<template>
  <div class="product-list-container">
    <div v-if="route.query.q" class="search-results-header">
      <h2>Search results for: <span>{{ route.query.q }}</span></h2>
    </div>

    <div v-if="loading" class="loading">Loading amazing products...</div>
    
    <div v-else class="product-grid">
      <div v-for="product in products" :key="product.id" class="product-card" @click="goToDetail(product.id)">
        <div class="image-container">
          <img :src="product.imageUrl" :alt="product.name" class="product-image" />
        </div>
        <div class="product-info">
          <h3 class="product-name">{{ product.name }}</h3>
          <p class="product-description">{{ product.description }}</p>
          <div class="product-footer">
            <span class="price">${{ product.price.toFixed(2) }}</span>
            <button class="view-btn">View Details</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.product-list-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.loading {
  text-align: center;
  font-size: 1.5rem;
  color: #666;
  margin-top: 3rem;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 2rem;
}

.product-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  cursor: pointer;
  display: flex;
  flex-direction: column;
}

.product-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.image-container {
  height: 200px;
  overflow: hidden;
  background-color: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.product-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.product-card:hover .product-image {
  transform: scale(1.05);
}

.product-info {
  padding: 1.5rem;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.product-name {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  color: #1a1a1a;
  font-weight: 600;
}

.product-description {
  color: #666;
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 1.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.product-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.price {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2c3e50;
}

.view-btn {
  background-color: #0071e3;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: 500;
  transition: background-color 0.2s;
}

.view-btn:hover {
  background-color: #005bb5;
}
</style>
