from flask import Flask, request, jsonify
import json

app = Flask(__name__)

print("Loading Bible...")

with open("kjv.json", "r", encoding="utf-8") as f:
    bible_data = json.load(f)

# Convert dictionary-style JSON to list
bible = []
for reference, text in bible_data.items():
    bible.append({
        "reference": reference,
        "text": text
    })

print("Bible Loaded:", len(bible), "verses")


@app.route("/")
def home():
    return jsonify({"status": "Bible AI Backend Running"})


@app.route("/ask", methods=["GET", "POST"])
def ask():
    try:
        # Get question safely
        if request.method == "GET":
            question = request.args.get("question", "")
        else:
            data = request.get_json(silent=True)
            question = data.get("question", "") if data else ""

        question = question.lower().strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        # Remove short/common words (like is, who, the)
        words = [w for w in question.split() if len(w) > 3]

        results = []

        for verse in bible:
            verse_text = verse["text"].lower()

            # Count how many meaningful words match
            match_count = sum(1 for word in words if word in verse_text)

            if match_count >= 1:  # at least 1 meaningful word match
                results.append({
                    "reference": verse["reference"],
                    "text": verse["text"],
                    "score": match_count
                })

        # Sort by highest score first
        results = sorted(results, key=lambda x: x["score"], reverse=True)

        # Remove score before sending to user
        final_results = [
            {"reference": r["reference"], "text": r["text"]}
            for r in results[:10]
        ]

        return jsonify(final_results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500