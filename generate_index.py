import os
import json
import re
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON = os.path.join(BASE_DIR, "master_registry.json")
GH_REPO = "MidoN37/daily-scraper-krok"

def clean_title(text):
    text = re.sub(r'(Krok|Крок)\s*([123])', r'КРОК \2', text, flags=re.IGNORECASE)
    words = text.split()
    final = []
    for w in words:
        if not final or w.lower() != final[-1].lower(): final.append(w)
    return ' '.join(final).strip()

def get_type(filename):
    booklet_keywords = ["усі буклети", "all booklets", "все буклеты", "merged", "live"]
    return "booklet" if any(k in filename.lower() for k in booklet_keywords) else "base"

def get_master_list():
    master_list = []

    # 1. Fetch Live Data from GitHub (База з ЦТ)
    print("🌐 Fetching Live Data from GitHub...")
    try:
        res = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/Merged/PDF")
        if res.status_code == 200:
            for f in res.json():
                if not f['name'].lower().endswith(".pdf"): continue
                name = f['name'].replace(".pdf", "")
                exam_type = "Krok English" if "(EN)" in name.upper() else "Крок Українська"
                if "ЄДКІ" in name: exam_type = "ЄДКІ"
                if "АМПС" in name: exam_type = "АМПС"
                
                level = "Інше"
                if "КРОК 1" in name.upper(): level = "КРОК 1"
                elif "КРОК 2" in name.upper(): level = "КРОК 2"
                elif "КРОК 3" in name.upper(): level = "КРОК 3"
                elif "Бакалаври" in name: level = "ЄДКІ Бакалаври"
                elif "Фахова" in name: level = "ЄДКІ Фахова передвища освіта"

                master_list.append({
                    "name": clean_title(name), "source": "База з ЦТ", "path": f['download_url'],
                    "exam_type": exam_type, "level": level, "subject": "Нові тести", "type": "booklet"
                })
    except Exception as e:
        print(f"Error fetching GitHub data: {e}")

    # 2. Index local folders (Звичайні Базі & Старше ЦТ)
    local_sources = ["Звичайні Базі", "Старше ЦТ"]
    for source_name in local_sources:
        root_path = os.path.join(BASE_DIR, source_name)
        if not os.path.exists(root_path): continue
        
        for root, dirs, files in os.walk(root_path):
            for f in files:
                if f.lower().endswith(".pdf"):
                    rel_path = os.path.relpath(os.path.join(root, f), BASE_DIR)
                    parts = rel_path.split(os.sep)
                    
                    if source_name == "Звичайні Базі" and "PDF Merged" in root:
                        # [Звичайні Базі, Lang, PDF Merged, Level, Subject, file]
                        lang = "Krok English" if parts[1] == "English" else ("Московська" if parts[1] == "Московська" else "Крок Українська")
                        level = clean_title(parts[3])
                        subject = parts[4]
                        exam_type = "ЄДКІ" if "ЄДКІ" in level else lang
                        
                        master_list.append({
                            "name": clean_title(f"{level} {subject} - {f.replace('.pdf', '')}"),
                            "source": source_name, "path": rel_path,
                            "exam_type": exam_type, "level": level, "subject": subject, "type": get_type(f)
                        })

                    elif source_name == "Старше ЦТ" and (root.lower().endswith(os.sep + "pdf") or "єдкі" in root.lower()):
                         # Standardized logic for Older database
                        rel = os.path.relpath(os.path.join(root, f), BASE_DIR)
                        p = rel.split(os.sep)
                        if p[1].lower() == "єдкі":
                            level = clean_title(p[2])
                            subject = p[3]
                            exam_type = "ЄДКІ"
                        else:
                            level = clean_title(p[1])
                            subject = p[2]
                            exam_type = "Крок Українська"

                        master_list.append({
                            "name": clean_title(f"{level} {subject}"),
                            "source": source_name, "path": rel,
                            "exam_type": exam_type, "level": level, "subject": subject, "type": "booklet"
                        })

    return master_list

if __name__ == "__main__":
    data = get_master_list()
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Build Complete: Indexed {len(data)} files.")