<script setup>
import SearchBar from './components/SearchBar.vue'
import { ref, onMounted } from 'vue'

const errorMessage = ref('')

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  
  if (params.has('error')) {
    errorMessage.value = params.get('error')
  }
})
</script>

<template>
  <div class="app-container">
    <header>
      <nav class="navbar">
        <div class="logo">Spring Shop</div>
        <SearchBar />
        <div class="nav-links">
          <router-link to="/">Home</router-link>
          <router-link to="/cart">Cart</router-link>
        </div>
      </nav>
    </header>

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <main>
      <router-view></router-view>
    </main>

    <footer>
      <p>&copy; 2023 Spring Shop. All rights reserved.</p>
    </footer>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

header {
  background-color: #131921;
  color: white;
  padding: 10px 20px;
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
}

.nav-links a {
  color: white;
  text-decoration: none;
  margin-left: 20px;
}

main {
  flex: 1;
  background-color: #eaeded;
  padding: 20px;
}

footer {
  background-color: #232f3e;
  color: white;
  text-align: center;
  padding: 20px;
}
</style>
