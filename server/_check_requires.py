"""临时校验：扫描 miniprogram 下所有 .js，确认每个 require 相对路径都能解析到真实文件。"""
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # bala-miniapp
ROOT = os.path.join(BASE, "miniprogram")

PATTERN = re.compile(r"require\(['\"](\.[^'\"]+)['\"]\)")

bad = 0
checked = 0
files_scanned = 0

for dirpath, dirnames, filenames in os.walk(ROOT):
    # 跳过 miniprogram 自带的 node_modules（如有）
    if "node_modules" in dirpath:
        continue
    for filename in filenames:
        if not filename.endswith(".js"):
            continue
        path = os.path.join(dirpath, filename)
        files_scanned += 1
        rel = os.path.relpath(path, BASE).replace(os.sep, "/")
        base = os.path.dirname(path)
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                match = PATTERN.search(line)
                if not match:
                    continue
                checked += 1
                target = os.path.normpath(os.path.join(base, match.group(1)))
                ok = os.path.isfile(target + ".js") or os.path.isfile(target)
                if not ok:
                    bad += 1
                    print(f"FAIL {rel}:{lineno} -> {match.group(1)}")

print()
print(f"扫描 {files_scanned} 个 js 文件，校验 {checked} 处 require，缺失 {bad} 处")
if bad == 0:
    print("全部路径正确")
