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

ARG USERNAME=dev
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ARG HOME_DIR=/home/dev

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash \
    && apt-get update \
    && apt-get install -y sudo curl \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && apt-get install -y git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/opencode.tar.gz https://github.com/anomalyco/opencode/releases/latest/download/opencode-linux-x64.tar.gz \
    && tar -xzf /tmp/opencode.tar.gz -C /tmp \
    && mv /tmp/opencode /usr/local/bin/opencode \
    && chmod +x /usr/local/bin/opencode \
    && rm /tmp/opencode.tar.gz

ENV PYTHONUNBUFFERED=1

RUN mkdir -p $HOME_DIR/.config/opencode \
    $HOME_DIR/.local/share/opencode \
    $HOME_DIR/.local/state/opencode \
    && chown -R $USERNAME:$USERNAME $HOME_DIR/.config $HOME_DIR/.local

COPY --from=builder /tmp/libqi-python/wheelhouse /tmp/wheelhouse

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir /tmp/wheelhouse/qi-*.whl \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -rf /tmp/wheelhouse /tmp/requirements.txt

USER $USERNAME
WORKDIR /home/nao-agent
CMD ["/bin/bash"]

# production configuration
FROM python:3.13-slim as production

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 nao \
    && useradd --uid 1000 --gid 1000 --create-home nao -s /bin/bash

COPY --from=builder /tmp/libqi-python/wheelhouse /tmp/wheelhouse

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir /tmp/wheelhouse/qi-*.whl \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -rf /tmp/wheelhouse /tmp/requirements.txt /root/.cache

COPY python /app/python
COPY data /app/data

WORKDIR /app/python
USER nao

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/python

ENTRYPOINT ["python", "-m", "main"]