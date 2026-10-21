FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY orbit_recovery /workspace/orbit_recovery
COPY examples /workspace/examples
RUN useradd --system --no-create-home --shell /usr/sbin/nologin orbitrunner
WORKDIR /workspace

CMD ["python", "-m", "orbit_recovery.cli"]
