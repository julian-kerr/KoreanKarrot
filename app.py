import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session, redirect
from krdict import lookup_word
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join("db", "app.db")

app = Flask(__name__)

app.secret_key = "dev-secret-change-later"

def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_users_table():
    conn = db_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def init_saved_words_table():
    conn = db_conn()

    conn.execute("""
                 CREATE TABLE IF NOT EXISTS saved_words (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                 word TEXT NOT NULL,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

    conn.commit()
    conn.close()


init_users_table()
init_saved_words_table()


@app.post("/save-word")
def save_word():
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Login Required"}), 401
    
    word = request.form.get("word", "").strip()

    if not word:
        return jsonify({"ok": False, "error": "No word provided"}), 400
    
    conn = db_conn()

    existing = conn.execute(
        """
        SELECT id
        FROM saved_words
        WHERE user_id = ? AND word = ?
        """,
        (session["user_id"], word)
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({
            "ok": True,
            "already_saved": True
        })

    conn.execute(
        "INSERT INTO saved_words (user_id, word) VALUES (?, ?)",
        (session["user_id"], word)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "already_saved": False
    })

@app.post("/delete-word")
def delete_word():
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Login Required"}), 401

    word_id = request.form.get("id", "").strip()

    conn = db_conn()
    conn.execute(
        "DELETE FROM saved_words WHERE id = ? AND user_id = ?",
        (word_id, session["user_id"])
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})

@app.get("/my-words")
def my_words():
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Login required"}), 401
    
    conn = db_conn()

    rows = conn.execute("""
                    SELECT id, word, created_at
                    FROM saved_words
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    """, (session["user_id"], )).fetchall()
    conn.close()

    return jsonify({
        "ok": True,
        "words": [
            {
                "id": row["id"],
                "word": row["word"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    })


@app.get("/")
def home():
    return render_template("index.html", username=session.get("username"))

@app.get("/search")
def search():
    
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    conn = db_conn()

    # FTS (fast) — may return fewer results for short queries
    try:
        rows = conn.execute("""
            SELECT v.title, v.youtube_id, f.start, f.text
            FROM captions_fts f
            JOIN videos v ON v.id = f.video_id
            WHERE captions_fts MATCH ?
            LIMIT 30
        """, (q,)).fetchall()
    except Exception:
        rows = []

    # Fallback: LIKE (slower but super reliable for Korean substrings)
    if not rows:
        rows = conn.execute("""
            SELECT v.title, v.youtube_id, v.source, c.start, c.text
            FROM captions c
            JOIN videos v ON v.id = c.video_id
            WHERE c.text LIKE ?
            LIMIT 3000
        """, (f"%{q}%",)).fetchall()

    conn.close()

    return jsonify([{
        "title": r["title"],
        "youtube_id": r["youtube_id"],
        "source": r["source"],
        "start": float(r["start"]),
        "text": r["text"]
    } for r in rows])

@app.get("/dictionary")
def dictionary():
    word = request.args.get("word", "").strip()

    if not word:
        return jsonify({"error": "No word provided"}), 400

    result = lookup_word(word)

    if result is None:
        return jsonify({"found": False})

    return jsonify({
        "found": True,
        "entry": result
    })

@app.post("/signup")
def signup():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    
    if not username or not password:
        return "Username and password required.", 400
    
    password_hash = generate_password_hash(password)
    conn = None

    try:
        conn = db_conn()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )

        conn.commit()

        session["user_id"] = cur.lastrowid
        session["username"] = username

        return redirect("/")
    
    except sqlite3.IntegrityError:
        return "Username already exists", 400

    finally:
        if conn:
            conn.close()

@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    conn = db_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/")
    return "Invalid username or password", 401

@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    # Use port 5000 (default). If you get a port-in-use error, change to 5001.
    app.run(debug=True, host="127.0.0.1", port=5001)