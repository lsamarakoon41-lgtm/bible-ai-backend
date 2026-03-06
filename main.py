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
# Load Brain Folder
# -------------------------

BRAIN = []

brain_folder = "brain"

if os.path.exists(brain_folder):

    for file in os.listdir(brain_folder):

        path = os.path.join(brain_folder, file)

        if os.path.isfile(path):

            try:

                if file.endswith(".json"):

                    with open(path, "r", encoding="utf-8") as f:

                        data = json.load(f)

                        if isinstance(data, list):

                            for item in data:

                                if isinstance(item, dict):
                                    BRAIN.append(item)

                elif file.endswith(".txt"):

                    with open(path, "r", encoding="utf-8") as f:

                        text = f.read()

                        BRAIN.append({
                            "title": file,
                            "keywords": file.replace(".txt","").split("_"),
                            "short_answer": text[:200],
                            "summary": text,
                            "scripture_references": [],
                            "major_points": []
                        })

            except Exception as e:
                print("Brain load error:", file, e)

print("Brain loaded:", len(BRAIN))


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
# Question Understanding
# -------------------------

def understand_question(question):

    question = question.lower()

    if question.startswith("who is"):
        return "person"

    if question.startswith("what is"):
        return "definition"

    if question.startswith("what does"):
        return "meaning"

    if question.startswith("where"):
        return "place"

    if question.startswith("why"):
        return "reason"

    if question.startswith("how"):
        return "explanation"

    return "general"


# -------------------------
# Auto Summarize
# -------------------------

def auto_summarize(text):

    if not text:
        return ""

    sentences = re.split(r'(?<=[.!?]) +', text)

    if len(sentences) <= 3:
        return text

    summary = " ".join(sentences[:3])

    return summary


# -------------------------
# Smart Knowledge Ranking
# -------------------------

def smart_knowledge_search(question):

    question = question.lower()
    words = question.split()

    best_match = None
    best_score = 0

    combined = KNOWLEDGE + BRAIN

    for item in combined:

        keywords = item.get("keywords", [])
        score = 0

        for word in words:

            for key in keywords:

                if word in key.lower():
                    score += 1

        if score > best_score:
            best_score = score
            best_match = item

    if best_score >= 2:
        return best_match

    return None


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

    combined = KNOWLEDGE + BRAIN

    for item in combined:

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
# Ask AI
# -------------------------

@app.route("/ask", methods=["POST"])
def ask():

    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON body"}), 400

    question = data.get("question", "")

    question_type = understand_question(question)

    if question == "":
        return jsonify({"error": "Empty question"}), 400

    range_result = find_range(question)

    if range_result:
        return jsonify({"type": "reference_range", "verses": range_result})

    ref = find_reference(question)

    if ref:
        return jsonify({"type": "reference", "verse": ref})

    item = smart_knowledge_search(question)

    if item:

        return jsonify({
            "type": "knowledge",
            "title": item.get("title", ""),
            "short_answer": item.get("short_answer", ""),
            "summary": auto_summarize(item.get("summary", "")),
            "scripture_references": item.get("scripture_references", []),
            "major_points": item.get("major_points", [])
        })

    item = search_knowledge(question)

    if item:

        return jsonify({
            "type": "knowledge",
            "title": item.get("title", ""),
            "short_answer": item.get("short_answer", ""),
            "summary": auto_summarize(item.get("summary", "")),
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
        "brain_loaded": len(BRAIN),
        "bible_loaded": len(BIBLE_VERSES)
    })


# -------------------------
# Railway Start
# -------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)