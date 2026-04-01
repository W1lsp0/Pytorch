import re
import os
from PyPDF2 import PdfReader

def check_github_links(pdf_path):
    print(f"\n========== Scanning {os.path.basename(pdf_path)} ==========")
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for p in reader.pages:
            extracted = p.extract_text()
            if extracted: text += extracted + "\n"
        
        # Searching for github URLs or 'source code'
        github_links = re.findall(r'github\.com[/\w\-]*', text, re.IGNORECASE)
        code_mentions = re.findall(r'source code is available|code availability', text, re.IGNORECASE)
        
        if github_links:
            print(f"-> Found GitHub Links: {set(github_links)}")
        else:
            print("-> ❌ No GitHub links found.")
            
        if code_mentions:
            print(f"-> Found code availability mentions: {set(code_mentions)}")
        else:
            print("-> ❌ No distinct 'source code available' statement found.")
            
    except Exception as e:
        print(f"Error: {e}")

papers = [
    '../Paper/11. RPPFL Robust and Privacy-Preserving Federated Learning via Trusted Execution Environments.pdf',
    '../Paper/4. TMT-FL Enabling Trustworthy Model Training of Federated Learning With Malicious Participants.pdf'
]

for p in papers:
    check_github_links(p)
