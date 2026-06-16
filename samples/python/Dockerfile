# The "before": a traditional, imperative Dockerfile build (TASK §2.2).
# Why it matters and how the Bazel variants compare: see samples/README.md.

#region dockerfile
FROM python:3.12-slim-bookworm

# System dependency: the `dot` binary. Imperative, daemon-run, cache-coarse.
RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz \
    && rm -rf /var/lib/apt/lists/*

# Python dependency layer.
COPY requirements_lock.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# App-source layer (changes here invalidate everything below in a Dockerfile).
WORKDIR /app
COPY app.py /app/app.py

ENTRYPOINT ["python", "/app/app.py", "--render", "/tmp/supply_chain.png"]
#endregion
