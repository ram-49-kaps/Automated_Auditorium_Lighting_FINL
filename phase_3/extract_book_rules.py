
import os
import pypdf
import json
import re

from utils.openai_client import openai_json_array

BOOKS = {
    "McCandless": "docs/A_method_of_lighting_the_stage.pdf",
    "Shelley": "docs/A Practical Guide to Stage Lighting, Second Edition.pdf",
    "Reid": "docs/695451874-Francis-Reid-The-Stage-Lighting-Handbook-2002-Routledge-libgen-lc.pdf",
    "Pilbrow": "docs/980786233-Stage-Lighting-Design-Richard-Pilbrow.pdf",
    "Rosenthal": "docs/dokumen.pub_the-magic-of-light-second-printingnbsped-0316931209.pdf"
}

KEYWORDS = [
    "emotion", "mood", "feeling", "color", "intensity", "angle", 
    "key light", "fill light", "back light", "warm", "cool", 
    "sadness", "joy", "anger", "fear", "mystery", "romantic",
    "fresnel", "profile", "ellipsoidal", "parcan", "gobo"
]

def extract_text_from_pdf(filepath, limit_pages=50):
    """Extract text from the first N pages to catch core principles/introductions."""
    print(f"📖 Reading {filepath}...")
    try:
        reader = pypdf.PdfReader(filepath)
        text = ""
        # Read intro + select chapters if possible, but for now linear scan
        # Limit to avoid massive memory usage, focus on theory chapters often early on
        count = 0
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
            count += 1
            if count >= limit_pages:
                break
        return text
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return ""

def find_rules(text, source_name):
    """
    Extract lighting design rules from text.
    Tier 1: Ollama LLM extraction (understands context)
    Tier 2: Keyword-based sentence matching (original logic)
    Tier 3: Empty list
    """
    # Tier 1: Try Ollama for intelligent extraction
    if is_ollama_available():
        try:
            ollama_rules = _find_rules_ollama(text, source_name)
            if ollama_rules:
                print(f"  ✅ Ollama extracted {len(ollama_rules)} rules from {source_name}")
                return ollama_rules
        except Exception as e:
            print(f"  ⚠️ Ollama extraction failed: {e}")

    # Tier 2: Keyword-based fallback (original logic)
    return _find_rules_keyword(text, source_name)


def _find_rules_ollama(text, source_name):
    """Use Ollama to intelligently extract lighting rules from text."""
    # Process in chunks (Ollama has token limits)
    chunk_size = 3000
    all_rules = []

    for i in range(0, min(len(text), 15000), chunk_size):
        chunk = text[i:i + chunk_size]
        if len(chunk.strip()) < 50:
            continue

        result = ollama_json_array(
            prompt=(
                f"Extract lighting design rules from this text excerpt from '{source_name}'.\n\n"
                f"Focus on rules that relate:\n"
                f"- Emotions/moods to colors or color temperatures\n"
                f"- Emotions/moods to light intensity levels\n"
                f"- Emotions/moods to lighting angles or positions\n"
                f"- Scene types to lighting techniques\n\n"
                f"TEXT:\n{chunk}\n\n"
                f'Return a JSON array: [{{"rule": "description of the rule", '
                f'"source": "{source_name}", "category": "color|intensity|angle|technique"}}]'
            ),
            system_prompt=(
                "You are a lighting design expert extracting rules from textbooks. "
                "Output ONLY a JSON array of rule objects. "
                "If no lighting rules are found, return an empty array []."
            ),
        )

        if result:
            all_rules.extend(result)

    return all_rules if all_rules else None


def _find_rules_keyword(text, source_name):
    """Keyword-based rule extraction (original logic — Tier 2 fallback)."""
    rules = []
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    
    for sentence in sentences:
        sentence = sentence.strip().replace('\n', ' ')
        if len(sentence) < 20 or len(sentence) > 300:
            continue
            
        # Check if sentence contains meaningful keywords
        found_keywords = [k for k in KEYWORDS if k in sentence.lower()]
        if found_keywords:
            rules.append({
                "source": source_name,
                "keywords": found_keywords,
                "exemplar_text": sentence
            })
            
    return rules

def main():
    all_rules = []
    
    for author, path in BOOKS.items():
        if os.path.exists(path):
            full_text = extract_text_from_pdf(path, limit_pages=100) # Deep scan 100 pages
            extracted = find_rules(full_text, author)
            print(f"✅ Found {len(extracted)} potential rules in {author}")
            all_rules.extend(extracted)
        else:
            print(f"⚠️ File not found: {path}")

    # Save raw extraction
    with open("phase_3/knowledge/semantics/raw_book_extraction.json", "w") as f:
        json.dump(all_rules, f, indent=2)
    
    print("\n🔍 Extraction Complete. Saved to phase_3/knowledge/semantics/raw_book_extraction.json")

if __name__ == "__main__":
    main()
