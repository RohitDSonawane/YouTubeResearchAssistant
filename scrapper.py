import os
import requests
from bs4 import BeautifulSoup
import re

LINKS_FILE = "links.txt"
OUTPUT_FOLDER = "Article"

# --- Store logs inside logs/ folder ---
LOGS_FOLDER = "logs"
os.makedirs(LOGS_FOLDER, exist_ok=True)
LOG_FILE = os.path.join(LOGS_FOLDER, "scraped.log")

def clean_filename(name):
    """Remove invalid filename characters."""
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

def already_scraped(url):
    """Check if URL is already in log file."""
    if not os.path.exists(LOG_FILE):
        return False
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return url.strip() in [line.strip() for line in f]

def log_scraped(url):
    """Add URL to log file."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(url.strip() + "\n")

def scrape_article(url):
    """Scrape title and main text from a webpage."""
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return None, None

    soup = BeautifulSoup(response.text, "html.parser")

    # Title
    header_tag = soup.find("h1")
    title = header_tag.get_text(strip=True) if header_tag else (soup.title.string.strip() if soup.title else "Untitled")

    # Remove unwanted tags
    for tag in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()

    # Extract paragraphs
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    article_text = "\n".join(paragraphs)

    return title, article_text if article_text.strip() else None

def scrape_links():
    """Scrape all links from links.txt."""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    for link in links:
        if already_scraped(link):
            print(f"⏩ Skipping already scraped: {link}")
            continue

        print(f"🔍 Scraping: {link}")
        title, content = scrape_article(link)
        if content:
            safe_title = clean_filename(title)
            file_path = os.path.join(OUTPUT_FOLDER, f"{safe_title}.txt")
            with open(file_path, "w", encoding="utf-8") as out:
                out.write(content)
            log_scraped(link)
            print(f"✅ Saved: {file_path}")
        else:
            print(f"⚠ No content found for {link}")

if __name__ == "__main__":
    scrape_links()
