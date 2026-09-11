// Allow Slidev's code-snippet importer (`<<< ../samples/...`) to read files
// from the repo root, one level above this slides/ project. This is what
// turns the deck into a build artifact of the real sample sources.
//
// Exported as a plain object (not wrapped in vite's `defineConfig`) so it needs
// no top-level `vite` dependency under the hermetic Bazel-linked node_modules —
// `vite` is only a transitive dep of @slidev/cli. `defineConfig` was just a
// type helper.
export default {
  server: {
    fs: {
      // '..' for the `<<< ../samples/...` transclusion; strict:false so the
      // hermetic Bazel build (files staged under bazel-bin via symlinks) isn't
      // rejected by Vite's realpath allow-list check on `<img>` asset imports.
      strict: false,
      allow: ['..'],
    },
  },
}
