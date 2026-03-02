from flask import Flask, request, jsonify
import json
import re
import os
import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# -------------------------------------------------
# LOGGING
# -------------------------------------------------

logging.basicConfig(level=logging.INFO)
logging.info("Starting Bible AI - Lightweight Production Mode")

# -------------------------------------------------
# LOAD BIBLE
# -------------------------------------------------

with open("kjv.json", "r", encoding="utf-8") as f:
    bible_data = json.load(f)

bible_lookup = {
    ref.lower(): {"reference": ref, "text": text}
    for ref, text in bible_data.items()
}

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

doctrine_core = load_json("doctrine_core.json")
jesus_life_data = load_json("jesus_life.json")
early_church_data = load_json("early_church.json")
historical_context_data = load_json("historical_context.json")

logging.info("Knowledge Loaded")

# -------------------------------------------------
# BUILD LIGHTWEIGHT SEMANTIC MEMORY (TF-IDF)
# -------------------------------------------------

SEMANTIC_DATA = []
TEXT_CORPUS = []

secondary = jesus_life_data + early_church_data + historical_context_data

for item in secondary:
    text = item.get("content") or item.get("text") or item.get("title")
    if text:
        SEMANTIC_DATA.append({
            "type": "knowledge",
            "data": item,
            "text": text
        })
        TEXT_CORPUS.append(text)

for entry in doctrine_core:
    combined_text = (
        entry.get("title", "") + " " +
        entry.get("explanation", "") + " " +
        entry.get("logical_reasoning", "")
    )

    SEMANTIC_DATA.append({
        "type": "doctrine",
        "data": entry,
        "text": combined_text
    })
    TEXT_CORPUS.append(combined_text)

if TEXT_CORPUS:
    vectorizer = TfidfVectorizer(stop_words="english")
    DOC_VECTORS = vectorizer.fit_transform(TEXT_CORPUS)
else:
    vectorizer = None
    DOC_VECTORS = None

logging.info(f"Semantic Memory Built: {len(SEMANTIC_DATA)} items")

# -------------------------------------------------
# SEMANTIC SEARCH
# -------------------------------------------------

def semantic_search(question, top_k=5):
    if not vectorizer or DOC_VECTORS is None:
        return []

    query_vector = vectorizer.transform([question])
    similarities = cosine_similarity(query_vector, DOC_VECTORS)[0]

    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if similarities[idx] > 0.15:
            results.append({
                "type": SEMANTIC_DATA[idx]["type"],
                "data": SEMANTIC_DATA[idx]["data"],
                "score": float(similarities[idx])
            })

    return results

# -------------------------------------------------
# SCRIPTURE CROSS-REFERENCE
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
            results.append({
                "reference": verse["reference"],
                "text": verse["text"],
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    return [
        {"reference": r["reference"], "text": r["text"]}
        for r in results[:limit]
    ]

# -------------------------------------------------
# ROUTES
# -------------------------------------------------

@app.route("/")
def home():
    return jsonify({"status": "Bible AI Running - Lightweight Mode"})

@app.route("/ask", methods=["GET", "POST"])
def ask():
    try:
        if request.method == "GET":
            question = request.args.get("question", "")
        else:
            data = request.get_json(silent=True)
            question = data.get("question", "") if data else ""

        question = question.strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        logging.info(f"Question: {question}")

        # 1️⃣ Direct verse reference
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

        # 2️⃣ Doctrine Priority
        semantic_results = semantic_search(question)

        doctrine_hits = [r for r in semantic_results if r["type"] == "doctrine"]
        knowledge_hits = [r for r in semantic_results if r["type"] == "knowledge"]

        if doctrine_hits:
            entry = doctrine_hits[0]["data"]

            verses = []
            for ref in entry.get("core_verses", []):
                verse = bible_lookup.get(ref.lower())
                if verse:
                    verses.append(verse)

            return jsonify({
                "type": "doctrine",
                "category": entry.get("category"),
                "title": entry.get("title"),
                "verses": verses,
                "explanation": entry.get("explanation"),
                "logical_reasoning": entry.get("logical_reasoning"),
                "defense_section": entry.get("defense_response")
            })

        if knowledge_hits:
            return jsonify({
                "type": "knowledge",
                "results": [k["data"] for k in knowledge_hits[:3]]
            })

        # 3️⃣ Scripture fallback search
        words = re.findall(r"\b[a-zA-Z]+\b", question.lower())
        words = [w for w in words if len(w) > 4]

        results = []

        for verse in bible_list:
            score = sum(1 for w in words if w in verse["text"].lower())
            if score > 0:
                results.append({
                    "reference": verse["reference"],
                    "text": verse["text"],
                    "score": score
                })

        results.sort(key=lambda x: x["score"], reverse=True)

        return jsonify({
            "type": "scripture_search",
            "results": [
                {"reference": r["reference"], "text": r["text"]}
                for r in results[:5]
            ]
        })

    except Exception as e:
        logging.error(str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)