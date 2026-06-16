% Build Without the Bytes: High-Velocity Image Composition at Scale
% BazelCon 2026 Workshop
% May 19, 2026

# Introduction

## The Workshop Goal
* Transition from **Imperative** (scripts) to **Declarative** (data) image builds.
* Achieve **Sub-Minute Iterations** for multi-gigabyte images.
* Eliminate dependencies on the **Docker Daemon** and root privileges.
* Understand the evolution from `rules_oci` to `rules_img`.

## The Problem: The "Black Box" Build
* Standard Dockerfiles are imperative scripts (`RUN apt-get install...`).
* **Non-deterministic**: `apt-get` today $\neq$ `apt-get` tomorrow.
* **Cache Invalidation**: Changing one early line breaks everything below.
* **The "Docker Socket" Dependency**: Security risks and CI bottlenecks.

# Pillar 1: From Imperative to Declarative

## Moving Beyond `RUN`
* In Bazel, we treat the filesystem as **pure data**.
* We don't "run" commands to create layers; we **assemble** them from pre-built artifacts.
* **Hermeticity**: Every input is tracked and content-addressed.

## Comparison: Dockerfile vs. rules_oci

**The Old Way (Dockerfile):**
```dockerfile
FROM python:3.9-slim
RUN apt-get update && apt-get install -y libpq-dev
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
CMD ["python", "/app/main.py"]
```

**The Bazel Way (rules_oci):**
```python
oci_image(
    name = "image",
    base = "@python_base",
    tars = [
        ":libs_layer",
        ":app_layer",
    ],
    entrypoint = ["python", "/app/main.py"],
)
```

# Pillar 2: High-Velocity Incrementalism

## Strategy: Build Without the Bytes
* **Partial Image Assembly**: Only re-compute what changed.
* **Layer Strategy**:
    1. **Base OS** (Static)
    2. **Runtimes/Dependencies** (Infrequent changes)
    3. **Application Code** (Frequent changes)
* Bazel only uploads the changed layer to the registry.

## From `rules_oci` to `rules_img`
* **rules_oci**: The industry standard. Uses `tar` to package layers.
* **rules_img**: The next step.
    * Avoids expensive `tar` compression steps during every build.
    * High-performance, Go-based incremental loader.
    * Treats layers as transparent blobs until the final assembly.

# Pillar 3: Daemonless & Security

## Breaking the Socket Dependency
* No `/var/run/docker.sock` needed.
* Build images on:
    * Restricted CI runners (no root).
    * macOS/Windows without a VM.
    * Side-by-side with other Bazel tasks.

## Verification: `container_structure_test`
* Validate image integrity in the Bazel sandbox.
* Check for file existence, content, and metadata without ever "running" the container.
```python
container_structure_test(
    name = "test",
    image = ":image",
    config = "test_config.yaml",
)
```

# Practical Comparison Snippets

## Interactive Demo: The 1-Second Rebuild

* **Setup**: A 1.5GB Python application image.
* **Action**: We change a single string in `main.py`.

**1. Traditional Docker Build:**
```bash
$ docker build -t myapp .
# ... invalidates cache at COPY . /app ...
# ... takes 2-3 minutes to re-run everything ...
```

**2. Bazel with rules_img:**
```bash
$ bazel run //src:image
# ... re-assembles only the application layer blob ...
# ... completed in < 2 seconds ...
```
*Notice how Bazel skipped all heavy operations because the graph proved they didn't change.*

## Comparing Tooling

| Feature | Dockerfile | rules_oci | rules_img |
|---------|------------|-----------|-----------|
| **Execution** | Imperative | Declarative | Optimized Declarative |
| **Hermetic** | No | Yes | Yes |
| **Speed** | Slow (Cache Miss) | Fast | Ultra-Fast |
| **Daemon Req.**| Yes | No | No |
| **Tar-less** | No | No | Yes |

# Conclusion

## Key Takeaways
1. **Stop Scripting, Start Mapping**: Use `rules_pkg` to define what goes where.
2. **Architect for Layers**: Keep heavy dependencies separate from volatile code.
3. **Go Daemonless**: Improve CI security and portability.
4. **Evaluate rules_img**: If `tar` is your bottleneck, it's time to upgrade.

## Q&A
* What about multi-stage builds?
* How to handle secret injection?
* Migrating legacy repositories.
