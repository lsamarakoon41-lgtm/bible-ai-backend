from flask import Flask, request, jsonify
import json
import re
import os
import time
import logging
from collections import Counter
from functools import lru_cache

app = Flask(__name__)

# -------------------------------------------------
# LOGGING
# -------------------------------------------------

logging.basicConfig(level=logging.INFO)
logging.info("Starting Bible AI - Master Authority System")

# -------------------------------------------------
# LOAD BIBLE
# -------------------------------------------------

with open("kjv.json", "r", encoding="utf-8") as f:
    bible_data = json.load(f)

bible_lookup = {ref.lower(): {"reference": ref, "text": text}
                for ref, text in bible_data.items()}

bible_list = list(bible_lookup.values())

logging.info(f"Bible Loaded: {len(bible_list)} verses")

# -------------------------------------------------
# LOAD KNOWLEDGE
# -------------------------------------------------

KNOWLEDGE_FOLDER = "knowledge"

def load_json(filename):
    path = os.path.join(KNOWLEDGE_FOLDER, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

if not os.path.exists(KNOWLEDGE_FOLDER):
    os.makedirs(KNOWLEDGE_FOLDER)

# Core Doctrine (PRIORITY)
doctrine_core = load_json("doctrine_core.json")

# Secondary Knowledge
jesus_life_data = load_json("jesus_life.json")
early_church_data = load_json("early_church.json")
historical_context_data = load_json("historical_context.json")

logging.info("Knowledge Loaded")

# -------------------------------------------------
# LOAD BRAIN (LOWEST AUTHORITY)
# -------------------------------------------------

BRAIN_FOLDER = "brain"
brain_data = []
brain_last_loaded = 0
BRAIN_REFRESH_INTERVAL = 60

def load_brain():
    global brain_last_loaded
    data = []

    if not os.path.exists(BRAIN_FOLDER):
        os.makedirs(BRAIN_FOLDER)

    for file in os.listdir(BRAIN_FOLDER):
        if file.endswith((".txt", ".md")):
            with open(os.path.join(BRAIN_FOLDER, file), "r", encoding="utf-8") as f:
                content = f.read()
                paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
                for p in paragraphs:
                    data.append({
                        "source": file,
                        "content": p,
                        "lower": p.lower(),
                        "freq": Counter(re.findall(r"\b[a-zA-Z]+\b", p.lower()))
                    })

    brain_last_loaded = time.time()
    logging.info(f"Brain Loaded: {len(data)} segments")
    return data

brain_data = load_brain()

def auto_refresh_brain():
    global brain_data
    if time.time() - brain_last_loaded > BRAIN_REFRESH_INTERVAL:
        brain_data = load_brain()

@lru_cache(maxsize=200)
def search_brain(question):
    auto_refresh_brain()
    words = re.findall(r"\b[a-zA-Z]+\b", question.lower())
    words = [w for w in words if len(w) > 4]

    results = []

    for item in brain_data:
        score = sum(item["freq"].get(w, 0) for w in words)
        if score > 0:
            results.append({"source": item["source"], "content": item["content"], "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]

# -------------------------------------------------
# SCRIPTURE EXPLAINS SCRIPTURE
# -------------------------------------------------

def cross_reference(main_verse, limit=5):
    words = re.findall(r"\b[a-zA-Z]+\b", main_verse["text"].lower())
    words = [w for w in words if len(w) > 4]

    results = []

    for verse in bible_list:
        if verse["reference"] == main_verse["reference"]:
            continue

        score = sum(1 for w in words if w in verse["text"].lower())
        if score > 0:
            results.append({"reference": verse["reference"], "text": verse["text"], "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)

    return [{"reference": r["reference"], "text": r["text"]} for r in results[:limit]]

# -------------------------------------------------
# DOCTRINE SEARCH (PRIORITY)
# -------------------------------------------------

def search_doctrine(question):
    q = question.lower()
    for entry in doctrine_core:
        if entry.get("category", "").lower() in q or entry.get("title", "").lower() in q:
            return entry
    return None

def build_mode_c(entry):
    verses = []
    for ref in entry.get("core_verses", []):
        verse = bible_lookup.get(ref.lower())
        if verse:
            verses.append(verse)

    return {
        "type": "doctrine",
        "category": entry.get("category"),
        "title": entry.get("title"),
        "verses": verses,
        "explanation": entry.get("explanation"),
        "logical_reasoning": entry.get("logical_reasoning"),
        "defense_section": entry.get("defense_response")
    }

# -------------------------------------------------
# ROUTES
# -------------------------------------------------

@app.route("/")
def home():
    return jsonify({"status": "Bible AI Master System Running"})

@app.route("/ask", methods=["GET", "POST"])
def ask():
    try:
        question = ""

        if request.method == "GET":
            question = request.args.get("question", "")
        else:
            data = request.get_json(silent=True)
            question = data.get("question", "") if data else ""

        question = question.strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        logging.info(f"Question: {question}")

        # -------------------------------------------------
        # 1️⃣ DIRECT VERSE (HIGHEST AUTHORITY)
        # -------------------------------------------------

        ref_pattern = r"([1-3]?\s?[A-Za-z]+\s\d+:\d+)"
        match = re.findall(ref_pattern, question)

        if match:
            ref = match[0].strip().lower()
            verse = bible_lookup.get(ref)

            if verse:
                return jsonify({
                    "type": "scripture",
                    "main_verse": verse,
                    "cross_references": cross_reference(verse)
                })

        # -------------------------------------------------
        # 2️⃣ DOCTRINE CORE (PRIORITY OVER EVERYTHING)
        # -------------------------------------------------

        doctrine_entry = search_doctrine(question)
        if doctrine_entry:
            return jsonify(build_mode_c(doctrine_entry))

        # -------------------------------------------------
        # 3️⃣ SECONDARY KNOWLEDGE
        # -------------------------------------------------

        all_secondary = jesus_life_data + early_church_data + historical_context_data

        for item in all_secondary:
            if item.get("title", "").lower() in question.lower():
                return jsonify({"type": "knowledge", "content": item})

        # -------------------------------------------------
        # 4️⃣ BRAIN (SUPPLEMENT ONLY)
        # -------------------------------------------------

        brain_results = search_brain(question)
        if brain_results:
            return jsonify({"type": "brain_supplement", "results": brain_results})

        # -------------------------------------------------
        # 5️⃣ KEYWORD FALLBACK
        # -------------------------------------------------

        words = re.findall(r"\b[a-zA-Z]+\b", question.lower())
        words = [w for w in words if len(w) > 4]

        results = []

        for verse in bible_list:
            score = sum(1 for w in words if w in verse["text"].lower())
            if score > 0:
                results.append({"reference": verse["reference"], "text": verse["text"], "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)

        return jsonify({
            "type": "scripture_search",
            "results": [{"reference": r["reference"], "text": r["text"]} for r in results[:5]]
        })

    except Exception as e:
        logging.error(str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)