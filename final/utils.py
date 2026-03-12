import re

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

def clean_text(text):
    if not text or text == "Not found":
        return text
    
    # Remove common PDF/Scraping artifacts
    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.I)
    text = re.sub(r'Reference ID: \d+', '', text, flags=re.I)
    
    # Normalize bullet points and list markers
    text = re.sub(r'^[ \t]*[\u2022\u00b7\u25cf\u25cb.-][ \t]+', '- ', text, flags=re.M)
    
    # Remove excessive vertical whitespace while preserving paragraph breaks
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove excessive horizontal whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Standardize dashes and quotes
    text = text.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-')
    text = text.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
    
    return text.strip()
