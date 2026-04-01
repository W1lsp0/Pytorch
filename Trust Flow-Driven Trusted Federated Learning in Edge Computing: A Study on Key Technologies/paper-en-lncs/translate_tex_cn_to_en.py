#!/usr/bin/env python3
import re
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator

if len(sys.argv) != 3:
    print("Usage: translate_tex_cn_to_en.py <input.tex> <output.tex>")
    sys.exit(1)

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text(encoding="utf-8")

translator = GoogleTranslator(source="zh-CN", target="en")
cache = {}

# Match contiguous Chinese text fragments (including common Chinese punctuation/spaces)
chunk_pattern = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fff0-9A-Za-z，。！？；：、“”‘’（）《》【】、\s\-—…·,.:%/]{0,5000}")
char_pattern = re.compile(r"[\u4e00-\u9fff]+")


def tr(s: str) -> str:
    key = s.strip()
    if not key:
        return s
    if key in cache:
        out = cache[key]
    else:
        last_err = None
        out = key
        for _ in range(4):
            try:
                out = translator.translate(key)
                break
            except Exception as e:
                last_err = e
                time.sleep(0.8)
        else:
            out = key
        cache[key] = out
        time.sleep(0.12)

    # Preserve leading/trailing spaces in original fragment
    lead = len(s) - len(s.lstrip())
    trail = len(s) - len(s.rstrip())
    return (" " * lead) + out + (" " * trail)


def replace_fragments(line: str) -> str:
    if line.lstrip().startswith("%"):
        return line

    # First pass: larger contiguous fragments
    line = chunk_pattern.sub(lambda m: tr(m.group(0)), line)
    # Second pass: any remaining CJK words
    line = char_pattern.sub(lambda m: tr(m.group(0)), line)
    return line

translated_lines = [replace_fragments(ln) for ln in text.splitlines(keepends=True)]
dst.write_text("".join(translated_lines), encoding="utf-8")
print(f"Wrote: {dst}")
