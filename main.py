from flask import Flask, request, jsonify
import json

app = Flask(__name__)

print("Loading Bible...")

with open("kjv.json", "r", encoding="utf-8") as f:
    bible_data = json.load(f)

# Flatten verses
bible = []
for book in bible_data:
    for chapter in book["chapters"]:
        for verse in chapter:
            bible.append({
                "book": book["name"],
                "text": verse
            })

print("Bible Loaded:", len(bible), "verses")


@app.route("/")
def home():
    return "Bible AI Backend Running"


@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question", "").lower()

    results = []

    for verse in bible:
        if question in verse["text"].lower():
            results.append(verse)

        if len(results) == 5:
            break

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)