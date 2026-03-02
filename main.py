from flask import Flask, request, jsonify
import json
import re
import os
import time
import logging
from collections import defaultdict, Counter
from functools import lru_cache

app = Flask(__name__)

# -----------------------------
# Logging Setup
# -----------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Starting Bible AI Backend...")

# -----------------------------
# Load Bible
# -----------------------------

with open("kjv.json", "r", encoding="utf-8") as f:
    bible_data = json.load(f)

bible = [{"reference": ref, "text": text} for ref, text in bible_data.items()]
bible_lookup = {v["reference"].lower(): v for v in bible}

logging.info(f"Bible Loaded: {len(bible)} verses")

# -----------------------------
# Structure: Book → Chapter → Verses
# -----------------------------

structure = defaultdict(lambda: defaultdict(list))

for verse in bible:
    ref = verse["reference"]
    parts = ref.rsplit(" ", 1)

    if len(parts) == 2:
        book = parts[0]
        chapter_verse = parts[1]

        if ":" in chapter_verse:
            chapter, _ = chapter_verse.split(":")
            structure[book][chapter].append(verse)

books_list = list(structure.keys())

# -----------------------------
# 🧠 Brain System (Auto Refresh + Smart Ranking)
# -----------------------------

BRAIN_FOLDER = "brain"
brain_knowledge = []
brain_last_loaded = 0
BRAIN_REFRESH_INTERVAL = 30  # seconds


def load_brain():
    global brain_last_loaded
    knowledge = []

    if not os.path.exists(BRAIN_FOLDER):
        os.makedirs(BRAIN_FOLDER)

    for filename in os.listdir(BRAIN_FOLDER):
        if filename.endswith((".txt", ".md")):
            filepath = os.path.join(BRAIN_FOLDER, filename)

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                paragraphs = [p.strip() for p in content.split("\n") if p.strip()]

                for para in paragraphs:
                    knowledge.append({
                        "source": filename,
                        "content": para,
                        "content_lower": para.lower(),
                        "word_freq": Counter(re.findall(r"\b[a-zA-Z]+\b", para.lower()))
                    })

    brain_last_loaded = time.time()
    logging.info(f"Brain Reloaded: {len(knowledge)} segments")
    return knowledge


def auto_refresh_brain():
    global brain_knowledge
    if time.time() - brain_last_loaded > BRAIN_REFRESH_INTERVAL:
        brain_knowledge = load_brain()


# Initial load
brain_knowledge = load_brain()


@lru_cache(maxsize=200)
def search_brain_cached(question):
    auto_refresh_brain()

    question_words = re.findall(r"\b[a-zA-Z]+\b", question.lower())
    question_freq = Counter([w for w in question_words if len(w) > 4])

    results = []

    for item in brain_knowledge:
        score = 0

        for word, q_count in question_freq.items():
            score += item["word_freq"].get(word, 0) * q_count

        if score > 0:
            results.append({
                "source": item["source"],
                "content": item["content"],
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]


# -----------------------------
# Scripture Interprets Scripture
# -----------------------------

def scripture_explains_scripture(main_verse, limit=5):

    stopwords = {
        "the","and","for","with","that","this","from","shall",
        "have","will","unto","your","you","are","was","were",
        "him","his","her","they","them","their","into","not",
        "said","saying","there","which","when","what","who"
    }

    words = [
        w for w in re.findall(r"\b[a-zA-Z]+\b", main_verse["text"].lower())
        if len(w) > 4 and w not in stopwords
    ]

    results = []

    for verse in bible:
        if verse["reference"] == main_verse["reference"]:
            continue

        score = sum(1 for word in words if word in verse["text"].lower())

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


# -----------------------------
# Routes
# -----------------------------

@app.route("/")
def home():
    return jsonify({"status": "Bible AI Backend Running"})


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

        logging.info(f"Question received: {question}")

        question_lower = question.lower()

        # 1️⃣ Direct Verse Reference
        ref_pattern = r"([1-3]?\s?[a-zA-Z\s]+?\s\d+:\d+)"
        ref_match = re.findall(ref_pattern, question)

        if ref_match:
            ref = ref_match[0].strip()

            if ref.lower() in bible_lookup:
                verse = bible_lookup[ref.lower()]
                explanation = scripture_explains_scripture(verse)

                return jsonify({
                    "type": "verse",
                    "main_verse": verse,
                    "scripture_explanation": explanation
                })

        # 2️⃣ Brain Search (Smart + Cached)
        brain_results = search_brain_cached(question)

        if brain_results:
            return jsonify({
                "type": "brain",
                "results": brain_results
            })

        # 3️⃣ Bible Keyword Search
        words = [w for w in re.findall(r"\b[a-zA-Z]+\b", question_lower) if len(w) > 3]

        results = []

        for verse in bible:
            score = sum(1 for word in words if word in verse["text"].lower())

            if score > 0:
                results.append({
                    "reference": verse["reference"],
                    "text": verse["text"],
                    "score": score
                })

        results.sort(key=lambda x: x["score"], reverse=True)

        return jsonify({
            "type": "search",
            "results": [
                {"reference": r["reference"], "text": r["text"]}
                for r in results[:5]
            ]
        })

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)