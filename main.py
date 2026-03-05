from flask import Flask, request, jsonify
import json
import os
import random
import re

app = Flask(__name__)

# ================================
# LOAD KNOWLEDGE
# ================================

KNOWLEDGE_FOLDER = "knowledge"

knowledge_data = []

def load_knowledge():
    global knowledge_data
    knowledge_data = []

    if not os.path.exists(KNOWLEDGE_FOLDER):
        return

    for file in os.listdir(KNOWLEDGE_FOLDER):
        if file.endswith(".json"):
            path = os.path.join(KNOWLEDGE_FOLDER, file)
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    knowledge_data.extend(data)
                except:
                    pass

load_knowledge()

# ================================
# DAILY BIBLE VERSE
# ================================

daily_verses = [
    "John 3:16 - For God so loved the world...",
    "Psalm 23:1 - The Lord is my shepherd...",
    "Romans 8:28 - All things work together for good...",
    "Matthew 5:9 - Blessed are the peacemakers...",
]

def get_daily_verse():
    return random.choice(daily_verses)

# ================================
# SEMANTIC VERSE INTELLIGENCE
# ================================

SEMANTIC_MAP = {
    "jesus": ["christ", "messiah", "lord", "son"],
    "die": ["death", "crucified", "cross", "sacrifice"],
    "love": ["charity", "mercy", "compassion"],
    "faith": ["believe", "trust", "hope"],
    "sin": ["evil", "wickedness", "transgression"],
    "forgive": ["forgiveness", "mercy"],
    "save": ["salvation", "redeem"],
}

def expand_semantic_words(words):
    expanded = set(words)

    for w in words:
        if w in SEMANTIC_MAP:
            expanded.update(SEMANTIC_MAP[w])

    return list(expanded)

# ================================
# QUESTION CLEANING
# ================================

def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text

def extract_keywords(question):
    words = clean_text(question).split()
    return words

# ================================
# TOPIC MEMORY
# ================================

last_topic = None

def detect_topic(question):

    topics = {
        "jesus": ["jesus", "christ"],
        "salvation": ["save", "salvation"],
        "love": ["love", "charity"],
        "faith": ["faith", "believe"],
    }

    for topic, words in topics.items():
        for w in words:
            if w in question.lower():
                return topic

    return None

# ================================
# VERSE SCORING
# ================================

def semantic_bonus(text, keywords):

    score = 0
    text = text.lower()

    for k in keywords:
        if k in text:
            score += 1

    return score

# ================================
# SMART SEARCH
# ================================

def search_answer(question):

    global last_topic

    keywords = extract_keywords(question)

    keywords = expand_semantic_words(keywords)

    topic = detect_topic(question)

    if topic:
        last_topic = topic

    results = []

    for item in knowledge_data:

        text = item.get("answer", "").lower()

        score = 0

        for k in keywords:
            if k in text:
                score += 2

        score += semantic_bonus(text, keywords)

        if score > 0:
            results.append((score, item))

    results.sort(reverse=True, key=lambda x: x[0])

    answers = []

    for r in results[:3]:
        answers.append(r[1]["answer"])

    if answers:
        return "\n\n".join(answers)

    return "No answer found."

# ================================
# BIBLE A TO Z READING
# ================================

bible_books = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy",
    "Joshua","Judges","Ruth","1 Samuel","2 Samuel",
    "1 Kings","2 Kings","1 Chronicles","2 Chronicles",
    "Ezra","Nehemiah","Esther","Job","Psalms","Proverbs",
    "Ecclesiastes","Song of Solomon","Isaiah","Jeremiah",
    "Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah",
    "Haggai","Zechariah","Malachi",
    "Matthew","Mark","Luke","John","Acts",
    "Romans","1 Corinthians","2 Corinthians","Galatians",
    "Ephesians","Philippians","Colossians","1 Thessalonians",
    "2 Thessalonians","1 Timothy","2 Timothy","Titus",
    "Philemon","Hebrews","James","1 Peter","2 Peter",
    "1 John","2 John","3 John","Jude","Revelation"
]

reading_index = 0

def bible_read_next():

    global reading_index

    if reading_index >= len(bible_books):
        reading_index = 0

    book = bible_books[reading_index]

    reading_index += 1

    return f"Next Bible Book: {book}"

# ================================
# API ROUTE
# ================================

@app.route("/ask", methods=["POST"])
def ask():

    data = request.json

    question = data.get("question","")

    if question.lower() == "read bible":
        return jsonify({"answer": bible_read_next()})

    answer = search_answer(question)

    return jsonify({
        "answer": answer,
        "daily_verse": get_daily_verse()
    })

# ================================
# HOME
# ================================

@app.route("/")
def home():

    return jsonify({
        "message": "Bible AI running",
        "daily_verse": get_daily_verse()
    })

# ================================
# START SERVER
# ================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port)