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
# Topic Intelligence (NEW)
# -------------------------

TOPIC_KEYWORDS = {

    "jesus":[
        "jesus","christ","messiah","son of god"
    ],

    "salvation":[
        "salvation","saved","eternal life","grace","redeem"
    ],

    "love":[
        "love","charity","loving","compassion"
    ],

    "faith":[
        "faith","believe","belief","trust god"
    ],

    "fear":[
        "fear","afraid","anxious","worry"
    ],

    "sin":[
        "sin","sinner","evil","wicked"
    ]

}


# -------------------------
# Semantic Verse Intelligence (NEW)
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
                    return results

    return results


# -------------------------
# Multi Verse Intelligence (NEW)
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

    final = []

    for item in results[:5]:
        final.append(item[1])

    return final


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
# Bible A → Z Reading System (NEW)
# -------------------------

READ_INDEX = 0

@app.route("/read_bible", methods=["GET"])
def read_bible():

    global READ_INDEX

    if READ_INDEX >= len(BIBLE_VERSES):
        READ_INDEX = 0

    verse = BIBLE_VERSES[READ_INDEX]

    READ_INDEX += 1

    return jsonify({
        "type":"bible_reading",
        "verse":verse
    })


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


    # Semantic search (NEW)
    verses = semantic_search(question)

    if verses:

        return jsonify({
            "type":"bible_semantic",
            "verses":verses
        })


    # Multi verse search (NEW)
    verses = multi_verse_search(question)

    if verses:

        return jsonify({
            "type":"bible_multi",
            "verses":verses
        })


    # Basic search (ORIGINAL)
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