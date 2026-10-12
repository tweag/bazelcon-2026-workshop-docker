# Slides as PDF

📄 **[Download the deck (v0.2.0)](https://github.com/tweag/bazelcon-2026-workshop-docker-build/releases/download/v0.2.0/building-without-bytes.pdf)**
· newer versions are on the [Releases](https://github.com/tweag/bazelcon-2026-workshop-docker-build/releases) page.

The PDF isn't tracked in git (it's ~76 MB). The `pdf` workflow exports it from
each release's tag and attaches it to that release. To build it yourself:

```bash
bazel run //slides:export_pdf   # -> docs/building-without-bytes.pdf
```
