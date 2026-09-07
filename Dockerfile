# ABOUTME: Two-stage build producing a minimal, non-root image whose entrypoint is the
# ABOUTME: Spec & Design Agent CLI. The agent runs as a bounded job, not a long-lived service.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY schemas ./schemas
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm
WORKDIR /app
# git is required for workspace verification and the single agent-owned artifact commit.
RUN apt-get update \
  && apt-get install --no-install-recommends -y git ca-certificates \
  && rm -rf /var/lib/apt/lists/* \
  && useradd --system --uid 10001 --create-home specagent
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
COPY --from=build /app/schemas /app/schemas
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH="/app/src"
USER specagent
ENTRYPOINT ["python", "-m", "spec_design_agent"]
CMD ["--help"]
