# The "before": a traditional, imperative Dockerfile build (TASK §2.2).
#
# Note the system dependency handled the daemon way: `apt-get install graphviz`
# in a RUN layer. It works, but the layer is an opaque blob produced by a
# stateful daemon, and editing app.py below busts every layer after the COPY.
# Compare with //samples/python:image, where the same dependency is a
# declarative, content-addressed layer in the Bazel action graph.
#
# Build & run:
#   docker build -t bwb/python-graphviz-dockerfile samples/python
#   docker run --rm bwb/python-graphviz-dockerfile   # renders the PNG

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
