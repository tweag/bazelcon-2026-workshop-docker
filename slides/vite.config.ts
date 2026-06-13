import { defineConfig } from 'vite'

// Allow Slidev's code-snippet importer (`<<< ../samples/...`) to read files
// from the repo root, one level above this slides/ project. This is what
// turns the deck into a build artifact of the real sample sources.
export default defineConfig({
  server: {
    fs: {
      allow: ['..'],
    },
  },
})
