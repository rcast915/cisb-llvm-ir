# Variant of cisb-linux whose alive-tv links Z3 5.3.2 (the version on the macOS run) instead of Ubuntu's 4.8.12.
FROM cisb-linux
ARG Z3_VERSION=5.3.2.0
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip && rm -rf /var/lib/apt/lists/* \
    && pip3 install --break-system-packages --no-cache-dir z3-solver==${Z3_VERSION} \
    && Z3DIR=$(python3 -c "import z3,os;print(os.path.dirname(z3.__file__))") \
    && ls $Z3DIR/lib $Z3DIR/include \
    && if [ ! -f $Z3DIR/include/z3_version.h ]; then python3 -c "import z3;M,m,b,r=z3.get_version();print(f'#define Z3_MAJOR_VERSION {M}\n#define Z3_MINOR_VERSION {m}\n#define Z3_BUILD_NUMBER {b}\n#define Z3_REVISION_NUMBER {r}')" > $Z3DIR/include/z3_version.h; fi \
    && cat $Z3DIR/include/z3_version.h \
    && cd /opt/alive2 && rm -rf build \
    && cmake -S . -B build -GNinja -DCMAKE_BUILD_TYPE=Release -DBUILD_TV=1 \
         -DCMAKE_CXX_FLAGS="-Wno-error=deprecated-declarations" \
         -DLLVM_DIR=/usr/lib/llvm-23/lib/cmake/llvm \
         -DZ3_INCLUDE_DIR=$Z3DIR/include -DZ3_LIBRARIES=$Z3DIR/lib/libz3.so \
         -DCMAKE_BUILD_RPATH=$Z3DIR/lib \
    && ninja -C build alive-tv && rm -rf build/CMakeFiles \
    && ldd build/alive-tv | grep z3 \
    && echo "z3 $(python3 -c 'import z3;print(z3.get_version_string())') (pip z3-solver)" >> /opt/alive2/BUILD_REF.txt
