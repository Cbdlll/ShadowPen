import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue()],
    server: {
        proxy: {
            '/api': process.env.BACKEND_URL || 'http://localhost:8000',
            '/ws': {
                target: process.env.WS_BACKEND_URL || 'ws://localhost:8000',
                ws: true
            }
        }
    }
})
