import json
import re

for cid in [1, 2, 4, 13]:
    fname = f"log/client_{cid}.log"
    try:
        with open(fname, "r") as f:
            content = f.read()
            # find JSON string
            match = re.search(r"trust_report_json':\s*'(.*?)'\}", content)
            if match:
                jstr = match.group(1)
                data = json.loads(jstr)
                sep = data.get("metrics", {}).get("data_health_audit", {}).get("cluster_quality", {}).get("separability_ratio", "N/A")
                print(f"Client {cid} separability_ratio: {sep}")
    except Exception as e:
        print(f"Client {cid} err {e}")
