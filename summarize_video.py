import os
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
openai = OpenAI(api_key=openai_api_key)

def extract_video_id(url):
    import re
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

# def get_transcript(video_url):
#     video_id = extract_video_id(video_url)
#     transcript = YouTubeTranscriptApi.get_transcript(video_id)
#     text = " ".join([t['text'] for t in transcript])
#     return text
def get_transcript(video_url):
    video_id = extract_video_id(video_url)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t['text'] for t in transcript])
        return text
    except Exception as e:
        print(f"❌ Failed to fetch transcript: {e}")
        return None
def summarize_text(text):
    response = openai.chat.completions.create (
        model = "gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You summarize YouTube video transcripts."},
            {"role": "user", "content": f"Summarize the following video transcript:\n\n{text}"}
        ],
        max_tokens=700,
        temperature=0.5
    )
    return response.choices[0].message.content

def save_to_pdf(transcript, summary, output_path="summary.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.multi_cell(0, 10, "=== Summary ===\n" + summary)
    pdf.add_page()
    pdf.multi_cell(0, 10, "=== Transcript ===\n" + transcript)

    pdf.output(output_path)

def main():
    video_url = input("Enter YouTube video URL: ")
    print("Fetching transcript...")
    transcript = get_transcript(video_url)

    print("Summarizing with ChatGPT...")
    summary = summarize_text(transcript)

    print("Saving to PDF...")
    save_to_pdf(transcript, summary)
    print("✅ PDF saved as summary.pdf")

if __name__ == "__main__":
    main()
