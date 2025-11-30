<script setup>
import { ref, onMounted, computed } from 'vue'

const cartItems = ref([])

onMounted(() => {
  const savedCart = localStorage.getItem('cart')
  if (savedCart) {
    cartItems.value = JSON.parse(savedCart)
  }
})

const removeFromCart = (index) => {
  cartItems.value.splice(index, 1)
  localStorage.setItem('cart', JSON.stringify(cartItems.value))
}

const total = computed(() => {
  return cartItems.value.reduce((sum, item) => sum + item.price, 0)
})

const checkout = () => {
  alert('Checkout functionality coming soon!')
}
</script>

<template>
  <div class="cart-container">
    <h1>Your Shopping Cart</h1>
    
    <div v-if="cartItems.length === 0" class="empty-cart">
      <p>Your cart is empty.</p>
      <router-link to="/" class="continue-shopping">Continue Shopping</router-link>
    </div>
    
    <div v-else class="cart-content">
      <div class="cart-items">
        <div v-for="(item, index) in cartItems" :key="index" class="cart-item">
          <img :src="item.imageUrl" :alt="item.name" class="item-image" />
          <div class="item-details">
            <h3>{{ item.name }}</h3>
            <p class="item-price">${{ item.price.toFixed(2) }}</p>
          </div>
          <button @click="removeFromCart(index)" class="remove-btn">Remove</button>
        </div>
      </div>
      
      <div class="cart-summary">
        <h2>Order Summary</h2>
        <div class="summary-row">
          <span>Subtotal</span>
          <span>${{ total.toFixed(2) }}</span>
        </div>
        <div class="summary-row total">
          <span>Total</span>
          <span>${{ total.toFixed(2) }}</span>
        </div>
        <button @click="checkout" class="checkout-btn">Proceed to Checkout</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cart-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  margin-bottom: 2rem;
  color: #1a1a1a;
}

.empty-cart {
  text-align: center;
  padding: 4rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.continue-shopping {
  display: inline-block;
  margin-top: 1rem;
  color: #0071e3;
  text-decoration: none;
  font-weight: 500;
}

.cart-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
}

.cart-items {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.cart-item {
  display: flex;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid #eee;
}

.cart-item:last-child {
  border-bottom: none;
}

.item-image {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 8px;
  margin-right: 1.5rem;
}

.item-details {
  flex: 1;
}

.item-details h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
}

.item-price {
  color: #666;
  margin: 0;
}

.remove-btn {
  color: #ff3b30;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
}

.remove-btn:hover {
  text-decoration: underline;
}

.cart-summary {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  height: fit-content;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
  color: #666;
}

.summary-row.total {
  color: #1a1a1a;
  font-weight: 700;
  font-size: 1.2rem;
  border-top: 1px solid #eee;
  padding-top: 1rem;
  margin-top: 1rem;
}

.checkout-btn {
  width: 100%;
  background-color: #0071e3;
  color: white;
  border: none;
  padding: 1rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 1rem;
  transition: background-color 0.2s;
}

.checkout-btn:hover {
  background-color: #005bb5;
}

@media (max-width: 768px) {
  .cart-content {
    grid-template-columns: 1fr;
  }
}
</style>
