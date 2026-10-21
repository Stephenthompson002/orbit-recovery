FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY . /tests/
RUN mkdir -p /workspace/orbit_recovery /logs/verifier
RUN useradd --system --no-create-home --shell /usr/sbin/nologin orbitrunner \
    && chown -R root:root /tests /logs \
    && chmod -R go-rwx /tests /logs
RUN chmod +x /tests/test.sh
WORKDIR /workspace
