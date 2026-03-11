import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import io
import os
import sys
import time
import random

def get_session():
    session = requests.Session()
    # A more complete set of modern browser headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
    })
    return session

def search_drugs_com(session, drug_name):
    """Searches drugs.com for the drug name."""
    # Try direct URL first
    direct_url = f"https://www.drugs.com/{drug_name.lower().replace(' ', '-')}.html"
    
    try:
        # Add a small random delay to seem less like a bot
        time.sleep(random.uniform(1.0, 2.0))
        response = session.get(direct_url, timeout=10)
        if response.status_code == 200:
            return direct_url
    except:
        pass

    # If direct fails, try search
    search_url = f"https://www.drugs.com/search.php?searchterm={drug_name}"
    try:
        time.sleep(random.uniform(1.0, 2.0))
        response = session.get(search_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            result = soup.find('div', class_='ddc-media-list')
            if result:
                link = result.find('a')
                if link and 'href' in link.attrs:
                    url = link['href']
                    if not url.startswith('http'):
                        url = 'https://www.drugs.com' + url
                    return url
    except:
        pass
    
    return direct_url

def extract_content(session, url):
    """Extracts HTML text and looks for PDF links."""
    try:
        time.sleep(random.uniform(1.5, 3.0))
        response = session.get(url, timeout=15)
        if response.status_code != 200:
            return f"Failed to retrieve page: {url} (Status Code: {response.status_code})", [], []
    except Exception as e:
        return f"Error accessing page: {str(e)}", [], []

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract main content
    main_content = soup.find('div', class_='contentBox') or soup.find('div', id='content') or soup.find('main')
    
    if main_content:
        content_copy = BeautifulSoup(str(main_content), 'html.parser')
        for tag in content_copy(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()
        text = content_copy.get_text(separator='\n')
    else:
        text = soup.get_text(separator='\n')

    lines = (line.strip() for line in text.splitlines())
    text = '\n'.join(line for line in lines if line)

    pdf_links = []
    pro_links = []
    
    # More robust PDF and Professional link finding
    for link in soup.find_all('a', href=True):
        href = link['href']
        link_text = link.get_text().lower()
        
        if href.lower().endswith('.pdf') or 'pdf' in link_text:
            if not href.startswith('http'):
                href = 'https://www.drugs.com' + ('' if href.startswith('/') else '/') + href
            pdf_links.append(href)
        
        # Professional/FDA pages are the goldmine for PDFs
        if any(keyword in link_text for keyword in ['professional', 'fda', 'prescribing information']):
            if not href.startswith('http'):
                href = 'https://www.drugs.com' + ('' if href.startswith('/') else '/') + href
            pro_links.append(href)

    return text, list(set(pdf_links)), list(set(pro_links))

def extract_pdf_text(session, pdf_url):
    """Downloads a PDF and extracts its text."""
    try:
        time.sleep(random.uniform(1.0, 2.0))
        response = session.get(pdf_url, timeout=20)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/pdf' in content_type or pdf_url.lower().endswith('.pdf'):
                pdf_file = io.BytesIO(response.content)
                reader = PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
    except Exception as e:
        return f"Error extracting PDF from {pdf_url}: {str(e)}"
    return ""

def main():
    drug_name = input("Enter the drug name (e.g., Descovy): ")
    print(f"Searching drugs.com for '{drug_name}'...")
    
    session = get_session()
    url = search_drugs_com(session, drug_name)
    print(f"Accessing: {url}")
    
    html_text, pdf_links, pro_links = extract_content(session, url)
    
    if "Status Code: 403" in html_text:
        print("Warning: Access was blocked (403 Forbidden).")
        print("Trying an alternative entry point...")
        # Try appending '/pro' directly
        alt_url = url.replace('.html', '/pro')
        if not alt_url.endswith('/pro'): alt_url += '/pro'
        html_text_alt, pdf_links_alt, _ = extract_content(session, alt_url)
        if "Status Code: 403" not in html_text_alt:
            print("Alternative successful!")
            html_text = html_text_alt
            pdf_links = pdf_links_alt
            url = alt_url

    content = f"DRUG: {drug_name.upper()}\n"
    content += f"SOURCE: {url}\n"
    content += "="*50 + "\n\n"
    content += "--- HTML CONTENT ---\n"
    content += html_text + "\n\n"

    # If no PDF links found, try top professional links
    if not pdf_links and pro_links:
        print(f"Checking {len(pro_links)} Professional pages for PDFs...")
        for pro_url in pro_links[:3]:
            print(f"Checking: {pro_url}")
            _, pro_pdfs, _ = extract_content(session, pro_url)
            pdf_links.extend(pro_pdfs)
            if pdf_links: break

    pdf_links = list(set(pdf_links))
    if pdf_links:
        print(f"Found {len(pdf_links)} PDF link(s). Extracting...")
        for pdf_url in pdf_links:
            pdf_text = extract_pdf_text(session, pdf_url)
            if pdf_text and len(pdf_text.strip()) > 100:
                content += f"--- PDF CONTENT FROM {pdf_url} ---\n"
                content += pdf_text + "\n\n"
                print(f"Successfully extracted: {pdf_url}")

    filename = f"drugs_com_{drug_name.replace(' ', '_').lower()}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"\nExtraction complete! Saved to {filename}")

if __name__ == "__main__":
    main()
