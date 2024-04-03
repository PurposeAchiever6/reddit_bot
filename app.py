from flask import Flask, request, jsonify, g, render_template, redirect, url_for
from praw import Reddit
from openai import OpenAI
import os
from dotenv import load_dotenv
import sqlite3
import time
import threading

app = Flask(__name__)

DATABASE = 'reddit.db'
monitoring_flag = threading.Event()  # Flag to control monitoring process

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def initialize_database():
    """
    Initializes the SQLite database.
    """
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                response TEXT NOT NULL
            )
        ''')
        db.commit()

def initialize_reddit():
    """
    Initializes the Reddit instance.
    """
    # Initialize Reddit instance using environment variables
    reddit = Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=True,
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD")
    )
    return reddit

def initialize_openai():
    """
    Initializes the OpenAI client.
    """
    # Initialize OpenAI client using environment variable
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/interactions')
def fetch_interactions():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM interactions ORDER BY id DESC")
        interactions = cursor.fetchall()
        return render_template('interactions.html', interactions=interactions)
    except Exception as e:
        return str(e), 500

@app.route('/monitor', methods=['POST'])
def monitor_subreddit():
    try:
        # Load environment variables from .env file
        load_dotenv()

        # Initialize Reddit instance
        reddit = initialize_reddit()

        # Initialize OpenAI client
        client = initialize_openai()

        # Retrieve subreddit name and keywords from request
        data = request.json
        subreddit_name = data['subreddit_name']
        keywords = data['keywords']

        # Set the monitoring flag to True
        monitoring_flag.set()

        # Start monitoring the subreddit
        search_and_reply(reddit, client, subreddit_name, keywords)

        return jsonify({"message": "Monitoring initiated successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    try:
        # Set the monitoring flag to False
        monitoring_flag.clear()
        return jsonify({"message": "Monitoring stopped successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def search_and_reply(reddit, client, subreddit_name, keywords):
    """
    Monitors the specified subreddit for posts containing keywords and replies to them.

    Args:
        reddit (praw.Reddit): An instance of the Reddit API.
        client (OpenAI): An instance of the OpenAI API.
        subreddit_name (str): The name of the subreddit to monitor.
        keywords (list): A list of keywords to search for in posts.
    """
    try:
        count = 1
        subreddit = reddit.subreddit(subreddit_name)
        replied_posts = set()  # To keep track of posts already replied to

        db = get_db()
        cursor = db.cursor()

        while monitoring_flag.is_set():
            # Fetch recent posts from the subreddit
            for submission in subreddit.new(limit=50):
                title = submission.title
                content = submission.selftext

                # Check if post contains any of the keywords
                if any(keyword in title.lower() or keyword in content.lower() for keyword in keywords):
                    if submission.id not in replied_posts:  # Check if post already replied to
                        if not is_post_replied(cursor, submission.id):  # Check if post already replied to (in database)
                            response = generate_response(client, title, content)
                            if response:
                                submission.reply(response)
                                log_interaction(cursor, submission.id, title, content, response)
                                print(count,"\n")
                                print(title,"\n")
                                print(content,"\n")
                                print(response,"\n")
                                print("_____________________________")
                                replied_posts.add(submission.id)
                                time.sleep(660)
                                count += 1

    except Exception as e:
        print(f"Error in search_and_reply: {e}")

def is_post_replied(cursor, post_id):
    """
    Checks if the given post ID has already been replied to.

    Args:
        cursor (sqlite3.Cursor): SQLite cursor object.
        post_id (str): The ID of the Reddit post.

    Returns:
        bool: True if the post has already been replied to, False otherwise.
    """
    cursor.execute("SELECT COUNT(*) FROM interactions WHERE post_id = ?", (post_id,))
    count = cursor.fetchone()[0]
    return count > 0

def generate_response(client, title, content):
    """
    Generates a response using OpenAI's GPT model.

    Args:
        client (OpenAI): An instance of the OpenAI API.
        title (str): The title of the Reddit post.
        content (str): The content of the Reddit post.

    Returns:
        str: The generated response.
    """
    try:
        # Construct prompt for GPT model
        prompt = f"Title: {title}\n\nContent: {content} "
        # Generate response using GPT model
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a reddit bot. Your job is to provide short and relevant replies to the reddit posts."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {e}")
        return None

def log_interaction(cursor, post_id, title, content, response):
    """
    Logs bot interactions to the database.

    Args:
        cursor (sqlite3.Cursor): SQLite cursor object.
        post_id (str): The ID of the Reddit post.
        title (str): The title of the Reddit post.
        content (str): The content of the Reddit post.
        response (str): The response generated by the bot.
    """
    cursor.execute('''INSERT INTO interactions (post_id, title, content, response)
                      VALUES (?, ?, ?, ?)''', (post_id, title, content, response))
    cursor.connection.commit()

@app.teardown_appcontext
def teardown_db(e=None):
    close_db()

if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
    