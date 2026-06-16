# The "docker tax" baseline: make the test run hermetic by putting it in a
# container. pytest installs above the COPY, so an incremental "code change"
# (marker.txt) re-runs only COPY + the test — but still pays daemon + layer
# overhead on every iteration, with no fine-grained action caching.
#
#   docker build -t pytest-tax benchmark/pytest_tax
FROM python:3.12-slim-bookworm
RUN pip install --no-cache-dir pytest
WORKDIR /app
COPY marker.txt /app/marker.txt
COPY calc.py calc_test.py /app/
RUN python -m pytest -q calc_test.py
