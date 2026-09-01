#!/usr/bin/env bash
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate

    # CUDA runtime wheels keep their shared libraries inside site-packages.
    # CTranslate2/Faster-Whisper loads them through the system dynamic loader.
    DIKTAT_CUDA_LIBS=""
    for DIKTAT_CUDA_DIR in "$VIRTUAL_ENV"/lib/python*/site-packages/nvidia/{cublas,cudnn,cuda_nvrtc,cuda_runtime}/lib; do
        if [ -d "$DIKTAT_CUDA_DIR" ]; then
            DIKTAT_CUDA_LIBS="${DIKTAT_CUDA_LIBS:+$DIKTAT_CUDA_LIBS:}$DIKTAT_CUDA_DIR"
        fi
    done
    if [ -n "$DIKTAT_CUDA_LIBS" ]; then
        export LD_LIBRARY_PATH="$DIKTAT_CUDA_LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    fi
fi

exec python diktat.py "$@"
