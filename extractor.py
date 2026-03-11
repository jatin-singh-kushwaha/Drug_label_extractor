import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import io
import os

def search_drug(drug_name):
    """Searches DailyMed for the given drug name and returns the first Set ID found."""
    url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name={drug_name}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        if data['data']:
            return data['data'][0]['setid']
    return None

def extract_from_html(setid):
    """Extracts text content from the DailyMed HTML label."""
    url = f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={setid}&view=all"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        # Get text
        text = soup.get_text(separator='\n')
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    return ""

def extract_from_pdf(setid):
    """Searches for a PDF link on the label page and extracts text if found."""
    # Note: DailyMed PDF links are often structured as:
    # https://dailymed.nlm.nih.gov/dailymed/downloadpdf.cfm?setid={setid}
    pdf_url = f"https://dailymed.nlm.nih.gov/dailymed/downloadpdf.cfm?setid={setid}"
    response = requests.get(pdf_url)
    
    if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    return ""

def main():
    drug_name = input("Enter the drug name to search: ")
    print(f"Searching for '{drug_name}'...")
    
    setid = search_drug(drug_name)
    if not setid:
        print(f"No results found for '{drug_name}'.")
        return

    print(f"Found product with Set ID: {setid}")
    
    content = f"DRUG LABEL CONTENT FOR: {drug_name.upper()}\n"
    content += "="*40 + "\n\n"

    print("Extracting text from HTML...")
    html_text = extract_from_html(setid)
    if html_text:
        content += "--- HTML CONTENT ---\n"
        content += html_text + "\n\n"

    print("Checking for PDF and extracting text...")
    pdf_text = extract_from_pdf(setid)
    if pdf_text:
        content += "--- PDF CONTENT ---\n"
        content += pdf_text + "\n\n"

    filename = f"{drug_name.replace(' ', '_').lower()}_label.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"\nExtraction complete! Saved to {filename}")

if __name__ == "__main__":
    main()
