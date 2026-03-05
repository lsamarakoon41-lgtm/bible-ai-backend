from flask import Flask, request, jsonify
import json
import os
import re
from collections import Counter

app = Flask(__name__)

# =====================================================
# CONFIG
# =====================================================

STOP_WORDS = {
    "the","is","a","an","what","when","where","who","why","how",
    "of","and","to","in","on","for","with","by","at","from"
}

MAX_VERSES = 5

# =====================================================
# TEXT CLEANING
# =====================================================

def clean_text(text):
    words = re.findall(r'\w+', text.lower())
    return [w for w in words if w not in STOP_WORDS]

# =====================================================
# LOAD BIBLE (PRE-INDEXED FOR SPEED)
# =====================================================

with open("kjv.json", "r", encoding="utf-8") as f:
    bible_data = json.load(f)

indexed_verses = []
bible_word_frequency = Counter()

for book in bible_data:
    for chapter in book["chapters"]:
        for verse in chapter:

            words = clean_text(verse["text"])

            for w in words:
                bible_word_frequency[w] += 1

            indexed_verses.append({
                "reference": f'{book["name"]} {verse["chapter"]}:{verse["verse"]}',
                "text": verse["text"],
                "words": words
            })

# =====================================================
# LOAD KNOWLEDGE (FIXED FOR YOUR STRUCTURE)
# =====================================================

knowledge_folder = "knowledge"
knowledge_data = {}
knowledge_word_frequency = Counter()

for filename in os.listdir(knowledge_folder):

    if filename.endswith(".json"):

        with open(os.path.join(knowledge_folder, filename), "r", encoding="utf-8") as f:

            items = json.load(f)

            for item in items:

                title = item.get("title","")

                content_parts = []

                if "short_answer" in item:
                    content_parts.append(item["short_answer"])

                if "summary" in item:
                    content_parts.append(item["summary"])

                if "major_points" in item:
                    content_parts.append(" ".join(item["major_points"]))

                content = " ".join(content_parts)

                content_words = clean_text(content)
                title_words = clean_text(title)

                for w in content_words + title_words:
                    knowledge_word_frequency[w] += 1

                item["clean_content"] = content_words
                item["clean_title"] = title_words
                item["content"] = content

            knowledge_data[filename] = items

# =====================================================
# QUESTION TYPE DETECTION
# =====================================================

def detect_question_type(question):

    q = question.lower()

    if any(w in q for w in ["sin","forgive","marriage","wrong","should"]):
        return "moral"

    if any(w in q for w in ["who","when","where","history"]):
        return "history"

    if any(w in q for w in ["prophecy","revelation","antichrist","end times"]):
        return "prophecy"

    if any(w in q for w in ["grace","faith","salvation","justify","define","explain"]):
        return "theology"

    return "general"

# =====================================================
# WORD IMPORTANCE
# =====================================================

def word_importance(word, frequency_map):

    freq = frequency_map.get(word, 1)

    return 1 / freq

# =====================================================
# KNOWLEDGE SEARCH
# =====================================================

def search_knowledge(question_words, question_type):

    best_answer = None
    highest_score = 0

    for filename, items in knowledge_data.items():

        weight = 3 if question_type in filename else 1

        for item in items:

            score = 0

            for w in question_words:

                if w in item["clean_content"]:
                    score += word_importance(w, knowledge_word_frequency)

                if w in item["clean_title"]:
                    score += word_importance(w, knowledge_word_frequency) * 2

            score *= weight

            if score > highest_score:
                highest_score = score
                best_answer = item.get("content")

    return best_answer, highest_score

# =====================================================
# BIBLE SEARCH
# =====================================================

def search_bible(question_words):

    scored = []

    for verse in indexed_verses:

        score = 0

        for w in question_words:

            if w in verse["words"]:
                score += word_importance(w, bible_word_frequency)

        if score > 0:
            scored.append((score, verse))

    scored.sort(reverse=True, key=lambda x: x[0])

    top = scored[:MAX_VERSES]

    verses = [
        {
            "reference": v["reference"],
            "text": v["text"]
        }
        for s, v in top
    ]

    total_score = sum([s for s, _ in top])

    return verses, total_score

# =====================================================
# TONE PERSONALIZATION
# =====================================================

def apply_tone(answer, tone):

    if tone == "encouragement":
        return "Take heart. Scripture assures us that " + answer

    elif tone == "academic":
        return "Doctrinally speaking, " + answer

    elif tone == "teaching":
        return "According to the Holy Scriptures, " + answer

    else:
        return answer

# =====================================================
# SUMMARY FORMAT
# =====================================================

def build_summary(answer, verses, confidence):

    return {
        "Explanation": answer,
        "Biblical Support": verses,
        "Confidence Score": round(confidence, 2)
    }

# =====================================================
# MAIN ROUTE
# =====================================================

@app.route("/ask", methods=["POST"])
def ask():

    data = request.get_json()

    question = data.get("question","")
    tone = data.get("tone","default")

    if not question:
        return jsonify({"error":"No question provided"})

    question_words = clean_text(question)

    question_type = detect_question_type(question)

    knowledge_answer, knowledge_score = search_knowledge(question_words, question_type)

    bible_verses, bible_score = search_bible(question_words)

    total_score = knowledge_score + bible_score

    confidence = min(100, total_score * 100)

    if not knowledge_answer:
        knowledge_answer = "No direct doctrinal explanation found in knowledge base."

    final_answer = apply_tone(knowledge_answer, tone)

    response = {
        "type": question_type,
        "result": build_summary(final_answer, bible_verses, confidence)
    }

    return jsonify(response)

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)