<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const searchQuery = ref('')
const suggestions = ref([])
const showSuggestions = ref(false)
const urlSearchParam = ref(route.query.q || '')

watch(() => route.query.q, (newVal) => {
  urlSearchParam.value = newVal || ''
})

const fetchSuggestions = async () => {
  if (searchQuery.value.length > 0) {
    try {
      const response = await axios.get(`/api/search/suggestions?q=${searchQuery.value}`)
      suggestions.value = response.data
      showSuggestions.value = true
    } catch (error) {
      console.error('Error fetching suggestions:', error)
    }
  } else {
    suggestions.value = []
    showSuggestions.value = false
  }
}

const search = () => {
  router.push({ query: { q: searchQuery.value } })
  showSuggestions.value = false
}
</script>

<template>
  <div class="search-container">
    <div class="search-box">
      <input 
        v-model="searchQuery" 
        @input="fetchSuggestions"
        @keyup.enter="search"
        placeholder="Search products..." 
        class="search-input"
      />
      <button @click="search" class="search-button">Search</button>
    </div>
    
    <div v-if="urlSearchParam" class="search-results">
      <p>Search results for: <span>{{ urlSearchParam }}</span></p>
    </div>

    <div v-if="showSuggestions && suggestions.length > 0" class="suggestions-dropdown">
      <div 
        v-for="(suggestion, index) in suggestions" 
        :key="index" 
        class="suggestion-item"
      >{{ suggestion }}</div>
    </div>
  </div>
</template>

<style scoped>
.search-container {
  position: relative;
  flex: 1;
  max-width: 600px;
  margin: 0 20px;
}

.search-box {
  display: flex;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 4px 0 0 4px;
}

.search-button {
  background-color: #febd69;
  border: none;
  padding: 8px 16px;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
}

.search-results {
  margin-top: 10px;
  padding: 10px;
  background: white;
  color: #333;
  border-radius: 4px;
}

.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-top: 5px;
  max-height: 300px;
  overflow-y: auto;
  z-index: 1000;
}

.suggestion-item {
  padding: 10px;
  cursor: pointer;
  color: #333;
}

.suggestion-item:hover {
  background-color: #f0f0f0;
}
</style>
