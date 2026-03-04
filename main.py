from flask import Flask, request, jsonify
import json
import re
import os
import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logging.info("Starting Bible AI - Production Mode")

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
SEMANTIC_DATA = []
TEXT_CORPUS = []

if os.path.exists(KNOWLEDGE_FOLDER):
    for filename in os.listdir(KNOWLEDGE_FOLDER):
        if filename.endswith(".json"):
            path = os.path.join(KNOWLEDGE_FOLDER, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    if isinstance(data, list):
                        for entry in data:

                            if "core_verses" in entry:
                                combined = (
                                    entry.get("title", "") + " " +
                                    entry.get("explanation", "") + " " +
                                    entry.get("logical_reasoning", "")
                                )

                                SEMANTIC_DATA.append({
                                    "type": "doctrine",
                                    "data": entry,
                                    "text": combined
                                })
                                TEXT_CORPUS.append(combined)

                            else:
                                text = (
                                    entry.get("content") or
                                    entry.get("text") or
                                    entry.get("title", "")
                                )

                                SEMANTIC_DATA.append({
                                    "type": "knowledge",
                                    "data": entry,
                                    "text": text
                                })
                                TEXT_CORPUS.append(text)

            except Exception as e:
                logging.warning(f"Failed loading {filename}: {e}")

logging.info(f"Knowledge Loaded: {len(SEMANTIC_DATA)} entries")

# -------------------------------------------------
# BUILD TFIDF
# -------------------------------------------------

if TEXT_CORPUS:
    vectorizer = TfidfVectorizer(stop_words="english")
    DOC_VECTORS = vectorizer.fit_transform(TEXT_CORPUS)
else:
    vectorizer = None
    DOC_VECTORS = None

logging.info("Semantic memory ready")

# -------------------------------------------------
# SEMANTIC SEARCH (STRONG FILTER)
# -------------------------------------------------

def semantic_search(question):
    if not vectorizer or DOC_VECTORS is None:
        return None

    query_vector = vectorizer.transform([question])
    similarities = cosine_similarity(query_vector, DOC_VECTORS)[0]

    top_index = np.argmax(similarities)
    top_score = similarities[top_index]

    if top_score > 0.40:
        return SEMANTIC_DATA[top_index]

    return None

# -------------------------------------------------
# CROSS REFERENCE
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
            results.append((score, verse))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]

# -------------------------------------------------
# ROUTES
# -------------------------------------------------

@app.route("/")
def home():
    return jsonify({"text": "Bible AI Running - Production Mode"})

@app.route("/ask", methods=["GET", "POST"])
def ask():
    try:
        if request.method == "GET":
            question = request.args.get("question", "")
        else:
            data = request.get_json(silent=True)
            question = data.get("question", "") if data else ""

        question = question.strip()
        lower_q = question.lower()

        if not question:
            return jsonify({"text": "Please provide a question."})

        logging.info(f"Question: {question}")

        # -------------------------------------------------
        # 1️⃣ DIRECT VERSE (SMART DETECTION)
        # -------------------------------------------------

        clean_q = lower_q.replace(".", ":")
        clean_q = re.sub(r"\s+", " ", clean_q)

        ref_pattern = r"([1-3]?\s?[a-zA-Z]+\s\d+(:\d+)?)"
        match = re.findall(ref_pattern, clean_q)

        if match:
            ref = match[0][0]

            # Chapter only (e.g. Genesis 1)
            if ":" not in ref:
                formatted = ""
                for key in bible_lookup:
                    if key.startswith(ref):
                        verse = bible_lookup[key]
                        formatted += f"{verse['reference']}\n{verse['text']}\n\n"

                if formatted:
                    return jsonify({"text": formatted.strip()})

            else:
                verse = bible_lookup.get(ref)
                if verse:
                    formatted = f"{verse['reference']}\n\n{verse['text']}\n\n"

                    for cr in cross_reference(verse):
                        formatted += f"{cr['reference']}\n{cr['text']}\n\n"

                    return jsonify({"text": formatted.strip()})

        # -------------------------------------------------
        # 2️⃣ SEMANTIC SEARCH
        # -------------------------------------------------

        result = semantic_search(question)

        if result:

            if result["type"] == "doctrine":
                entry = result["data"]

                formatted = f"{entry.get('title','')}\n\n"
                formatted += f"{entry.get('explanation','')}\n\n"
                formatted += f"{entry.get('logical_reasoning','')}\n\n"

                for ref in entry.get("core_verses", []):
                    verse = bible_lookup.get(ref.lower())
                    if verse:
                        formatted += f"{verse['reference']}\n{verse['text']}\n\n"

                return jsonify({"text": formatted.strip()})

            else:
                item = result["data"]
                formatted = f"{item.get('title','')}\n\n"
                formatted += f"{item.get('content') or item.get('text','')}\n\n"
                return jsonify({"text": formatted.strip()})

        # -------------------------------------------------
        # 3️⃣ SCRIPTURE FALLBACK
        # -------------------------------------------------

        words = re.findall(r"\b[a-zA-Z]+\b", lower_q)
        words = [w for w in words if len(w) > 4]

        results = []

        for verse in bible_list:
            score = sum(1 for w in words if w in verse["text"].lower())
            if score > 0:
                results.append((score, verse))

        results.sort(key=lambda x: x[0], reverse=True)

        formatted = ""
        for r in results[:5]:
            v = r[1]
            formatted += f"{v['reference']}\n{v['text']}\n\n"

        if formatted:
            return jsonify({"text": formatted.strip()})

        return jsonify({"text": "No relevant answer found."})

    except Exception as e:
        logging.error(str(e))
        return jsonify({"text": "Error processing request."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)