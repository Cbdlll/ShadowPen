<script setup>
import { ref } from 'vue'

const adData = ref({
  imageUrl: 'https://placehold.co/1200x100/e74c3c/ffffff?text=Special+Offer+-+50%25+OFF',
  linkUrl: '#'
})
</script>

<template>
  <div class="ad-banner">
    <a :href="adData.linkUrl" class="ad-link">
      <img :src="adData.imageUrl" alt="Advertisement" class="ad-image" />
    </a>
  </div>
</template>

<style scoped>
.ad-banner {
  margin-bottom: 20px;
  width: 100%;
}

.ad-link {
  display: block;
  width: 100%;
}

.ad-image {
  width: 100%;
  height: auto;
  border-radius: 4px;
}
</style>
