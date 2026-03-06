from flask import Flask, request, jsonify
import json
import os
import random
import re

app = Flask(__name__)

# -------------------------
# Load Bible
# -------------------------

BIBLE = []
BIBLE_VERSES = []
VERSE_INDEX = {}

try:
    with open("kjv.json", "r", encoding="utf-8") as f:
        BIBLE = json.load(f)

    for book in BIBLE:
        book_name = book.get("name", "")

        for chapter in book.get("chapters", []):

            for verse in chapter:

                verse_data = {
                    "book": book_name,
                    "chapter": verse.get("chapter"),
                    "verse": verse.get("verse"),
                    "text": verse.get("text", "")
                }

                BIBLE_VERSES.append(verse_data)

                key = f"{book_name.lower()}_{verse.get('chapter')}_{verse.get('verse')}"
                VERSE_INDEX[key] = verse_data

except Exception as e:
    print("Bible load error:", e)

print("Bible verses loaded:", len(BIBLE_VERSES))


# -------------------------
# Load Knowledge
# -------------------------

KNOWLEDGE = []

try:
    with open("knowledge_index.json", "r", encoding="utf-8") as f:
        index = json.load(f)

    for category in index:

        for file in index[category]:

            path = os.path.join("knowledge", file)

            if os.path.exists(path):

                try:
                    with open(path, "r", encoding="utf-8") as k:

                        data = json.load(k)

                        if isinstance(data, list):

                            for item in data:

                                if isinstance(item, dict):
                                    KNOWLEDGE.append(item)

                except Exception as e:
                    print("Knowledge file error:", file, e)

except Exception as e:
    print("Knowledge index error:", e)

print("Knowledge loaded:", len(KNOWLEDGE))


# -------------------------
# Topic Intelligence
# -------------------------

TOPIC_KEYWORDS = {

    "jesus": ["jesus", "christ", "messiah", "son of god"],
    "salvation": ["salvation", "saved", "eternal life", "grace", "redeem"],
    "love": ["love", "charity", "loving", "compassion"],
    "faith": ["faith", "believe", "belief", "trust god"],
    "fear": ["fear", "afraid", "anxious", "worry"],
    "sin": ["sin", "sinner", "evil", "wicked"]

}


# -------------------------
# Bible Reference Detection
# -------------------------

def find_reference(question):

    pattern = r'([1-3]?\s?[A-Za-z]+)\s(\d+):(\d+)'
    match = re.search(pattern, question)

    if match:

        book = match.group(1).strip()
        chapter = int(match.group(2))
        verse = int(match.group(3))

        key = f"{book.lower()}_{chapter}_{verse}"

        return VERSE_INDEX.get(key)

    return None


# -------------------------
# Verse Range Detection
# -------------------------

def find_range(question):

    pattern = r'([1-3]?\s?[A-Za-z]+)\s(\d+):(\d+)-(\d+)'
    match = re.search(pattern, question)

    if match:

        book = match.group(1).strip()
        chapter = int(match.group(2))
        start = int(match.group(3))
        end = int(match.group(4))

        verses = []

        for v in BIBLE_VERSES:

            if v["book"].lower() == book.lower() and v["chapter"] == chapter:

                if start <= v["verse"] <= end:
                    verses.append(v)

        return verses

    return None


# -------------------------
# Semantic Search
# -------------------------

def semantic_search(question):

    question = question.lower()
    detected_topics = []

    for topic in TOPIC_KEYWORDS:

        for word in TOPIC_KEYWORDS[topic]:

            if word in question:
                detected_topics.append(topic)
                break

    results = []

    if detected_topics:

        for verse in BIBLE_VERSES:

            text = verse["text"].lower()

            for topic in detected_topics:

                for keyword in TOPIC_KEYWORDS[topic]:

                    if keyword in text:
                        results.append(verse)
                        break

            if len(results) >= 5:
                break

    return results


# -------------------------
# Multi Verse Search
# -------------------------

def multi_verse_search(question):

    words = question.lower().split()
    results = []

    for verse in BIBLE_VERSES:

        text = verse["text"].lower()
        score = 0

        for word in words:

            if word in text:
                score += 1

        if score >= 2:
            results.append((score, verse))

    results.sort(reverse=True, key=lambda x: x[0])

    return [r[1] for r in results[:5]]


# -------------------------
# Knowledge Search
# -------------------------

def search_knowledge(question):

    question = question.lower()

    for item in KNOWLEDGE:

        keywords = item.get("keywords", [])

        for word in keywords:

            if word.lower() in question:
                return item

    return None


# -------------------------
# Basic Bible Search
# -------------------------

def search_bible(question):

    question = question.lower()
    results = []

    for verse in BIBLE_VERSES:

        if question in verse["text"].lower():
            results.append(verse)

        if len(results) >= 5:
            break

    return results


# -------------------------
# API : Books
# -------------------------

@app.route("/books", methods=["GET"])
def books():
    return jsonify([b.get("name") for b in BIBLE])


# -------------------------
# API : Chapter Reader
# -------------------------

@app.route("/chapter", methods=["GET"])
def chapter():

    book = request.args.get("book")
    chapter = request.args.get("chapter")

    if not book or not chapter:
        return jsonify({"error": "book and chapter required"}), 400

    chapter = int(chapter)

    verses = [v for v in BIBLE_VERSES if v["book"].lower() == book.lower() and v["chapter"] == chapter]

    return jsonify(verses)


# -------------------------
# API : Random Verse
# -------------------------

@app.route("/random-verse", methods=["GET"])
def random_verse():
    return jsonify(random.choice(BIBLE_VERSES))


# -------------------------
# API : Stats
# -------------------------

@app.route("/stats", methods=["GET"])
def stats():

    return jsonify({
        "books": len(BIBLE),
        "verses": len(BIBLE_VERSES),
        "knowledge_items": len(KNOWLEDGE)
    })


# -------------------------
# Ask AI
# -------------------------

@app.route("/ask", methods=["POST"])
def ask():

    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON body"}), 400

    question = data.get("question", "")

    if question == "":
        return jsonify({"error": "Empty question"}), 400

    range_result = find_range(question)

    if range_result:
        return jsonify({"type": "reference_range", "verses": range_result})

    ref = find_reference(question)

    if ref:
        return jsonify({"type": "reference", "verse": ref})

    item = search_knowledge(question)

    if item:

        return jsonify({
            "type": "knowledge",
            "title": item.get("title", ""),
            "short_answer": item.get("short_answer", ""),
            "summary": item.get("summary", ""),
            "scripture_references": item.get("scripture_references", []),
            "major_points": item.get("major_points", [])
        })

    verses = semantic_search(question)

    if verses:
        return jsonify({"type": "bible_semantic", "verses": verses})

    verses = multi_verse_search(question)

    if verses:
        return jsonify({"type": "bible_multi", "verses": verses})

    verses = search_bible(question)

    if verses:
        return jsonify({"type": "bible", "verses": verses})

    return jsonify({
        "type": "unknown",
        "message": "No answer found in Bible or knowledge."
    })


# -------------------------
# Health
# -------------------------

@app.route("/")
def home():

    return jsonify({
        "status": "Bible AI running",
        "knowledge_loaded": len(KNOWLEDGE),
        "bible_loaded": len(BIBLE_VERSES)
    })


# -------------------------
# Railway Start
# -------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)