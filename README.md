# Orange Pi 4 Pro — Armbian Build Overlay (12GB Edition)

[![Build](https://github.com/98654561111/orangepi-4pro-armbian/actions/workflows/release.yml/badge.svg)](https://github.com/98654561111/orangepi-4pro-armbian/actions/workflows/release.yml)

Build Armbian images for the **Orange Pi 4 Pro** — including the **12GB RAM variant** — with mainline Linux kernel on Allwinner A733 (sun60iw2).

Forked from [jonas5/orangepi-4pro-armbian](https://github.com/jonas5/orangepi-4pro-armbian).

## 12GB RAM Fix

The upstream overlay only boots the 2/4/8/16GB variants. The 12GB model hangs during boot0 DRAM initialization: the BSP enables ADC auto DRAM-profile selection, but no 12GB profile exists.

This fork fixes it:

- DRAM timings transplanted from the **Radxa Cubie A7A** FEX (`dram_para3`: 12GB LPDDR5 @ 1800MHz). Same A733 SoC; DDR parameters verified identical to the Orange Pi 4 Pro board.
- ADC/GPIO auto-select disabled (`select_mode=0`) — the 12GB config is used directly, no probing.
- Both boot0 blobs (SD card + SPI NOR) repacked with the fixed config.

To reproduce the repack from stock blobs:

```bash
python3 scripts/repack-boot0-12gb.py \
  <orangepi-build>/external/packages/pack-uboot/tools \
  <armbian-build>/packages/blobs/sunxi/sun60iw2
```

See `scripts/repack-boot0-12gb.py` and `scripts/apply-12gb-dram.py` for details. (The prebuilt blobs are stored as base64 chunks `*.b64.part*` because the GitHub API rejects raw binaries; `scripts/apply-overlay.sh` reassembles them at build time.)

## Hardware

| Component | Details |
|-----------|---------|
| SoC | Allwinner A733 — 2× Cortex-A76 + 6× Cortex-A55, Mali Bifrost GPU |
| RAM | 2/4/8/**12**/16 GB LPDDR4X/LPDDR5 (**12GB supported by this fork**) |
| Storage | eMMC (MMC2, 8-bit), microSD (MMC0), SPI NOR flash (16MB), NVMe (PCIe x1 Gen3) |
| Ethernet | Gigabit (GMAC0, RGMII, RTL8211F) |
| WiFi/BT | AIC8800D80 (SDIO + UART HCI) |
| USB | 1× USB3 Type-C (OTG), 2× USB2 Type-A (EHCI/OHCI) |
| PCIe | x1 Gen3 (RC mode, via combo PHY) |
| Display | MIPI DSI (800×1280, Goodix GT9271 touchscreen) |
| Audio | ES8388 codec (I2C @0x10 + I2S4), 3.5mm headphone jack |
| PMIC | AXP8191 (main DCDC/ALDO/BLDO/CLDO/DLDO/ELDO) + AXP515 (battery/charging) |
| Serial | UART0 debug (115200), UART1 BT HCI, UART2 expansion |
| LEDs | Green status LED (PI8) |

## Pre-built Images

No static releases — images are built on demand via GitHub Actions:

1. Open [Actions → Build and Upload Release Images](https://github.com/98654561111/orangepi-4pro-armbian/actions/workflows/release.yml)
2. Click **Run workflow**, pick a release (`noble` = Ubuntu 24.04 LTS, `trixie` = Debian 13, …)
3. When the run finishes, download the artifact (e.g. `Orangepi4pro-noble-desktop`, `.img.xz` inside)

All images target the 12GB board and use the mainline kernel. Flash to SD card with `dd`, [balenaEtcher](https://etcher.balena.io/), or Raspberry Pi Imager.

## Building Your Own Image

### Prerequisites

- x86_64 or arm64 Linux host (Debian/Ubuntu recommended)
- ~25 GB free disk space (more for desktop builds)
- Internet connection

Install dependencies:

```bash
sudo apt-get update
sudo apt-get install -y git gcc make bc bison flex libssl-dev \
    libc6-dev-arm64-cross gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
    qemu-user-static binfmt-support dpkg-dev
# For U-Boot x86-64 toolchain emulation:
sudo dpkg --add-architecture amd64
sudo apt-get update
sudo apt-get install -y libc6:amd64
```

Enable binfmt (allows running x86-64 U-Boot tools on arm64 hosts):

```bash
sudo systemctl restart systemd-binfmt
```

### Step 1: Clone Armbian Build System

```bash
git clone --depth=1 https://github.com/armbian/build.git armbian-build
cd armbian-build
```

### Step 2: Clone This Overlay

```bash
git clone https://github.com/98654561111/orangepi-4pro-armbian.git orangepi4pro-overlay
```

### Step 3: Apply the Overlay

```bash
./orangepi4pro-overlay/scripts/apply-overlay.sh .
```

This copies the board config, kernel config/patch, firmware, and the 12GB boot blobs (reassembled from base64 chunks) into the Armbian tree.

### Step 4: Build

**Desktop image (Noble GNOME, 12GB):**

```bash
./compile.sh \
    BOARD=orangepi4pro \
    BRANCH=next \
    RELEASE=noble \
    BUILD_DESKTOP=yes \
    DESKTOP_ENVIRONMENT=gnome \
    DESKTOP_ENVIRONMENT_CONFIG_NAME=config_base \
    DESKTOP_APPGROUPS_SELECTED="browsers editors multimedia" \
    KERNEL_CONFIGURE=no \
    NO_HOST_RELEASE_CHECK=yes \
    COMPRESS_OUTPUTIMAGE=no \
    BUILD_OPT=image
```

**Server image (Noble, 12GB):**

```bash
./compile.sh \
    BOARD=orangepi4pro \
    BRANCH=next \
    RELEASE=noble \
    BUILD_DESKTOP=no \
    BUILD_MINIMAL=yes \
    KERNEL_CONFIGURE=no \
    NO_HOST_RELEASE_CHECK=yes \
    COMPRESS_OUTPUTIMAGE=no \
    BUILD_OPT=image
```

Images are written to `output/images/`.

### Build Options Reference

| Option | Description |
|--------|-------------|
| `BOARD=orangepi4pro` | Board name |
| `BRANCH=next` | Mainline kernel (`current` = vendor kernel) |
| `RELEASE=noble\|trixie\|bookworm\|plucky\|forky\|resolute` | Debian/Ubuntu release (`resolute` = Ubuntu 26.04) |
| `BUILD_DESKTOP=no\|yes` | Server or desktop image |
| `BUILD_MINIMAL=yes` | Minimal server image (smaller, fewer packages) |

## Repository Layout

| Path | Contents |
|------|----------|
| `config/boards/orangepi4pro.conf` | Board definition (points at 12GB boot blobs) |
| `config/bootloader/dram-12gb-para.fex` | 12GB DRAM config source |
| `packages/blobs/sunxi/sun60iw2/` | Boot0 blobs + patched sys_config (12GB blobs as `.b64.part*` chunks) |
| `scripts/apply-overlay.sh` | Applies overlay to Armbian tree (reassembles 12GB blobs) |
| `scripts/apply-12gb-dram.py` | Patches sys_config FEX with 12GB DRAM block |
| `scripts/repack-boot0-12gb.py` | Repacks stock boot0 blobs with 12GB config |
| `patch/kernel/sun60iw2-next/` | Kernel patches |
| `.github/workflows/release.yml` | CI: build images via workflow_dispatch |

## Credits

- Original overlay: [jonas5](https://github.com/jonas5) ([buy him a coffee](https://buymeacoffee.com/jonas5))
- 12GB DRAM fix: DRAM config from [Radxa Cubie A7A](https://github.com/radxa/allwinner-device) (`device-a733-v1.4.8`)
