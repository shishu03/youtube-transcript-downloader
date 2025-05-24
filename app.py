from flask import Flask, render_template, request, send_file
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import Playlist, YouTube
import os
import re
import requests
import textwrap
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_ENV', 'development') == 'development'

# Error handler for 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

def is_playlist(url):
    return 'playlist' in url

def extract_video_ids_from_playlist(url):
    try:
        pl = Playlist(url)
        return pl.video_urls
    except Exception:
        return []

def extract_video_id(url):
    # Accepts full YouTube URL or just video ID
    patterns = [
        r"(?:v=|youtu.be/|embed/)([\w-]{11})",
        r"^([\w-]{11})$"
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None

def parse_input_urls(url_inputs):
    video_urls = []
    for raw in url_inputs:
        val = raw.strip()
        if not val:
            continue
        # Only allow comma or space as delimiters
        if re.search(r";|\n", val):
            return None, 'Only comma or space is allowed as a delimiter between video URLs.'
        # Split by comma or space
        parts = re.split(r",| ", val)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if is_playlist(part):
                video_urls.extend(extract_video_ids_from_playlist(part))
            else:
                video_urls.append(part)
    return video_urls, None

def get_video_title(vid):
    # Try pytube first
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={vid}")
        return yt.title
    except Exception as e:
        print(f"pytube failed for {vid}: {e}")
    # Fallback to oEmbed
    try:
        resp = requests.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json")
        if resp.status_code == 200:
            return resp.json().get('title')
    except Exception as e:
        print(f"oEmbed failed for {vid}: {e}")
    return None

def save_transcripts(video_urls):
    os.makedirs("transcripts", exist_ok=True)
    files = []
    for url in video_urls:
        vid = extract_video_id(url)
        if not vid:
            continue
        try:
            transcript = YouTubeTranscriptApi.get_transcript(vid)
            # Get video title for filename and header
            title = get_video_title(vid)
            if title:
                safe_title = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_')
                filename = f"{safe_title}.txt"
            else:
                filename = f"{vid}.txt"
                title = vid
            path = f"transcripts/{filename}"
            # Combine transcript text, remove timestamps/metadata
            text = ' '.join([line['text'] for line in transcript if 'text' in line])
            # Wrap text to 180 characters per line (about 30-40 words)
            wrapped = textwrap.fill(text, width=180)
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{title}\n{'='*len(title)}\n\n")
                f.write(wrapped)
            files.append(filename)
        except Exception as e:
            print(f"Failed to get transcript for {vid}: {e}")
            continue
    return files

@app.route("/", methods=["GET", "POST"])
def index():
    files = []
    error = None
    if request.method == "POST":
        url_inputs = request.form.getlist("urls")
        video_urls, error = parse_input_urls(url_inputs)
        if error:
            return render_template("index.html", files=files, error=error)
        files = save_transcripts(video_urls)
    return render_template("index.html", files=files, error=error)

@app.route("/download/<filename>")
def download(filename):
    return send_file(f"transcripts/{filename}", as_attachment=True)

if __name__ == "__main__":
    # Set development environment for local runs
    os.environ['FLASK_ENV'] = 'development'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
