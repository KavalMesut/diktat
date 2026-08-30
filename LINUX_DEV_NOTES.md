# Linux development notes

Date: 2026-08-30
Branch: `linux-development`

## Current state

- Diktat runs as the transient user service `diktat.service`.
- The selected input is the raw ReSpeaker device:
  `reSpeaker XVF3800 4-Mic Array: USB Audio (hw:0,0)`.
- Latest capture succeeded: 44,032 samples, RMS 0.016150, peak 0.119507.
- Automatic gain applied: 5.0x.
- CUDA runtime issue was fixed by installing cuBLAS/cuDNN wheels and exporting
  their library directories in `run_diktat.sh`.
- Faster-Whisper now runs on the RTX 4060 Ti and uses about 2.2 GB VRAM.
- CUDA transcription, clipboard copy and automatic paste now work end-to-end.
- The Linux IPC shortcut uses a native Unix socket instead of initializing Qt,
  so the original editor keeps focus and receives the automatic Ctrl+V.

## Resolved audio bug

The microphone was recording correctly. Faster-Whisper initially failed because
`libcublas.so.12` was unavailable, and transcription could also wait behind the
Gemma loading lock. The CUDA runtime libraries are now installed/exported and
Whisper/LLM loading uses separate locks.

## Possible future audio work

The current mono 16 kHz ReSpeaker path works. If recognition quality needs
further tuning later, compare both hardware channels independently rather than
averaging them.

## HUD state

- A KWin Wayland helper positions the `Diktat HUD` window.
- Vertical placement is correct: the HUD sits immediately above the taskbar.
- Remaining known issue: on this three-monitor KDE Wayland layout, the HUD stays
  on the rightmost screen instead of the middle/main screen. This is accepted
  for now and can be revisited later without blocking the Linux release.

## Git state

- Linux work is maintained on the `linux-development` branch and is ready for
  integration after validation on KDE Wayland.
