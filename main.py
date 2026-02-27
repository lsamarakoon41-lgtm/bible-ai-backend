import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from flask import Flask, request, jsonify
from flask_cors import CORS

TOP_K = 5

app = Flask(__name__)
CORS(app)

# ===============================
# LOAD BIBLE
# ===============================

print("Loading Bible...")

with open("kjv.json", "r", encoding="utf-8") as f:
    bible_data = json.load(f)

bible = []
for ref, text in bible_data.items():
    bible.append({
        "reference": ref,
        "text": text
    })

texts = [verse["text"] for verse in bible]

# ===============================
# LOAD MODEL + CREATE INDEX
# ===============================

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Creating embeddings (first time may take a few minutes)...")
embeddings = model.encode(texts, show_progress_bar=True)

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings))

print("\nBible AI Server Ready on port 5000\n")

# ===============================
# HEALTH CHECK (Optional but Useful)
# ===============================

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Bible AI is running"})

# ===============================
# ASK ENDPOINT
# ===============================

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"answer": "Invalid request."}), 400

        question = data.get("question", "").strip()

        if not question:
            return jsonify({"answer": "Please provide a question."})

        # Create embedding
        q_embedding = model.encode([question])

        # Search
        D, I = index.search(np.array(q_embedding), k=TOP_K)

        results = []

        for i in I[0]:
            verse = bible[i]
            results.append(f"{verse['reference']} - {verse['text']}")

        answer_text = "\n\n".join(results)

        return jsonify({"answer": answer_text})

    except Exception as e:
        return jsonify({"answer": f"Server error: {str(e)}"}), 500

# ===============================
# START SERVER
# ===============================

