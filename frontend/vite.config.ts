import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    /** 允许局域网/本机其他方式访问，避免仅绑定 localhost 导致「打不开」 */
    host: true,
    /** 5173 被占用时自动换端口，避免启动失败导致「页面打不开」 */
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  /** `npm run build && npm run preview` 时同样转发 API，否则 /api 会 404 导致首页数据异常 */
  preview: {
    port: 4173,
    host: true,
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
