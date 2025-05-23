# YouTube Transcript Downloader

This is a local Flask web app that lets you input one or more YouTube video links (or a playlist URL), and downloads their transcripts in `.txt` format. Each transcript is saved with the corresponding video title as the filename.

## ✨ Features

- Input multiple YouTube video links or playlist URL.
- Transcripts are cleaned and formatted.
- Output saved as `.txt` files using video titles.

## 📦 Setup Instructions

### 1. Clone the repository
git clone https://github.com/your-username/youtube-transcript-downloader.git
cd youtube-transcript-downloader

### 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # For Linux/macOS
venv\Scripts\activate     # For Windows


### 3. Install dependencies
pip install -r requirements.txt
If requirements.txt doesn't exist, generate it with:
pip freeze > requirements.txt

### 4. Set up environment variables
Create a .env file in the project root:
OPENAI_API_KEY=your_openai_api_key_here
(For now, OpenAI key isn't used but will be needed when summary feature is added.)

### 5. Run the Flask app
python app.py
Open http://127.0.0.1:5000 in your browser.

📝 Notes
Output .txt files will be saved in transcript directory.Additionally can be downloaded via hyperlink

Transcripts are formatted for better readability.

🔒 Do not commit .env
Be sure .env is in .gitignore.


🔧 To Do
 Add transcript summarization using OpenAI.

 Export summaries as PDF.

 Improve styling.

 # Additionally there is a standalone script download-transcript.py that can be used directly to download the transcript
