from flask import Flask, render_template, request, send_file, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import Playlist, YouTube
import os
import re
import requests
import textwrap
import tempfile
import time
from dotenv import load_dotenv
import traceback
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable
import sys

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['DEBUG'] = os.environ.get('FLASK_ENV', 'development') == 'development'

# Configure cleanup of old files
def cleanup_old_files():
    if os.environ.get('FLASK_ENV') == 'production':
        transcript_dir = os.path.join(tempfile.gettempdir(), 'transcripts')
        if os.path.exists(transcript_dir):
            for file in os.listdir(transcript_dir):
                file_path = os.path.join(transcript_dir, file)
                # Remove files older than 1 hour
                if os.path.isfile(file_path) and time.time() - os.path.getmtime(file_path) > 3600:
                    try:
                        os.remove(file_path)
                        print(f"Cleaned up old file: {file}")
                    except Exception as e:
                        print(f"Error cleaning up {file}: {e}")

# Configure cleanup
last_cleanup_time = 0
CLEANUP_INTERVAL = 3600  # Run cleanup every hour

@app.before_request
def before_request():
    global last_cleanup_time
    current_time = time.time()
    
    # Run cleanup if it's been more than CLEANUP_INTERVAL seconds
    if current_time - last_cleanup_time > CLEANUP_INTERVAL:
        cleanup_old_files()
        last_cleanup_time = current_time

# Error handler for 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    print('--- Internal Server Error ---')
    print(traceback.format_exc())
    return render_template('500.html', error=str(e)), 500

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
    # In production, use temp directory for transcripts
    if os.environ.get('FLASK_ENV') == 'production':
        transcript_dir = os.path.join(tempfile.gettempdir(), 'transcripts')
    else:
        transcript_dir = 'transcripts'
    
    os.makedirs(transcript_dir, exist_ok=True)
    files = []
    errors = []
    
    for url in video_urls:
        vid = extract_video_id(url)
        if not vid:
            errors.append(f"Invalid YouTube URL or video ID: {url}")
            continue
            
        try:
            # First get the video title to provide better error messages
            title = get_video_title(vid)
            video_info = f"'{title}' ({vid})" if title else f"video {vid}"
              
            # Get available transcripts
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(vid)
                
                # Try different methods to get transcript
                try:
                    # Try manual subtitles first (usually better quality)
                    print(f"Trying manual subtitles for {vid}")
                    transcript = transcript_list.find_manually_created_transcript().fetch()
                except Exception as e:
                    print(f"No manual transcript for {vid}: {str(e)}")
                    try:
                        # Try English auto-generated subtitles
                        print(f"Trying auto-generated English subtitles for {vid}")
                        transcript = transcript_list.find_generated_transcript(['en']).fetch()
                    except Exception as e:
                        print(f"No English auto-generated transcript for {vid}: {str(e)}")
                        # Try any available transcript
                        print(f"Trying any available transcript for {vid}")
                        available_transcripts = transcript_list.get_transcript_list()
                        if available_transcripts:
                            transcript = available_transcripts[0].fetch()
                        else:
                            raise Exception("No transcripts available")
            except Exception as e:
                # Final fallback: try direct transcript retrieval
                print(f"Trying direct transcript retrieval for {vid}")
                transcript = YouTubeTranscriptApi.get_transcript(vid)
            
            if title:
                safe_title = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_')
                filename = f"{safe_title}.txt"
            else:
                filename = f"{vid}.txt"
                title = vid
                
            path = os.path.join(transcript_dir, filename)
            # Combine transcript text, remove timestamps/metadata
            text = ' '.join([line['text'] for line in transcript if 'text' in line])
            # Wrap text to 180 characters per line (about 30-40 words)
            wrapped = textwrap.fill(text, width=180)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{title}\n{'='*len(title)}\n\n")
                f.write(wrapped)
            files.append(filename)
            
        except NoTranscriptFound:
            errors.append(f"No subtitles/transcript available for {video_info}")
        except TranscriptsDisabled:
            errors.append(f"Subtitles are disabled for {video_info}")
        except VideoUnavailable:
            errors.append(f"Video {video_info} is unavailable. It might be private or deleted.")
        except Exception as e:
            errors.append(f"Failed to process {video_info}: {str(e)}")
            
    return files, errors

def test_youtube_access():
    try:
        resp = requests.get('https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=json', timeout=10)
        print(f"[DIAG] YouTube oEmbed status: {resp.status_code}", file=sys.stderr)
        print(f"[DIAG] oEmbed response: {resp.text[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"[DIAG] YouTube oEmbed request failed: {e}", file=sys.stderr)

@app.route("/", methods=["GET", "POST"])
def index():
    test_youtube_access()
    files = []
    error = None
    errors = []
    if request.method == "POST":
        url_inputs = request.form.getlist("urls")
        video_urls, error = parse_input_urls(url_inputs)
        if error:
            return render_template("index.html", files=files, error=error, errors=errors)
        files, errors = save_transcripts(video_urls)
    return render_template("index.html", files=files, error=error, errors=errors)

@app.route("/download/<filename>")
def download(filename):
    # Get the appropriate transcript directory based on environment
    if os.environ.get('FLASK_ENV') == 'production':
        transcript_dir = os.path.join(tempfile.gettempdir(), 'transcripts')
    else:
        transcript_dir = 'transcripts'
        
    transcript_path = os.path.join(transcript_dir, filename)
    print(f"[DEBUG] Downloading from: {transcript_path}")
    
    if os.path.exists(transcript_path):
        return send_file(transcript_path, as_attachment=True)
    else:
        print(f"[ERROR] File not found: {transcript_path}")
        return "File not found", 404

if __name__ == "__main__":
    # Set development environment for local runs
    os.environ['FLASK_ENV'] = 'development'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
