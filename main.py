from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# -------------------------
# Load Bible (KJV)
# -------------------------

BIBLE = []

try:
    with open("KJV.json", "r", encoding="utf-8") as f:
        BIBLE = json.load(f)
except Exception as e:
    print("Bible load error:", e)

# -------------------------
# Load Knowledge Index
# -------------------------

KNOWLEDGE = []

try:
    with open("knowledge_index.json", "r", encoding="utf-8") as f:
        index = json.load(f)

    for category in index:
        files = index[category]

        for file in files:
            path = os.path.join("knowledge", file)

            if os.path.exists(path):

                try:
                    with open(path, "r", encoding="utf-8") as k:
                        data = json.load(k)

                        if isinstance(data, list):
                            KNOWLEDGE.extend(data)

                except Exception as e:
                    print("Knowledge file error:", file, e)

except Exception as e:
    print("Index load error:", e)

print("Knowledge loaded:", len(KNOWLEDGE))


# -------------------------
# Search Knowledge
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
# Search Bible Verses
# -------------------------

def search_bible(question):

    question = question.lower()

    results = []

    for verse in BIBLE:

        text = verse.get("text","").lower()

        if question in text:
            results.append(verse)

        if len(results) >= 3:
            break

    return results


# -------------------------
# Ask Endpoint
# -------------------------

@app.route("/ask", methods=["POST"])
def ask():

    data = request.get_json()

    question = data.get("question","")

    # 1. Knowledge search
    item = search_knowledge(question)

    if item:

        response = {
            "type": "knowledge",
            "title": item.get("title",""),
            "short_answer": item.get("short_answer",""),
            "summary": item.get("summary",""),
            "scripture_references": item.get("scripture_references",[]),
            "major_points": item.get("major_points",[])
        }

        return jsonify(response)


    # 2. Bible search
    verses = search_bible(question)

    if verses:

        return jsonify({
            "type": "bible",
            "verses": verses
        })


    # 3. No answer
    return jsonify({
        "type": "unknown",
        "message": "No answer found in Bible knowledge."
    })


# -------------------------
# Health Check
# -------------------------

@app.route("/")
def home():
    return jsonify({
        "status":"Bible AI running",
        "knowledge_loaded": len(KNOWLEDGE),
        "bible_loaded": len(BIBLE)
    })


# -------------------------
# Railway Start
# -------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)