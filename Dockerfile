# builder configuration
FROM python:3.13-slim as builder

ARG QI_REPOSITORY="https://github.com/aldebaran/libqi.git"
ARG QI_VERSION="4.0.5"
ARG QI_PATH="$HOME/libqi"

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libpython3-dev \
    patchelf \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade \
    pip \
    "conan>=2.0.0,<3.0.0" \
    "cmake>=3.23" \
    build \
    auditwheel

RUN conan profile detect --force

WORKDIR /tmp

RUN git clone \
    --depth 1 \
    --branch "qi-framework-v${QI_VERSION}" \
    "${QI_REPOSITORY}" \
    "${QI_PATH}"
    
RUN conan export "${QI_PATH}" \
    --version "${QI_VERSION}"

RUN git clone \
    --depth 1 \
    https://github.com/aldebaran/libqi-python.git \
    /tmp/libqi-python

WORKDIR /tmp/libqi-python
    
RUN conan install . \
    --build=missing \
    -c tools.build:skip_test=true

RUN python -m build \
    --config-setting cmake.define.CMAKE_TOOLCHAIN_FILE=$PWD/build/linux-x86_64-gcc-release/generators/conan_toolchain.cmake

RUN auditwheel repair \
    --strip \
    --plat auto \
    dist/qi-*.whl

# dev configuration
FROM python:3.13-slim as dev

RUN apt-get update && apt-get install -y \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libglib2.0-0 \
    libgles2-mesa-dev \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PYTHONBUFFERED=1

COPY --from=builder /tmp/libqi-python/wheelhouse /tmp/wheelhouse

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir /tmp/wheelhouse/qi-*.whl \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -rf /tmp/wheelhouse /tmp/requirements.txt

WORKDIR /opt/nvidia-riva
RUN git clone https://github.com/nvidia-riva/python-clients.git

WORKDIR /workspaces/nao
CMD ["/bin/bash"]