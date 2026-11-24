# Linux reproduction of the cisb-llvm-ir toolchain (macOS original: Homebrew LLVM 23.1.4 + alive2 21.0_9).
# LLVM 23 from apt.llvm.org; Alive2 = tag v21.0 + the same two upstream commits Homebrew backports
# (a86aaa0 "PassPlugin.h moved upstream", 155386f "remove Os and Oz pipelines").
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates wget gnupg git cmake ninja-build g++ make re2c \
      libz3-dev z3 python3 perl file \
    && rm -rf /var/lib/apt/lists/*

ARG LLVM_MAJOR=23
RUN wget -qO /etc/apt/trusted.gpg.d/apt.llvm.org.asc https://apt.llvm.org/llvm-snapshot.gpg.key \
    && echo "deb http://apt.llvm.org/noble/ llvm-toolchain-noble-${LLVM_MAJOR} main" > /etc/apt/sources.list.d/llvm.list \
    && apt-get update && apt-get install -y --no-install-recommends \
      clang-${LLVM_MAJOR} llvm-${LLVM_MAJOR} llvm-${LLVM_MAJOR}-dev llvm-${LLVM_MAJOR}-tools \
      libclang-rt-${LLVM_MAJOR}-dev libclang-common-${LLVM_MAJOR}-dev \
      libpolly-${LLVM_MAJOR}-dev zlib1g-dev libzstd-dev libedit-dev libffi-dev libxml2-dev libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

ARG ALIVE2_REF=v21.0
ARG ALIVE2_PICKS="a86aaa0ea44c5671ce3e998ec6d422feaa95b236 155386f37536a8f64d78c0ef7d52f7d3f1926cd1"
RUN git clone https://github.com/AliveToolkit/alive2.git /opt/alive2 \
    && cd /opt/alive2 && git checkout -q ${ALIVE2_REF} \
    && for c in ${ALIVE2_PICKS}; do git -c user.name=build -c user.email=build@localhost cherry-pick -x $c; done \
    && git log --oneline -4 > /opt/alive2/BUILD_REF.txt \
    && cmake -S . -B build -GNinja -DCMAKE_BUILD_TYPE=Release -DBUILD_TV=1 \
         -DCMAKE_CXX_FLAGS="-Wno-error=deprecated-declarations" \
         -DLLVM_DIR=/usr/lib/llvm-${LLVM_MAJOR}/lib/cmake/llvm \
    && ninja -C build alive-tv \
    && rm -rf build/CMakeFiles

WORKDIR /workspace
