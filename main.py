import os
import re
import json
import numpy as np
from flask import Flask, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------------------------------------
# APP SETUP
# -------------------------------------------------

app = Flask(__name__)

KNOWLEDGE_FOLDER = "knowledge"
BIBLE_FILE = "bible.json"

SEMANTIC_DATA = []
VECTOR_TEXTS = []
vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = None

bible_lookup = {}
bible_list = []

# -------------------------------------------------
# LOAD KNOWLEDGE FILES
# -------------------------------------------------

def load_knowledge():
    global SEMANTIC_DATA, VECTOR_TEXTS, tfidf_matrix

    for filename in os.listdir(KNOWLEDGE_FOLDER):
        if filename.endswith(".json"):
            path = os.path.join(KNOWLEDGE_FOLDER, filename)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

                for entry in data:
                    text_parts = []

                    for key in ["title", "explanation", "logical_reasoning", "content", "text"]:
                        if key in entry and entry[key]:
                            text_parts.append(entry[key])

                    combined_text = " ".join(text_parts)

                    SEMANTIC_DATA.append({
                        "data": entry,
                        "combined_text": combined_text
                    })

                    VECTOR_TEXTS.append(combined_text)

    if VECTOR_TEXTS:
        tfidf_matrix = vectorizer.fit_transform(VECTOR_TEXTS)

# -------------------------------------------------
# LOAD BIBLE
# -------------------------------------------------

def load_bible():
    global bible_lookup, bible_list

    with open(BIBLE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

        for verse in data:
            key = verse["reference"].lower()
            bible_lookup[key] = verse
            bible_list.append(verse)

# -------------------------------------------------
# SYNONYMS
# -------------------------------------------------

SYNONYMS = {
    "die": ["crucified", "death", "killed"],
    "love": ["charity", "compassion"],
    "sin": ["iniquity", "transgression"],
    "bible": ["scripture", "word"],
    "jesus": ["christ", "messiah", "son"]
}

def expand_question(question):
    words = question.lower().split()
    expanded = words.copy()

    for word in words:
        if word in SYNONYMS:
            expanded.extend(SYNONYMS[word])

    return " ".join(expanded)

# -------------------------------------------------
# INTENT DETECTION
# -------------------------------------------------

def detect_intent(question):
    q = question.lower()

    if re.search(r"\b\d+[:.]\d+\b", q):
        return "verse_lookup"

    if "chapter" in q:
        return "chapter_lookup"

    if any(w in q for w in ["who is", "what is", "define", "explain"]):
        return "definition"

    if any(w in q for w in ["why", "reason"]):
        return "reason"

    if any(w in q for w in ["how"]):
        return "process"

    return "general"

# -------------------------------------------------
# SEMANTIC SEARCH
# -------------------------------------------------

def semantic_search(question):
    if tfidf_matrix is None:
        return None

    query_vector = vectorizer.transform([question])
    similarities = cosine_similarity(query_vector, tfidf_matrix)[0]

    top_indices = similarities.argsort()[-3:][::-1]

    results = []
    for idx in top_indices:
        if similarities[idx] > 0.30:
            results.append(SEMANTIC_DATA[idx]["data"])

    return results if results else None

# -------------------------------------------------
# BUILD SMART ANSWER
# -------------------------------------------------

def build_smart_answer(results, question):
    response = ""

    for entry in results:
        for key in ["title", "explanation", "logical_reasoning", "content", "text"]:
            if key in entry and entry[key]:
                response += entry[key] + "\n\n"

    # Attach best verse
    words = question.lower().split()
    best_verse = None
    best_score = 0

    for verse in bible_list:
        score = sum(1 for w in words if w in verse["text"].lower())
        if score > best_score:
            best_score = score
            best_verse = verse

    if best_verse:
        response += "Bible Verse:\n"
        response += f"{best_verse['reference']}\n"
        response += f"{best_verse['text']}\n\n"

    response += "May the truth of Scripture guide you."

    return response.strip()

# -------------------------------------------------
# ROUTE
# -------------------------------------------------

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"text": "Please ask a question."})

    intent = detect_intent(question)

    # 1️⃣ Verse lookup
    if intent == "verse_lookup":
        key = question.lower()
        verse = bible_lookup.get(key)
        if verse:
            text = f"{verse['reference']}\n{verse['text']}"
            return jsonify({"text": text})

    # 2️⃣ Chapter lookup
    if intent == "chapter_lookup":
        chapter_ref = question.lower().replace("chapter", "").strip()
        formatted = ""
        count = 0

        for key, verse in bible_lookup.items():
            if key.startswith(chapter_ref + ":"):
                formatted += f"{verse['reference']}\n{verse['text']}\n\n"
                count += 1
                if count >= 40:
                    break

        if formatted:
            return jsonify({"text": formatted.strip()})

    # 3️⃣ Semantic search
    expanded_q = expand_question(question)
    results = semantic_search(expanded_q)

    if results:
        answer_text = build_smart_answer(results, question)
        return jsonify({"text": answer_text})

    return jsonify({"text": "I could not find a clear answer in Scripture. Please ask another question."})

# -------------------------------------------------
# STARTUP
# -------------------------------------------------

load_knowledge()
load_bible()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)