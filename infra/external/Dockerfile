ARG PYTHON_VERSION=3.14

FROM python:${PYTHON_VERSION}-slim
COPY --from=busybox:1.37-musl /bin/busybox /bin/wget
WORKDIR /app
COPY stub.py .
USER nobody
STOPSIGNAL SIGINT
CMD ["python", "stub.py"]
