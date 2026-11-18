import os
import sys
import time
from pathlib import Path

sys.path.insert(0, '/work')
from rusit.translator import RusitTranslator

src_root = Path('/work/books')
dst_root = Path('/work/books_rusit')

def translate_file(translator, src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.read().splitlines()
    out_lines = []
    for i, line in enumerate(lines):
        if not line.strip():
            out_lines.append('')
        else:
            try:
                out_lines.append(translator.translate(line, preserve_punctuation=True))
            except Exception as e:
                out_lines.append(f'[ERROR: {e}] {line}')
    with open(dst, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
        if lines:
            f.write('\n')
    return len(lines)

def main():
    translator = RusitTranslator()
    files = sorted(src_root.rglob('*.txt'))
    total = len(files)
    start = time.time()
    for idx, src in enumerate(files, 1):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        t0 = time.time()
        n = translate_file(translator, src, dst)
        dt = time.time() - t0
        print(f'[{idx}/{total}] {rel} ({n} lines, {dt:.1f}s)', flush=True)
    print(f'Done in {time.time()-start:.1f}s', flush=True)

if __name__ == '__main__':
    main()
