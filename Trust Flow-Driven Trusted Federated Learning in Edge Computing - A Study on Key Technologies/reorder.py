import re
import sys

tex_file = 'main.tex'

try:
    with open(tex_file, 'r', encoding='utf-8') as f:
        text = f.read()
except Exception as e:
    print(f"Error reading {tex_file}: {e}")
    sys.exit(1)

# 1. Find \begin{thebibliography} and \end{thebibliography}
bib_start_match = re.search(r'\\begin\{thebibliography\}\{.*?\}', text)
bib_end_match = re.search(r'\\end\{thebibliography\}', text)

if not bib_start_match or not bib_end_match:
    print("Could not find thebibliography block.")
    sys.exit(1)

text_before = text[:bib_start_match.start()]
bib_block = text[bib_start_match.start():bib_end_match.end()]
text_after = text[bib_end_match.end():]

# 2. Extract citations in order they appear
lines = text_before.split('\n')
clean_lines = [re.sub(r'(?<!\\)%.*$', '', line) for line in lines]
clean_text = '\n'.join(clean_lines)

ordered_keys = []
for match in re.finditer(r'\\cite\{([^}]+)\}', clean_text):
    keys = match.group(1).split(',')
    for k in keys:
        k = k.strip()
        if k and k not in ordered_keys:
            ordered_keys.append(k)

# 3. Parse bibitems from the block
bib_header = bib_block[:bib_block.find('}') + 1]
bib_inner = bib_block[bib_block.find('}') + 1 : bib_block.rfind('\\end{thebibliography}')]

# Strip leading structural newlines from inner to header
while bib_inner.startswith('\n'):
    bib_header += '\n'
    bib_inner = bib_inner[1:]

parts = re.split(r'(\\bibitem\{.*?\})', bib_inner)

bib_items = {}
# parts[0] is everything before first \bibitem, add to header
bib_header += parts[0]

for i in range(1, len(parts), 2):
    tag = parts[i]
    content = parts[i+1]
    
    key_match = re.search(r'\\bibitem\{([^}]+)\}', tag)
    if key_match:
        key = key_match.group(1).strip()
        bib_items[key] = tag + content

# 4. Generate new bib block
new_bib = bib_header
added = set()

for k in ordered_keys:
    if k in bib_items:
        new_bib += bib_items[k]
        added.add(k)
    else:
        print(f"Warning: {k} is cited but missing from bibliography.")

for k, content in bib_items.items():
    if k not in added:
        new_bib += content
        added.add(k)
        print(f"Note: {k} was not cited but is in bibliography.")

new_bib += '\\end{thebibliography}'

# 5. Write back to file
new_text = text_before + new_bib + text_after
with open(tex_file, 'w', encoding='utf-8') as f:
    f.write(new_text)

print(f"Sorted {len(ordered_keys)} citations.")
