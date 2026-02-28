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

        results = []

        words = question.split()

        for verse in bible:
            verse_text = verse["text"].lower()

            if any(word in verse_text for word in words):
                results.append(verse)

            if len(results) == 5:
                break

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500