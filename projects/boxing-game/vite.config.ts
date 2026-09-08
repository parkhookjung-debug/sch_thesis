import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // The pose-detection package statically imports `@mediapipe/pose` even
      // when only MoveNet is used. The shipped @mediapipe/pose ESM is broken
      // (does not actually export `Pose`), so we redirect to a local stub.
      '@mediapipe/pose': fileURLToPath(new URL('./src/stubs/mediapipe-pose.ts', import.meta.url)),
    },
  },
})
