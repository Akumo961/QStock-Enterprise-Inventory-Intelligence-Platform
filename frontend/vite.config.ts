import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';
import { pwaConfig } from './pwa-config.js';
import basicSsl from '@vitejs/plugin-basic-ssl';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [
      basicSsl(),

      react({
         fastRefresh: true,
         babel: {
           plugins: ['@emotion/babel-plugin'],
        },
      }),

  VitePWA(pwaConfig),
],

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@pages': path.resolve(__dirname, './src/pages'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
        '@services': path.resolve(__dirname, './src/services'),
        '@utils': path.resolve(__dirname, './src/utils'),
        '@types': path.resolve(__dirname, './src/types'),
        '@assets': path.resolve(__dirname, './src/assets'),
      },
    },

    server: {
      port: 5173,
      host: true,
      open: false,
      cors: true,

      https: true,

      proxy: {
        // The AI /api/ai/chat endpoint can take 60-120 s on local CPU/GPU
        // hardware. Vite's http-proxy inherits Node.js's default socket idle
        // timeout (~60 s) unless overridden, which silently drops long-running
        // AI requests and makes the frontend show "something went wrong" even
        // though the backend completed successfully with HTTP 200.
        // proxyTimeout = how long to wait for the target to respond (ms)
        // timeout      = how long the socket can be idle (ms)
        '/api/ai': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          proxyTimeout: 300000,   // 5 minutes — covers worst-case CPU inference
          timeout: 300000,
        },
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          proxyTimeout: 30000,
          timeout: 30000,
        },
      },

      hmr: {
        host: '192.168.2.1',
        port: 5173,
        // When Vite runs with https:true it serves over HTTPS, so HMR
        // WebSockets must use wss:// not ws:// — the mismatch was causing the
        // flood of ERR_EMPTY_RESPONSE errors in the browser console.
        protocol: 'wss',
        overlay: true,
      },
    },

    preview: {
      port: 4173,
      host: true,
      open: true,
    },

    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: mode === 'development',
      minify: 'terser',

      terserOptions: {
        compress: {
          drop_console: mode === 'production',
          drop_debugger: mode === 'production',
        },
      },

      rollupOptions: {
        output: {
          manualChunks: {
            'react-core': ['react', 'react-dom'],
            'react-router': ['react-router-dom'],
            'mui-core': [
              '@mui/material',
              '@mui/system',
              '@emotion/react',
              '@emotion/styled',
            ],
            'mui-icons': ['@mui/icons-material'],
            'date-utils': ['date-fns'],
            'qr-libs': ['html5-qrcode', 'qrcode'],
            'utils': ['notistack'],
          },

          assetFileNames: (assetInfo) => {
            const info = assetInfo.name?.split('.');
            let extType = info?.[info.length - 1];

            if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType ?? '')) {
              extType = 'images';
            } else if (/woff|woff2|eot|ttf|otf/i.test(extType ?? '')) {
              extType = 'fonts';
            }

            return `assets/${extType}/[name]-[hash][extname]`;
          },

          chunkFileNames: 'assets/js/[name]-[hash].js',
          entryFileNames: 'assets/js/[name]-[hash].js',
        },
      },

      chunkSizeWarningLimit: 1000,
      assetsInlineLimit: 4096,
      cssCodeSplit: true,
      reportCompressedSize: true,
      manifest: true,
    },

    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@mui/material',
        '@mui/icons-material',
        'date-fns',
        'notistack',
      ],
      exclude: ['@vite/client', '@vite/env'],
    },

    css: {
      devSourcemap: mode === 'development',
      modules: {
        localsConvention: 'camelCase',
      },
      preprocessorOptions: {
        scss: {
          additionalData: `$injectedColor: orange;`,
        },
      },
    },

    define: {
      __APP_VERSION__: JSON.stringify(env.VITE_APP_VERSION || '1.0.0'),
      __APP_NAME__: JSON.stringify(env.VITE_APP_NAME || 'QR Inventory System'),
    },

    esbuild: {
      logOverride: { 'this-is-undefined-in-esm': 'silent' },
      drop: mode === 'production' ? ['console', 'debugger'] : [],
    },

    json: {
      stringify: true,
    },
  };
});