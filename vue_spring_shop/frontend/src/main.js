import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import './style.css'
import App from './App.vue'
import ProductList from './components/ProductList.vue'
import ProductDetail from './components/ProductDetail.vue'
import Cart from './components/Cart.vue'

const routes = [
    { path: '/', component: ProductList },
    { path: '/product/:id', component: ProductDetail },
    { path: '/cart', component: Cart }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

createApp(App).use(router).mount('#app')
