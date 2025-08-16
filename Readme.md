Here's a clear and developer-friendly **README.md** for your project:

---

# 📑 YouTube Research Assistant

This project automates the workflow of **finding YouTube videos related to an article, extracting transcripts, and saving metadata** into structured JSON files.

It combines:

* **Scraping** (`scrapper.py`)
* **Article parsing** (TXT, PDF, DOCX)
* **Keyword generation** via OpenRouter GPT API
* **YouTube search & transcripts** (via `yt_dlp` + `youtube_transcript_api`)
* **Logging system** (avoid re-processing the same videos)

---

## 🚀 Features

* Load research articles (`.txt`, `.pdf`, `.docx`)
* Extract a **smart keyword phrase** using OpenRouter GPT
* Search YouTube for **top 3 relevant videos**
* Fetch transcripts:

  * First try `youtube_transcript_api`
  * Fallback to `yt_dlp` subtitles
  * Auto-translate to English if needed
* Save results as JSON (`results/<article>.json`)
* Maintain logs:

  * Processed videos → `logs/videos.log`
  * Scraper logs → `logs/scraper.log`

---

## 📂 Project Structure

```
.
├── Article/              # Input folder (research articles)
│   └── example.pdf
├── results/              # Output folder (JSON metadata & transcripts)
├── logs/                 # Logging (processed videos & scraper logs)
│   ├── videos.log
│   └── scraper.log
├── scrapper.py           # Custom scraper script (provided separately)
├── main.py               # Main script (this file)
└── README.md             # Documentation
```

---

## ⚙️ Installation

1. Clone repo and install dependencies:

   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -r requirements.txt
   ```

2. Create `.env` file with your [OpenRouter](https://openrouter.ai/) API key:

   ```env
   OPENROUTER_API_KEY=your_api_key_here
   ```

3. Add at least **one article file** (`.txt`, `.pdf`, or `.docx`) in `Article/`.

---

## ▶️ Usage

Run the main script:

```bash
python main.py
```

Steps performed:

1. Runs the web scraper (`scrapper.py`)
2. Loads the first article from `Article/`
3. Extracts best YouTube search phrase
4. Fetches top videos & transcripts
5. Saves results to `results/<article>.json`

---

## 📜 Example Output (`results/example.json`)

```json
[
  {
    "title": "AI Research Breakthrough 2025",
    "url": "https://www.youtube.com/watch?v=abcd1234",
    "views": 120394,
    "published": "20250801",
    "duration": 600,
    "channel": "AI News",
    "transcript": "In this video, we explore the latest research..."
  }
]
```

---

## 📝 Logs

* `logs/videos.log` → Keeps track of already processed videos (avoids duplicates)
* `logs/scraper.log` → Handled internally by `scrapper.py`

---

## ⚠️ Notes

* If no `OPENROUTER_API_KEY` is found, it defaults to `"latest research update"` as the query.
* If no transcript is available, a placeholder message is saved.
* `scrapper.py` must be implemented with a function `scrape_links()` (imported in `main.py`).

---

## 📌 Requirements

* Python 3.8+
* Libraries:

  ```
  yt-dlp
  deep-translator
  youtube-transcript-api
  python-dotenv
  PyPDF2
  python-docx
  requests
  ```

---

Do you want me to also **add installation commands for ffmpeg** (needed for `yt-dlp` on some systems), or should I keep the README Python-only?
