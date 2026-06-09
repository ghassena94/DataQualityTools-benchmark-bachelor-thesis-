FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Berlin

# Install system dependencies.
# postgresql is NOT installed here — it runs as a separate container
# defined in docker-compose.yml. Only the client tools (psql, pg_isready)
# from postgresql-client are needed so the entrypoint can wait for the DB.
# swig is required by auto-sklearn and smac (C extension build tools).
RUN apt-get update && apt-get install -y \
    python3.8 python3.8-dev python3-pip python3.8-venv \
    git wget curl build-essential libpq-dev postgresql-client \
    sudo openjdk-11-jdk make g++ libssl-dev libffi-dev \
    libsuitesparse-dev swig \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# Setup virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# py_entitymatching imports tkinter at load time for its GUI explorer.
# python3-tk installs tkinter for the system Python but not inside the venv.
# The symlink makes it visible to the venv without needing --system-site-packages.
RUN ln -s /usr/lib/python3.8/tkinter /opt/venv/lib/python3.8/site-packages/tkinter

RUN python3 -m pip install "pip<24.1" setuptools wheel

WORKDIR /rein

# Copy local repository
COPY . /rein

# Pre-install build dependencies for scikit-sparse to avoid Cython 3.0+ bug
RUN pip3 install "Cython==0.29.36" numpy==1.21.2 scipy==1.7.1
RUN pip3 install --no-build-isolation scikit-sparse==0.4.5

# Install PyTorch CPU wheels.
# Architecture-aware installation:
#   x86_64  → torch 1.10.2+cpu from PyTorch's own index (the +cpu suffix wheels
#              are Linux x86 only and are NOT on PyPI).
#   aarch64 → torch 1.13.1 from PyPI (1.10.2 has no Linux ARM64 wheels;
#              1.13.1 is the last stable 1.x release and has full ARM64 support).
# typing-extensions is pinned to 4.1.1 in both cases because PyTorch's index
# serves 4.15.0 which requires Python >=3.9 and would break our Python 3.8 build.
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        pip3 install \
            "typing-extensions==4.1.1" \
            torch==1.10.2+cpu \
            torchvision==0.11.3+cpu \
            torchaudio==0.10.2+cpu \
            --extra-index-url https://download.pytorch.org/whl/cpu; \
    else \
        pip3 install \
            "typing-extensions==4.1.1" \
            torch==1.13.1 \
            torchvision==0.14.1 \
            torchaudio==0.13.1; \
    fi

# Install remaining requirements.
# Two inline fixes applied via grep/sed:
#   1. Skip torch/torchvision/torchaudio — already installed above.
#   2. mxnet==1.4.0 → mxnet==1.9.1 — version 1.4.0 has no Python 3.8
#      wheels on PyPI (only Python 2.7/3.5/3.6/3.7). Version 1.9.1 is the
#      last 1.x release, supports Python 3.8, and satisfies datawig's
#      requirement mxnet>=1.4.0,<2.0.0.
RUN grep -v "^torch\|^torchvision\|^torchaudio" requirements.txt \
    | sed 's/mxnet==1\.4\.0/mxnet==1.9.1/' \
    | pip3 install -r /dev/stdin

# Compile the FAHES C++ shared library (libFahes.so).
# FAHES is an error detector that ships as C++ source code.
# The Python wrapper loads this .so at runtime via ctypes.
RUN cd cleaners/FAHES/src && make clean && make

# Install REIN core package and local sub-packages in editable mode.
# tools/error-generator provides the `error_generator` module imported by
# rein/auxiliaries/configurations.py. tools/Profiler is the data profiler.
# Neither is on PyPI — they must be installed from the local source tree.
RUN pip3 install -e . \
    && pip3 install -e tools/error-generator \
    && pip3 install -e tools/Profiler \
    && pip3 install sqlalchemy-utils

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
