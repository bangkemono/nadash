import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// vite.config.ts
export default defineConfig({
    plugins: [tailwindcss(), sveltekit()],
    server: {
        host: true,
    port:3000,
    strictPort:true,
        proxy: {
            '/api': {
                target: 'http://aiops-engine:8000',
                changeOrigin: true,
                secure: false,
                // Add this line to strip '/api' from the URL
                rewrite: (path) => path.replace(/^\/api/, '') 
            }
        }
    }
});
