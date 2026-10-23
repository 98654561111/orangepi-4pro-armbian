#!/usr/bin/env python3
"""Repack Orange Pi 4 Pro boot0 blobs with the tested 12GB DRAM config.

Usage: repack-boot0-12gb.py <pack-uboot-tools-dir> <blob-dir>

Inputs (in <blob-dir>):
  boot0_sdcard_orangepi4pro.fex      stock sdcard boot0 blob
  boot0_spinor_orangepi4pro.fex      stock spinor boot0 blob
  sys_config_orangepi4pro_12gb.fex   patched sys_config (12GB manual DRAM,
                                     select_mode=0; LF or CRLF ok)

Outputs (in <blob-dir>):
  boot0_sdcard_orangepi4pro_12gb.fex
  boot0_spinor_orangepi4pro_12gb.fex

Method:
  - sdcard: Allwinner's update_boot0 (3rd arg ignored; updates in place).
  - spinor: update_boot0 rejects its layout, so the same 11 word changes
    are applied manually + additive checksum fix (verified equivalent).
  - both outputs are verified: 32 DRAM fields == Radxa Cubie A7A 12GB
    values and select_mode == 0.
"""
import os
import struct
import subprocess
import sys

# Expected 12GB DRAM struct (Radxa Cubie A7A [dram_para3]), field order as
# stored in the boot0 dram para struct.
EXPECTED = [
    1800, 9, 0x0E0E0E0E, 0x0F0F0F0F, 0xEC030E0F, 0,
    0xA11A, 0x1001,
    0, 0, 0, 0x6, 0, 0, 0,
    0x12, 0x44, 0, 0x34, 0, 0x86, 0,
    0x4040, 0, 0x11080503, 0x3800, 0x3514,
    0xB25F0000, 0, 0, 0x10065, 0,
]
# (offset, old_value, new_value) for the spinor manual patch.
SPINOR_CHANGES = {
    0x50: (0xA0FA, 0xA11A),
    0x74: (0x13, 0x12),
    0x80: (0x2E, 0x34),
    0x88: (0x6, 0x86),
    0x98: (0x170B0703, 0x11080503),
    0xA4: (0x325F0000, 0xB25F0000),
    0xB0: (0x61, 0x10065),
    0xBC: (0x1030002, 0x1020902),
    0xC4: (0x1030102, 0x1020A02),
    0xCC: (0x0, 0x1),
    0x350: (0x102, 0x100),  # select_mode 2 -> 0 (low byte)
}
SELECT_MODE_OFF = 0x350


def verify(path):
    d = open(path, "rb").read()
    i = d.find(struct.pack("<II", 0xA11A, 0x1001))
    if i < 0:
        raise SystemExit(f"{path}: 12GB dram struct not found")
    vals = struct.unpack_from("<%dI" % len(EXPECTED), d, i - 24)
    if list(vals) != EXPECTED:
        bad = [(n, hex(v), hex(e)) for n, v, e in
               zip(range(len(EXPECTED)), vals, EXPECTED) if v != e]
        raise SystemExit(f"{path}: DRAM mismatch: {bad}")
    sm = struct.unpack_from("<I", d, SELECT_MODE_OFF)[0]
    if sm & 0xFF != 0:
        raise SystemExit(f"{path}: select_mode not 0 (word={hex(sm)})")
    print(f"{path}: 12GB DRAM verified, select_mode=0")


def main():
    tools, blob = sys.argv[1], sys.argv[2]
    sd = os.path.join(blob, "boot0_sdcard_orangepi4pro.fex")
    sp = os.path.join(blob, "boot0_spinor_orangepi4pro.fex")
    fex = os.path.join(blob, "sys_config_orangepi4pro_12gb.fex")
    sd12 = os.path.join(blob, "boot0_sdcard_orangepi4pro_12gb.fex")
    sp12 = os.path.join(blob, "boot0_spinor_orangepi4pro_12gb.fex")
    bin12 = os.path.join(blob, "sys_config_orangepi4pro_12gb.bin")

    # CRLF for Allwinner tools (work on a copy; keep tree file as-is).
    with open(fex, "rb") as f:
        raw = f.read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    tmpfex = os.path.join(blob, "_repack_tmp.fex")
    with open(tmpfex, "wb") as f:
        f.write(raw)
    # NOTE: these Allwinner tools misbehave with absolute paths
    # (update_boot0 silently skips select_mode); always use cwd=blob
    # and relative file names.
    subprocess.run(["script", "_repack_tmp.fex"],
                   cwd=blob, check=True, stdout=subprocess.DEVNULL,
                   env={**os.environ, "PATH": tools + os.pathsep +
                        os.environ.get("PATH", "")})
    os.rename(os.path.join(blob, "_repack_tmp.bin"), bin12)
    os.remove(tmpfex)

    # sdcard via Allwinner update_boot0 (updates arg1 in place; needs 3 args).
    with open(sd, "rb") as f:
        data = f.read()
    with open(sd12, "wb") as f:
        f.write(data)
    subprocess.run(
        ["update_boot0", os.path.basename(sd12),
         os.path.basename(bin12), "_"],
        cwd=blob, check=True, stdout=subprocess.DEVNULL,
        env={**os.environ, "PATH": tools + os.pathsep +
             os.environ.get("PATH", "")})
    verify(sd12)

    # spinor: manual patch (update_boot0 rejects this layout).
    with open(sp, "rb") as f:
        d = bytearray(f.read())
    for off, (old, new) in SPINOR_CHANGES.items():
        cur = struct.unpack_from("<I", d, off)[0]
        if cur != old:
            raise SystemExit(
                f"spinor blob unexpected value at {hex(off)}: "
                f"{hex(cur)} != expected {hex(old)}")
        struct.pack_into("<I", d, off, new)
    delta = sum(n - o for o, n in SPINOR_CHANGES.values()) & 0xFFFFFFFF
    ck = struct.unpack_from("<I", d, 0xC)[0]
    struct.pack_into("<I", d, 0xC, (ck + delta) & 0xFFFFFFFF)
    with open(sp12, "wb") as f:
        f.write(d)
    verify(sp12)
    print("12GB boot0 repack complete")


if __name__ == "__main__":
    main()
