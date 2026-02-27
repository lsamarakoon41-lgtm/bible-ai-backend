from flask import Flask, request, jsonify
import json

app = Flask(__name__)

print("Loading Bible...")

with open("kjv.json", "r", encoding="utf-8") as f:
    bible_data = json.load(f)

# ✅ Handle dictionary-style JSON
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


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.json
        question = data.get("question", "").lower()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        results = []

        for verse in bible:
            if question in verse["text"].lower():
                results.append(verse)

            if len(results) == 5:
                break

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500