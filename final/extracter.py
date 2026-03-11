import requests
from bs4 import BeautifulSoup
import json
import urllib.parse
import sys
import time
import random
import urllib3
import io
from pypdf import PdfReader

# Disable SSL warnings for cleaner output
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

class USExtractor:
    """Extracts from DailyMed (USA - National Library of Medicine/FDA)"""
    def search_and_extract(self, drug_name, generic_name=None):
        print(f"[US - DailyMed] Searching for '{drug_name}'...")
        query = urllib.parse.quote(drug_name)
        url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name={query}"
        try:
            res = requests.get(url, headers=get_headers(), timeout=30)
            if res.status_code == 200:
                data = res.json()
                if data and 'data' in data and data['data']:
                    setid = data['data'][0]['setid']
                    title = data['data'][0]['title']
                    print(f"[US - DailyMed] Found: {title}")
                    
                    html_url = f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={setid}&view=all"
                    html_res = requests.get(html_url, headers=get_headers(), timeout=30)
                    soup = BeautifulSoup(html_res.text, 'html.parser')
                    for tag in soup(["script", "style", "nav", "footer"]): 
                        tag.decompose()
                    
                    text = '\n'.join(line.strip() for line in soup.get_text(separator='\n').splitlines() if line.strip())
                    return f"SOURCE: DailyMed (USA - FDA)\nURL: {html_url}\nPRODUCT: {title}\n" + "="*50 + "\n\n" + text
        except Exception as e:
            return f"[US - DailyMed] Error: {str(e)}"
        return "[US - DailyMed] No results found."

class UKExtractor:
    """Extracts from eMC (UK - electronic Medicines Compendium)"""
    def search_and_extract(self, drug_name, generic_name=None):
        print(f"[UK - eMC] Searching for '{drug_name}'...")
        search_url = f"https://www.medicines.org.uk/emc/search?q={urllib.parse.quote(drug_name)}"
        try:
            res = requests.get(search_url, headers=get_headers(), timeout=30)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                product_url = None
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/emc/product/' in href and ('smpc' in href.lower() or 'pil' in href.lower()):
                        product_url = "https://www.medicines.org.uk" + href
                        break
                
                if not product_url:
                    for a in soup.find_all('a', href=True):
                        if '/emc/product/' in a['href']:
                            product_url = "https://www.medicines.org.uk" + a['href']
                            if not product_url.endswith('/smpc'):
                                product_url += '/smpc'
                            break

                if product_url:
                    print(f"[UK - eMC] Found product URL: {product_url}")
                    time.sleep(1)
                    prod_res = requests.get(product_url, headers=get_headers(), timeout=30)
                    prod_soup = BeautifulSoup(prod_res.text, 'html.parser')
                    main_content = prod_soup.find('main') or prod_soup.find('div', class_='smpc-content') or prod_soup
                    for tag in main_content(["script", "style", "nav", "footer", "header"]): 
                        tag.decompose()
                    text = '\n'.join(line.strip() for line in main_content.get_text(separator='\n').splitlines() if line.strip())
                    return f"SOURCE: eMC (UK)\nURL: {product_url}\n" + "="*50 + "\n\n" + text
        except Exception as e:
            return f"[UK - eMC] Error: {str(e)}"
        return "[UK - eMC] No results found."



class JapanExtractor:
    """Extracts from PMDA (Japan) and parses English PDFs"""
    def search_and_extract(self, drug_name, generic_name=None):
        print(f"[Japan - PMDA] Searching for '{drug_name}'...")
        search_url = "https://www.pmda.go.jp/english/review-services/reviews/approved-information/drugs/0001.html"
        try:
            res = requests.get(search_url, headers=get_headers(), timeout=30)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                pdf_url = None
                
                # Search for the row containing the drug name or generic name
                for tr in soup.find_all('tr'):
                    cells = tr.find_all('td')
                    if not cells: continue
                    
                    row_text = tr.get_text().lower()
                    if drug_name.lower() in row_text or (generic_name and generic_name.split()[0].lower() in row_text):
                        # Look for English PDF link in the 4th column (index 3)
                        if len(cells) >= 4:
                            a_tag = cells[3].find('a', href=True)
                            if a_tag and '.pdf' in a_tag['href'].lower():
                                pdf_url = a_tag['href']
                                if pdf_url.startswith('/'):
                                    pdf_url = "https://www.pmda.go.jp" + pdf_url
                                break
                
                if pdf_url:
                    print(f"[Japan - PMDA] Found English PDF URL: {pdf_url}")
                    time.sleep(1)
                    pdf_res = requests.get(pdf_url, headers=get_headers(), timeout=45)
                    if pdf_res.status_code == 200:
                        pdf_file = io.BytesIO(pdf_res.content)
                        reader = PdfReader(pdf_file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        
                        if text.strip():
                            return f"SOURCE: PMDA (Japan)\nURL: {pdf_url}\n" + "="*50 + "\n\n" + text
                
        except Exception as e:
            return f"[Japan - PMDA] Error: {str(e)}"
        return "[Japan - PMDA] No results found or PDF could not be parsed."


def main():
    if len(sys.argv) > 1:
        drug_name = " ".join(sys.argv[1:])
    else:
        drug_name = input("Enter the drug name to search globally: ").strip()
        
    if not drug_name:
        print("No drug name provided.")
        return

    # Intelligent Generic Mapping (can be expanded)
    generic_mapping = {
        "descovy": "emtricitabine tenofovir alafenamide",
        "truvada": "emtricitabine tenofovir disoproxil",
        "biktarvy": "bictegravir emtricitabine tenofovir alafenamide",
        "tivicay": "dolutegravir",
        "genvoya": "elvitegravir cobicistat emtricitabine tenofovir alafenamide",
        "aspirin": "acetylsalicylic acid",
        "paracetamol": "acetaminophen",
        "humira": "adalimumab",
        "enbrel": "etanercept",
        "remicade": "infliximab"
    }
    generic_name = generic_mapping.get(drug_name.lower())
        
    print(f"Initiating global search for: {drug_name.upper()}")
    if generic_name:
        print(f"Generic components identified: {generic_name}\n")
    else:
        print("")
    
    extractors = {
        'US': USExtractor(),
        'UK': UKExtractor(),
        'Japan': JapanExtractor()
    }
    
    for country, extractor in extractors.items():
        print(f"--- Processing {country} ---")
        result = extractor.search_and_extract(drug_name, generic_name)
        
        if result and "No results found" not in result and "Error:" not in result:
            filename = f"label_{country.lower()}_{drug_name.replace(' ', '_').lower()}.txt"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"-> Success! Saved to {filename}\n")
            except Exception as e:
                print(f"-> Failed to save {filename}: {str(e)}\n")
        else:
            print(f"-> No data for {country}.\n")

if __name__ == '__main__':
    main()
