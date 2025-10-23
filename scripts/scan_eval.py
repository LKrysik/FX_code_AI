import os, re

base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
roots = [
    os.path.join(base, 'frontend'),
    os.path.join(base, 'frontend', 'node_modules'),
]
patterns = {
    'eval(': re.compile(r'\beval\s*\('),
    'new Function(': re.compile(r'new\s+Function\s*\('),
    'setTimeout-string': re.compile(r'setTimeout\s*\(\s*[\'\"`]'),
    'setInterval-string': re.compile(r'setInterval\s*\(\s*[\'\"`]'),
}

hits = []
max_hits = 100
for root in roots:
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(('.ts', '.tsx', '.js')):
                continue
            path = os.path.join(dirpath, fn)
            try:
                # Skip very large files (>1MB)
                if os.path.getsize(path) > 1_000_000:
                    continue
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    s = f.read()
            except (OSError, IOError, UnicodeDecodeError) as e:
                print(f"Warning: Could not read file {path}: {e}")
                continue
            except Exception as e:
                print(f"Error: Unexpected error reading file {path}: {e}")
                continue
            for name, rx in patterns.items():
                if rx.search(s):
                    rel = os.path.relpath(path, base).replace('\\\\','/')
                    hits.append((rel, name))
                    break
            if len(hits) >= max_hits:
                break
        if len(hits) >= max_hits:
            break
    if len(hits) >= max_hits:
        break

for p, k in hits:
    print(f"{k}: {p}")
