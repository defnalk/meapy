# Dockerfile — Multi-stage build for the meapy package.
#
# Stage 1 (builder) installs dev dependencies, builds a wheel, and runs the
# test suite so the build fails fast on regressions. Stage 2 (runtime) is a
# minimal image containing only the wheel + its runtime dependencies, running
# as a non-root user.
#
# Modify this file when:
#   - Python base image needs bumping
#   - Runtime system packages change
#   - The CLI entrypoint changes (see ENTRYPOINT below)

# ──────────────────────────────────────────────────────────────────────────
# Stage 1 — Builder
# ──────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# System build deps (BLAS/LAPACK for numpy/scipy wheels usually unneeded — slim
# images use manylinux wheels — but gcc is kept as a safety net for sdists).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first for cache reuse
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

# Install with dev extras + run tests inside the builder
RUN pip install --upgrade pip build \
 && pip install -e ".[dev]" \
 && pytest tests/unit -q --no-cov \
 && python -m build --wheel --outdir /wheels .

# ──────────────────────────────────────────────────────────────────────────
# Stage 2 — Runtime
# ──────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LOG_LEVEL=INFO

# Non-root user
RUN groupadd --system --gid 1000 meapy \
 && useradd  --system --uid 1000 --gid meapy --create-home --shell /bin/bash meapy

# Install only the wheel + its runtime deps
COPY --from=builder /wheels/*.whl /tmp/
RUN pip install --upgrade pip \
 && pip install /tmp/*.whl \
 && rm -rf /tmp/*.whl /root/.cache

USER meapy
WORKDIR /home/meapy

# Healthcheck — exits 0 if the package imports cleanly
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import meapy; print(meapy.__version__)" || exit 1

ENTRYPOINT ["python", "-m", "meapy"]
CMD ["--help"]
