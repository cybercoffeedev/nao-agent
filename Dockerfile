# builder configuration
# Bookworm is pinned because libqi 4.0.5 is only validated with GCC 12; newer GCC
# versions diagnose ill-formed constructs in the vendored `ka` headers.
FROM python:3.13-slim-bookworm as builder

ARG QI_REPOSITORY="https://github.com/aldebaran/libqi.git"
ARG QI_VERSION="4.0.5"
# The 3.1.5 release does not build on Python 3.13 (`_Py_IsFinalizing` was removed).
# Pin the master commit that adds the `Py_IsFinalizing` compatibility branch until a
# release containing it exists.
ARG QI_PYTHON_REPOSITORY="https://github.com/aldebaran/libqi-python.git"
ARG QI_PYTHON_COMMIT="f51dbb31f22e8b154121ad60654776bd8ad81dc8"
ARG QI_PATH="/tmp/libqi"

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libpython3-dev \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Bookworm ships patchelf 0.14.3, which auditwheel 6 rejects. The PyPI package
# provides a statically linked binary in /usr/local/bin, which shadows the system one.
RUN pip install --no-cache-dir --upgrade \
    pip \
    "conan>=2.0.0,<3.0.0" \
    "cmake>=3.23,<4" \
    "build>=1,<2" \
    "auditwheel>=6,<7" \
    "patchelf>=0.14.5,<1"

RUN conan profile detect --force

WORKDIR /tmp

RUN git clone \
    --depth 1 \
    --branch "qi-framework-v${QI_VERSION}" \
    "${QI_REPOSITORY}" \
    "${QI_PATH}"
    
RUN conan export "${QI_PATH}" \
    --version "${QI_VERSION}"

RUN git init /tmp/libqi-python \
    && git -C /tmp/libqi-python remote add origin "${QI_PYTHON_REPOSITORY}" \
    && git -C /tmp/libqi-python fetch --depth 1 origin "${QI_PYTHON_COMMIT}" \
    && git -C /tmp/libqi-python checkout --detach FETCH_HEAD

WORKDIR /tmp/libqi-python
    
RUN conan install . \
    --build=missing \
    -c tools.build:skip_test=true

RUN python -m build \
    --config-setting cmake.define.CMAKE_TOOLCHAIN_FILE=${PWD}/build/linux-x86_64-gcc-release/generators/conan_toolchain.cmake

RUN auditwheel repair \
    --strip \
    --plat auto \
    dist/qi-*.whl

# dev configuration
FROM python:3.13-slim-bookworm as dev

ARG USERNAME=dev
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        git \
        openssh-client \
        sudo \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

COPY --from=builder /tmp/libqi-python/wheelhouse /tmp/wheelhouse

COPY requirements.txt requirements-dev.txt /tmp/

RUN pip install --no-cache-dir /tmp/wheelhouse/qi-*.whl \
    && pip install --no-cache-dir -r /tmp/requirements-dev.txt \
    && rm -rf /tmp/wheelhouse /tmp/requirements.txt /tmp/requirements-dev.txt

# Pre-create the OpenCode directory so the named volume keeps the dev user's ownership.
RUN mkdir -p /home/$USERNAME/.opencode \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME/.opencode

# Keep OpenCode state inside the named volume mounted at /home/$USERNAME/.opencode.
ENV XDG_CONFIG_HOME=/home/$USERNAME/.opencode/config \
    XDG_DATA_HOME=/home/$USERNAME/.opencode/data

USER $USERNAME
WORKDIR /workspace/nao-agent
CMD ["/bin/bash"]

# production configuration
FROM python:3.13-slim-bookworm as production

ARG USER_UID=1000
ARG USER_GID=1000

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid $USER_GID nao \
    && useradd --uid $USER_UID --gid $USER_GID --create-home nao -s /bin/bash

COPY --from=builder /tmp/libqi-python/wheelhouse /tmp/wheelhouse

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir /tmp/wheelhouse/qi-*.whl \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -rf /tmp/wheelhouse /tmp/requirements.txt /root/.cache

COPY python /app/python

RUN mkdir -p /app/data \
    && echo '{}' > /app/data/known_hosts.json \
    && chown -R nao:nao /app/data

WORKDIR /app/python
USER nao

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/python

ENTRYPOINT ["python", "main.py"]