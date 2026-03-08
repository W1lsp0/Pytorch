import re

log_content = open('log/server.log', 'r').read()

# Find the Round 23 block
block = log_content.split('🛡️  [TMAA Server] 第 23 轮 | 审计阶段开始...')[1].split('🛡️  [TMAA Server] 第 24 轮')[0]

# Extract [DEBUG SIM] CID: ... | cos_root: ...
cid_to_cos = {}
for line in block.split('\n'):
    if '[DEBUG SIM]' in line:
        m = re.search(r'CID: ([0-9a-f]+) \|.*cos_root: ([\-\.\d]+)', line)
        if m:
            cid_to_cos[m.group(1)] = float(m.group(2))

print("DEBUG SIM CID to cos_root:")
print(cid_to_cos)

# How to map CID to Client ID?
# We can't directly map them from this block unless we have earlier logs. 
