# Optional reproducible local toolchain. Alive2 remains an optional add-on.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 llvm-18 clang-18 libclang-rt-18-dev \
    && rm -rf /var/lib/apt/lists/*

COPY cisb_hunter /opt/cisb-hunter/cisb_hunter
ENV PYTHONPATH=/opt/cisb-hunter
WORKDIR /workspace
ENTRYPOINT ["python3", "-m", "cisb_hunter"]
