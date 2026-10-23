#!/bin/bash
# apply-overlay.sh — Apply Orange Pi 4 Pro overlay to Armbian build tree
#
# Usage:
#   ./scripts/apply-overlay.sh /path/to/armbian-build
#
# Supports both legacy (external/) and new (flat) Armbian build layouts.

set -euo pipefail

OVERLAY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARMBIAN_DIR="${1:?Usage: $0 /path/to/armbian-build}"

# Detect layout: new (flat) or legacy (external/)
if [[ -d "$ARMBIAN_DIR/config/boards" ]]; then
    LAYOUT="flat"
    CFGDIR="$ARMBIAN_DIR/config"
    PATCHDIR="$ARMBIAN_DIR/patch"
elif [[ -d "$ARMBIAN_DIR/external/config" ]]; then
    LAYOUT="external"
    CFGDIR="$ARMBIAN_DIR/external/config"
    PATCHDIR="$ARMBIAN_DIR/external/patch"
else
    echo "Error: $ARMBIAN_DIR does not look like an Armbian build tree"
    echo "Expected config/boards/ or external/config/boards/"
    exit 1
fi

echo "Applying Orange Pi 4 Pro overlay to $ARMBIAN_DIR (layout: $LAYOUT)"

# Board definition
echo "  Board definition → $CFGDIR/boards/orangepi4pro.conf"
mkdir -p "$CFGDIR/boards"
cp "$OVERLAY_DIR/config/boards/orangepi4pro.conf" \
   "$CFGDIR/boards/orangepi4pro.conf"

# Bootscripts
echo "  Bootscripts → $CFGDIR/bootscripts/"
mkdir -p "$CFGDIR/bootscripts"
if [[ -d "$OVERLAY_DIR/config/bootscripts" ]]; then
    cp -r "$OVERLAY_DIR/config/bootscripts/"* "$CFGDIR/bootscripts/"
fi

# Kernel config
echo "  Kernel config → $CFGDIR/kernel/linux-sun60iw2-next-a733.config"
mkdir -p "$CFGDIR/kernel"
cp "$OVERLAY_DIR/config/kernel/linux-sun60iw2-next-a733.config" \
   "$CFGDIR/kernel/"

# Kernel patch
echo "  Kernel patch → $PATCHDIR/kernel/sun60iw2-next/"
mkdir -p "$PATCHDIR/kernel/sun60iw2-next"
cp "$OVERLAY_DIR/patch/kernel/sun60iw2-next/opi4pro-7.1.5.patch" \
   "$PATCHDIR/kernel/sun60iw2-next/"

# Firmware (new layout only — legacy uses cache/)
if [[ "$LAYOUT" == "flat" ]]; then
    echo "  Firmware → packages/firmware/"
    mkdir -p "$ARMBIAN_DIR/packages/firmware"
    cp -r "$OVERLAY_DIR/firmware/"* \
       "$ARMBIAN_DIR/packages/firmware/"
else
    echo "  Firmware → external/cache/sources/firmware/"
    mkdir -p "$ARMBIAN_DIR/external/cache/sources/firmware"
    cp -r "$OVERLAY_DIR/firmware/"* \
       "$ARMBIAN_DIR/external/cache/sources/firmware/"
fi

# 12GB DRAM fix files: prebuilt boot blobs + patched sys_config
# (DRAM config transplanted from Radxa Cubie A7A, ADC auto-select disabled)
# NOTE: the 12GB boot0 blobs are stored as base64 chunks (*.b64.part*)
# because the GitHub API push path rejects raw binaries; reassemble here.
echo "  12GB boot blobs → packages/blobs/sunxi/sun60iw2/"
mkdir -p "$ARMBIAN_DIR/packages/blobs/sunxi/sun60iw2"
cp "$OVERLAY_DIR/packages/blobs/sunxi/sun60iw2/"* \
   "$ARMBIAN_DIR/packages/blobs/sunxi/sun60iw2/"
for blob in boot0_sdcard_orangepi4pro_12gb boot0_spinor_orangepi4pro_12gb; do
    out="$ARMBIAN_DIR/packages/blobs/sunxi/sun60iw2/$blob.fex"
    if [[ ! -f "$out" ]]; then
        shopt -s nullglob
        parts=( "$OVERLAY_DIR/packages/blobs/sunxi/sun60iw2/$blob.fex.b64.part"* )
        shopt -u nullglob
        if (( ${#parts[@]} > 0 )); then
            cat "${parts[@]}" | base64 -d > "$out"
            echo "  reassembled $blob.fex from ${#parts[@]} chunks"
        else
            echo "  WARNING: $blob.fex missing and no chunks found" >&2
        fi
    fi
done

echo ""
echo "Overlay applied. Build with:"
echo "  cd $ARMBIAN_DIR"
echo "  sudo ./compile.sh BOARD=orangepi4pro BRANCH=next RELEASE=bookworm BUILD_DESKTOP=no BUILD_OPT=image"
