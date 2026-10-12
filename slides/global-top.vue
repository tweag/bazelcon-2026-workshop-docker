<script setup>
import { computed } from 'vue'
import { useNav } from '@slidev/client'
// Inlined as markup rather than a CSS mask or an <img>. A CSS mask exports to
// PDF as a solid rectangle plus a rasterized alpha mask, which viewers that
// ignore soft masks paint as a solid green block; inline paths export as real
// vector geometry. The SVG sets no `fill` of its own, and `fill` inherits, so
// the paths take `currentColor` from .deck-logo below.
import tweagLogo from './images/tweag-logo.svg?raw'

// Persistent footer mark, rendered once on the top layer so the opaque
// content-slide backgrounds don't occlude it. The Tweag wordmark sits
// bottom-left; the repo URL keeps the bottom-right corner opposite it.
const { currentLayout } = useNav()

// The cover / section / statement layouts paint a dark green background, so the
// footer switches to a light color to stay legible there (see style.css).
// Slidev gives the first slide the `cover` layout by default, which is what the
// `bazel-cover` class then restyles into the BazelCon title card.
const isDark = computed(() => ['cover', 'section', 'statement'].includes(currentLayout.value))
</script>

<template>
  <div class="deck-footer-layer">
    <div class="deck-footer" :class="{ dark: isDark }">
      BazelCon 2026 ·
      <a href="https://github.com/tweag/bazelcon-2026-workshop-docker"
         target="_blank" rel="noopener">github.com/tweag/bazelcon-2026-workshop-docker</a>
    </div>
    <div class="deck-logo" :class="{ dark: isDark }" aria-hidden="true" v-html="tweagLogo" />
  </div>
</template>

<style scoped>
/* Full-slide layer that never eats clicks; only the link is interactive. */
.deck-footer-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.deck-footer {
  position: absolute;
  bottom: 0.7rem;
  right: 1.1rem;
  font-size: 0.7rem;
  letter-spacing: 0.03em;
  color: var(--bc-forest);
  opacity: 0.6;
}
/* Legible on the dark cover / section / statement surfaces. */
.deck-footer.dark {
  color: var(--bc-lime-light);
  opacity: 0.85;
}
.deck-footer a {
  color: inherit;
  text-decoration: none;
  pointer-events: auto;
}
.deck-footer a:hover {
  text-decoration: underline;
  opacity: 0.9;
}
/* The inlined mark takes its color from `currentColor`, so it tracks the same
   light/dark token switch as the footer text. The SVG carries a viewBox but no
   width/height, so height follows from the width and the artwork's aspect. */
.deck-logo {
  position: absolute;
  bottom: 0.7rem;
  left: 1.1rem;
  width: 5.2rem; /* viewBox is 580.3 x 156.4, so this renders ~1.4rem tall */
  color: var(--bc-forest);
  opacity: 0.85;
}
.deck-logo.dark {
  color: var(--bc-lime-light);
  opacity: 0.95;
}
/* v-html content sits outside the scoped-style rewrite, hence :deep(). */
.deck-logo :deep(svg) {
  display: block;
  width: 100%;
  height: auto;
  fill: currentColor;
}
</style>
