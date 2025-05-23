from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from pytube import YouTube
import re

def extract_video_id(url):
    # Extract video ID from a YouTube URL
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    if "v" in query:
        return query.get("v", [None])[0]
    # Handle youtu.be short links
    if parsed_url.netloc.endswith("youtu.be"):
        return parsed_url.path.lstrip("/")
    return None

def get_video_title(video_id):
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        title = yt.title
        # Clean title for filename
        safe_title = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_')
        return safe_title or video_id
    except Exception:
        return video_id

def download_transcript(video_url, output_file=None):
    video_id = extract_video_id(video_url)
    if not video_id:
        print("❌ Could not extract video ID.")
        return

    try:
        print("📥 Fetching transcript...")
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = "\n".join([entry['text'] for entry in transcript])
        if not output_file:
            output_file = get_video_title(video_id) + ".txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"✅ Transcript saved to {output_file}")
    except Exception as e:
        print(f"❌ Error fetching transcript: {e}")

if __name__ == "__main__":
    video_url = input("Enter YouTube video URL: ").strip()
    download_transcript(video_url)

