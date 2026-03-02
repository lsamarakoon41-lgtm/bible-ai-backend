from flask import Flask, request, jsonify
import json
import re
import os
from collections import defaultdict

app = Flask(__name__)

print("Loading Bible...")

# -----------------------------
# Load Bible
# -----------------------------

with open("kjv.json", "r", encoding="utf-8") as f:
    bible_data = json.load(f)

bible = [{"reference": ref, "text": text} for ref, text in bible_data.items()]

# Fast lookup dictionary (important upgrade)
bible_lookup = {v["reference"].lower(): v for v in bible}

print("Bible Loaded:", len(bible), "verses")

# -----------------------------
# Build Structure (Book → Chapter → Verses)
# -----------------------------

structure = defaultdict(lambda: defaultdict(list))

for verse in bible:
    ref = verse["reference"]
    parts = ref.rsplit(" ", 1)

    if len(parts) == 2:
        book = parts[0]
        chapter_verse = parts[1]

        if ":" in chapter_verse:
            chapter, verse_num = chapter_verse.split(":")
            structure[book][chapter].append(verse)

books_list = list(structure.keys())

# -----------------------------
# 🧠 Brain Folder System
# -----------------------------

BRAIN_FOLDER = "brain"

def load_brain():
    brain_data = []

    if not os.path.exists(BRAIN_FOLDER):
        os.makedirs(BRAIN_FOLDER)

    for filename in os.listdir(BRAIN_FOLDER):
        if filename.endswith(".txt") or filename.endswith(".md"):
            filepath = os.path.join(BRAIN_FOLDER, filename)

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

                brain_data.append({
                    "source": filename,
                    "content": content
                })

    print("Brain Loaded:", len(brain_data), "files")
    return brain_data

brain_knowledge = load_brain()


def search_brain(question, limit=3):
    words = [w for w in re.findall(r"\b\w+\b", question.lower()) if len(w) > 4]

    results = []

    for item in brain_knowledge:
        text = item["content"].lower()
        score = sum(1 for word in words if word in text)

        if score > 0:
            results.append({
                "source": item["source"],
                "content": item["content"][:800],
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:limit]

# -----------------------------
# 📖 Scripture Interprets Scripture
# -----------------------------

def scripture_explains_scripture(main_verse, limit=5):

    stopwords = {
        "the","and","for","with","that","this","from","shall",
        "have","will","unto","your","you","are","was","were",
        "him","his","her","they","them","their","into","not",
        "said","saying","there","which","when","what","who"
    }

    main_text = main_verse["text"].lower()

    words = [
        w for w in re.findall(r"\b[a-zA-Z]+\b", main_text)
        if len(w) > 4 and w not in stopwords
    ]

    scored = []

    for verse in bible:
        if verse["reference"] == main_verse["reference"]:
            continue

        verse_text = verse["text"].lower()
        score = sum(1 for word in words if word in verse_text)

        if score > 0:
            scored.append({
                "reference": verse["reference"],
                "text": verse["text"],
                "score": score
            })

    scored.sort(key=lambda x: x["score"], reverse=True)

    return [
        {"reference": r["reference"], "text": r["text"]}
        for r in scored[:limit]
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

        question_lower = question.lower()

        # ---------------------------------------
        # 1️⃣ Direct Reference (Improved)
        # ---------------------------------------
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

        # ---------------------------------------
        # 2️⃣ Chapter Request
        # ---------------------------------------
        chapter_pattern = r"([1-3]?\s?[a-zA-Z\s]+?)\s(?:chapter\s)?(\d+)"
        chapter_match = re.findall(chapter_pattern, question_lower)

        if chapter_match:
            book_input, chapter = chapter_match[0]
            book_input = book_input.strip().title()

            for b in books_list:
                if b.lower() == book_input.lower():
                    return jsonify({
                        "type": "chapter",
                        "book": b,
                        "chapter": chapter,
                        "verses": structure[b].get(chapter, [])
                    })

        # ---------------------------------------
        # 3️⃣ Chapter Count
        # ---------------------------------------
        if "how many chapters" in question_lower:
            for book in books_list:
                if book.lower() in question_lower:
                    return jsonify({
                        "type": "chapter_count",
                        "answer": f"{book} has {len(structure[book])} chapters."
                    })

        # ---------------------------------------
        # 4️⃣ Brain Search (before fallback)
        # ---------------------------------------
        brain_results = search_brain(question)

        if brain_results:
            return jsonify({
                "type": "brain",
                "results": brain_results
            })

        # ---------------------------------------
        # 5️⃣ Bible Keyword Search
        # ---------------------------------------
        words = [w for w in re.findall(r"\b\w+\b", question_lower) if len(w) > 3]

        results = []

        for verse in bible:
            verse_text = verse["text"].lower()
            score = sum(1 for word in words if word in verse_text)

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
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)