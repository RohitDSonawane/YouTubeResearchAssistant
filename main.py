import os, glob, re, json, requests
import yt_dlp
from deep_translator import GoogleTranslator
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
except ImportError:
    from youtube_transcript_api import YouTubeTranscriptApi
    TranscriptsDisabled = Exception
    NoTranscriptFound = Exception
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
from scrapper import scrape_links

# ──────────────── ENV + CONST ────────────────
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "openai/gpt-oss-20b:free"
ARTICLE_FOLDER = "Article"
# --- MODIFICATION: Set up logs directory and file paths ---
LOGS_FOLDER = "logs"
VIDEO_LOG_FILE = os.path.join(LOGS_FOLDER, "videos.log")
SCRAPER_LOG_FILE = os.path.join(LOGS_FOLDER, "scraper.log") # Assuming this is used internally by scrapper.py


# ──────────────── HELPERS ────────────────
def parse_complex_transcript(transcript_data):
    """
    Parse complex JSON transcript format and extract simple English text.
    
    Follows the exact parsing logic:
    1. Load JSON data
    2. Access the events array
    3. Iterate through each object in events
    4. Extract utf8 text from segs array
    5. Concatenate all text segments
    """
    if isinstance(transcript_data, str):
        try:
            # Try to parse if it's a JSON string
            transcript_data = json.loads(transcript_data)
        except json.JSONDecodeError:
            # If it's not JSON, return as is
            return transcript_data
    
    if not isinstance(transcript_data, dict):
        return str(transcript_data)
    
    if 'events' in transcript_data:
        text_parts = []
        
        for event in transcript_data.get('events', []):
            if 'segs' in event:
                for seg in event['segs']:
                    if 'utf8' in seg and seg['utf8'].strip():
                        text_parts.append(seg['utf8'].strip())
        
        full_text = ' '.join(text_parts)
        full_text = re.sub(r'\s+', ' ', full_text)
        full_text = re.sub(r'\\n', ' ', full_text)
        
        return full_text.strip()
    
    elif isinstance(transcript_data, list):
        if transcript_data and isinstance(transcript_data[0], dict):
            if 'text' in transcript_data[0]:
                return ' '.join([item.get('text', '') for item in transcript_data])
            elif 'utf8' in transcript_data[0]:
                return ' '.join([item.get('utf8', '') for item in transcript_data])
    
    return str(transcript_data)


def load_article(file_path):
    """Load txt/pdf/docx article into string."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".pdf":
            return "\n".join([p.extract_text() for p in PdfReader(file_path).pages if p.extract_text()])
        elif ext == ".docx":
            return "\n".join([p.text for p in Document(file_path).paragraphs])
    except Exception as e:
        print(f"❌ Error loading article {file_path}: {e}")
    return ""


def extract_best_keyword_phrase(text):
    """Ask GPT (via OpenRouter) → best YouTube search phrase."""
    if not OPENROUTER_API_KEY:
        print("⚠ No OPENROUTER_API_KEY found, using default query")
        return "latest research update"
    
    prompt = f"""
From the text below, generate 5 candidate keyword phrases for YouTube search. 
Then choose ONE best phrase. 
Return ONLY that phrase.

TEXT:
{text}
"""
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": MODEL_NAME, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
        r = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        r.raise_for_status()
        phrase = r.json()["choices"][0]["message"]["content"].strip()
        return re.sub(r"\s+", " ", phrase)
    except Exception as e:
        print(f"⚠ Keyword extraction failed: {e}")
        return "latest research update"


def search_youtube(query, max_results=3):
    print(f"\n🔍 Searching YouTube for: \033[96m{query}\033[0m")
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            return info.get("entries", [])
    except Exception as e:
        print(f"❌ YouTube search error: {e}")
        return []


def get_transcript(video_id):
    """Transcript: API → yt_dlp fallback → translate if needed."""
    print(f"📝 Getting transcript for video: {video_id}")
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        print(f"✅ Got transcript via API for {video_id}")
        return transcript
    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"⚠ No transcript via API for {video_id}")
    except Exception as e:
        print(f"⚠ API error for transcript {video_id}: {e}")

    print("🔄 Trying yt_dlp subtitles...")
    try:
        opts = {"quiet": True, "skip_download": True, "writesubtitles": True,
                "writeautomaticsub": True, "subtitleslangs": ["en", "en-US", "en-GB"]}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            subs = info.get("subtitles") or info.get("automatic_captions")
            if not subs: 
                print(f"❌ No subtitles found for {video_id}")
                return [{"text": "Transcript not available", "start": 0, "duration": 0}]

            for lang in ["en", "en-US", "en-GB"]:
                if lang in subs:
                    print(f"✅ Found English subtitles ({lang}) for {video_id}")
                    srt = requests.get(subs[lang][0]["url"]).text
                    
                    if srt.strip().startswith('{'):
                        try:
                            json_data = json.loads(srt)
                            return json_data
                        except json.JSONDecodeError:
                            pass
                    
                    return [{"text": l, "start": 0, "duration": 0}
                            for l in srt.split("\n") if l and not l.strip().isdigit() and "-->" not in l]

            first_lang = next(iter(subs))
            print(f"🌍 Found {first_lang} subtitles, translating to English...")
            srt = requests.get(subs[first_lang][0]["url"]).text
            raw = "\n".join([l for l in srt.split("\n") if l and not l.strip().isdigit() and "-->" not in l])
            translated = GoogleTranslator(source="auto", target="en").translate(raw)
            return [{"text": t, "start": 0, "duration": 0} for t in translated.split("\n")]

    except Exception as e2:
        print(f"❌ yt_dlp fallback failed: {e2}")
        return [{"text": f"Transcript fetch failed: {e2}", "start": 0, "duration": 0}]


def log_video(url):
    # --- MODIFICATION: Create logs folder if it doesn't exist ---
    os.makedirs(LOGS_FOLDER, exist_ok=True)
    with open(VIDEO_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(url.strip() + "\n")


def already_logged(url):
    # --- MODIFICATION: Check in the correct log file location ---
    return os.path.exists(VIDEO_LOG_FILE) and url in open(VIDEO_LOG_FILE, "r", encoding="utf-8").read().splitlines()

# --- MODIFICATION: Pass log file path to scraper.py, if needed. Assuming scrape_links handles its own log path. ---
# For demonstration purposes, I'll update the main function to reflect the new log file path.
# The user's provided scrapper.py is not visible, so this is a best-effort modification.
def run_scraper_with_log():
    # Example of how you would call the scraper with the new log path
    # assuming scrape_links can take a log_file_path argument
    # scrape_links(log_file_path=SCRAPER_LOG_FILE)
    scrape_links()
    pass


# ──────────────── MAIN ────────────────
if __name__ == "__main__":
    try:
        print("🕵 Running web scraper...")
        # --- MODIFICATION: Call the function that handles logging for the scraper ---
        run_scraper_with_log()

        print("\n📂 Loading first article...")
        files = glob.glob(f"{ARTICLE_FOLDER}/*")
        if not files: raise FileNotFoundError("No files in Article/")
        article_text = load_article(files[0])

        print("\n🔍 Extracting best keyword phrase...")
        query = extract_best_keyword_phrase(article_text)
        print(f"✅ Using query: \033[92m{query}\033[0m")

        results = search_youtube(query, max_results=3)

        print("\n🎬 Top Videos:")
        videos = []
        for v in results:
            vid, title = v.get("id"), v.get("title", "Untitled")
            url = f"https://www.youtube.com/watch?v={vid}"

            if already_logged(url):
                print(f"⏩ Skipping logged: {title}")
                continue

            print(f"   ▶ \033[93m{title}\033[0m ({url})")
            transcript = get_transcript(vid)

            # Parse and clean transcript
            clean_transcript = parse_complex_transcript(transcript)
            
            meta = {
                "title": title, 
                "url": url, 
                "views": v.get("view_count"),
                "published": v.get("upload_date"), 
                "duration": v.get("duration"),
                "channel": v.get("channel"), 
                "transcript": clean_transcript
            }
            videos.append(meta)
            log_video(url)

        # --- Save results in results/ folder with article-based filename ---
        os.makedirs("results", exist_ok=True)

        # Use the article filename (without extension) as the result name
        article_name = os.path.splitext(os.path.basename(files[0]))[0]
        out_file = os.path.join("results", f"{article_name}.json")

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Results saved to \033[96m{out_file}\033[0m")


    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()