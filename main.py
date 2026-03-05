from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# -------------------------
# Load Bible
# -------------------------

BIBLE = []
BIBLE_VERSES = []

try:
    with open("kjv.json", "r", encoding="utf-8") as f:
        BIBLE = json.load(f)

    # Flatten Bible for searching
    for book in BIBLE:
        book_name = book.get("name","")

        for chapter in book.get("chapters",[]):

            for verse in chapter:

                BIBLE_VERSES.append({
                    "book": book_name,
                    "chapter": verse.get("chapter"),
                    "verse": verse.get("verse"),
                    "text": verse.get("text","")
                })

except Exception as e:
    print("Bible load error:", e)

print("Bible verses loaded:", len(BIBLE_VERSES))


# -------------------------
# Load Knowledge
# -------------------------

KNOWLEDGE = []

try:
    with open("knowledge_index.json","r",encoding="utf-8") as f:
        index = json.load(f)

    for category in index:

        for file in index[category]:

            path = os.path.join("knowledge",file)

            if os.path.exists(path):

                try:
                    with open(path,"r",encoding="utf-8") as k:

                        data = json.load(k)

                        if isinstance(data,list):

                            for item in data:

                                if isinstance(item,dict):

                                    KNOWLEDGE.append(item)

                except Exception as e:
                    print("Knowledge file error:",file,e)

except Exception as e:
    print("Knowledge index error:",e)

print("Knowledge loaded:",len(KNOWLEDGE))


# -------------------------
# Search Knowledge
# -------------------------

def search_knowledge(question):

    question = question.lower()

    for item in KNOWLEDGE:

        keywords = item.get("keywords",[])

        for word in keywords:

            if word.lower() in question:
                return item

    return None


# -------------------------
# Search Bible
# -------------------------

def search_bible(question):

    question = question.lower()

    results = []

    for verse in BIBLE_VERSES:

        text = verse["text"].lower()

        if question in text:

            results.append(verse)

        if len(results) >= 5:
            break

    return results


# -------------------------
# Ask Endpoint
# -------------------------

@app.route("/ask", methods=["POST"])
def ask():

    data = request.get_json()

    if not data:
        return jsonify({"error":"No JSON body"}),400

    question = data.get("question","")

    if question == "":
        return jsonify({"error":"Empty question"}),400

    # Knowledge search first
    item = search_knowledge(question)

    if item:

        return jsonify({
            "type":"knowledge",
            "title":item.get("title",""),
            "short_answer":item.get("short_answer",""),
            "summary":item.get("summary",""),
            "scripture_references":item.get("scripture_references",[]),
            "major_points":item.get("major_points",[])
        })


    # Bible search
    verses = search_bible(question)

    if verses:

        return jsonify({
            "type":"bible",
            "verses":verses
        })


    return jsonify({
        "type":"unknown",
        "message":"No answer found in Bible or knowledge."
    })


# -------------------------
# Health Check
# -------------------------

@app.route("/")
def home():

    return jsonify({
        "status":"Bible AI running",
        "knowledge_loaded":len(KNOWLEDGE),
        "bible_loaded":len(BIBLE_VERSES)
    })


# -------------------------
# Railway Start
# -------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT",8080))

    app.run(host="0.0.0.0",port=port)