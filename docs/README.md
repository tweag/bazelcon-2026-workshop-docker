# Slides as PDF

📄 **[Download the deck](https://github.com/tweag/bazelcon-2026-workshop-docker/releases/latest/download/building-without-bytes.pdf)**
· every version is on the [Releases](https://github.com/tweag/bazelcon-2026-workshop-docker/releases) page.

The PDF isn't tracked in git (it's ~76 MB). The `pdf` workflow exports it from
each release's tag and attaches it to that release. To build it yourself:

```bash
bazel run //slides:export_pdf   # -> docs/building-without-bytes.pdf
```
