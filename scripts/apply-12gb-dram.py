#!/usr/bin/env python3
"""Force 12GB manual DRAM init in an Allwinner sys_config.fex.

- Replaces the [dram_para] section with the tested 12GB LPDDR5 block
  (from Radxa Cubie A7A, configs/cubie_a7a/sys_config.fex [dram_para3]).
- Sets select_mode = 0 in [dram_select_para] (disable GPADC/GPIO
  auto DRAM profile selection, init 12GB manually).

Usage: apply-12gb-dram.py <sys_config.fex> <dram-12gb-para.fex>
Edits the fex file in place. Idempotent.
"""
import re
import sys


def replace_section(text: str, name: str, new_body: str) -> str:
    # Match "[name]" ... up to (not including) the next section header or EOF.
    pat = re.compile(
        r"(?m)^\[" + re.escape(name) + r"\][^\n]*\n(.*?)(?=^\[|\Z)", re.DOTALL
    )
    m = pat.search(text)
    if not m:
        raise SystemExit(f"section [{name}] not found in fex")
    return text[: m.start()] + f"[{name}]\n" + new_body + text[m.end():]


def main() -> None:
    fex_path, para_path = sys.argv[1], sys.argv[2]
    with open(fex_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    with open(para_path, encoding="utf-8") as f:
        para_block = f.read()
    # Strip the "[dram_para]" header line from the block file; we add our own.
    body = re.sub(r"(?m)^\[dram_para\][^\n]*\n", "", para_block, count=1)
    if not body.strip():
        raise SystemExit("dram para block is empty")
    if not body.endswith("\n"):
        body += "\n"

    text = replace_section(text, "dram_para", body)

    # Disable auto DRAM profile selection: select_mode = 0
    def fix_select(m: re.Match) -> str:
        header, sec_body = m.group(1), m.group(2)
        sec_body2, n = re.subn(
            r"(?m)^select_mode\s*=.*$", "select_mode\t= 0", sec_body
        )
        if n == 0:
            sec_body2 = "select_mode\t= 0\n" + sec_body
        return header + sec_body2

    text, n = re.subn(
        r"(?m)(^\[dram_select_para\][^\n]*\n)(.*?)(?=^\[|\Z)",
        fix_select,
        text,
        count=1,
        flags=re.DOTALL,
    )
    if n == 0:
        raise SystemExit("section [dram_select_para] not found in fex")

    with open(fex_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"patched {fex_path}: [dram_para]=12GB manual, select_mode=0")


if __name__ == "__main__":
    main()
