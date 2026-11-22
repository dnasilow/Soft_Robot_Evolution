import sys, re
from pypdf import PdfReader
path, out_path = sys.argv[1], sys.argv[2]
r = PdfReader(path)
out = []
for i, p in enumerate(r.pages):
    t = p.extract_text() or ""
    out.append(f"\n===== PAGE {i+1} =====\n{t}")
txt = re.sub(r'\n{3,}', '\n\n', "\n".join(out))
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(txt)
print(f"wrote {out_path}  ({len(r.pages)} pages, {len(txt)} chars)")
