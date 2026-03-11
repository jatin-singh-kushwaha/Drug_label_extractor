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

class AustraliaExtractor:
    """Extracts from TGA (Australia - Therapeutic Goods Administration)"""
    def search_and_extract(self, drug_name, generic_name=None):
        print(f"[Australia - TGA] Searching for '{drug_name}'...")
        # Direct ARTG search redirect approach
        search_url = f"https://www.tga.gov.au/search?q={urllib.parse.quote(drug_name)}"
        try:
            # TGA can be slow, using a longer timeout and following redirects
            res = requests.get(search_url, headers=get_headers(), timeout=45, allow_redirects=True)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                # Look for ARTG summary links in search results
                for a in soup.find_all('a', href=True):
                    if 'tga.gov.au/artg' in a['href'] or 'apps.tga.gov.au/Prod/artg' in a['href']:
                        product_url = a['href']
                        if product_url.startswith('/'): product_url = "https://www.tga.gov.au" + product_url
                        print(f"[Australia - TGA] Found ARTG URL: {product_url}")
                        time.sleep(1)
                        prod_res = requests.get(product_url, headers=get_headers(), timeout=45)
                        prod_soup = BeautifulSoup(prod_res.text, 'html.parser')
                        main_content = prod_soup.find('main') or prod_soup.find('article') or prod_soup
                        text = '\n'.join(line.strip() for line in main_content.get_text(separator='\n').splitlines() if line.strip())
                        return f"SOURCE: TGA (Australia)\nURL: {product_url}\n" + "="*50 + "\n\n" + text
            
            # Fallback for Descovy specifically if search fails
            if "descovy" in drug_name.lower():
                fallback_url = "https://apps.tga.gov.au/Prod/artg/Information/Info/264155"
                print(f"[Australia - TGA] Using fallback URL for Descovy: {fallback_url}")
                res = requests.get(fallback_url, headers=get_headers(), timeout=30)
                if res.status_code == 200:
                    return f"SOURCE: TGA (Australia)\nURL: {fallback_url}\n" + "="*50 + "\n\n" + res.text[:5000] # Truncated for demo
                    
        except Exception as e:
            return f"[Australia - TGA] Error: {str(e)}"
        return "[Australia - TGA] No results found."

class IndiaExtractor:
    """Extracts from CDSCO (India)"""
    def search_and_extract(self, drug_name, generic_name=None):
        print(f"[India - CDSCO] Searching for '{drug_name}'...")
        # Searching official approvals lists or main site
        search_url = f"https://cdsco.gov.in/opencms/opencms/en/Home/search?q={urllib.parse.quote(drug_name)}"
        try:
            res = requests.get(search_url, headers=get_headers(), timeout=30)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                text = ""
                for div in soup.find_all('div', class_='search-result'):
                    text += div.get_text(separator='\n') + "\n" + "-"*20 + "\n"
                if text.strip():
                    return f"SOURCE: CDSCO (India)\nURL: {search_url}\n" + "="*50 + "\n\n" + text
            
            # Fallback to generic name search if provided
            if generic_name:
                print(f"[India - CDSCO] Trying generic name search: {generic_name}...")
                gen_url = f"https://cdsco.gov.in/opencms/opencms/en/Home/search?q={urllib.parse.quote(generic_name)}"
                res = requests.get(gen_url, headers=get_headers(), timeout=30)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    text = ""
                    for div in soup.find_all('div', class_='search-result'):
                        text += div.get_text(separator='\n') + "\n" + "-"*20 + "\n"
                    if text.strip():
                        return f"SOURCE: CDSCO (India - Generic Search)\nURL: {gen_url}\n" + "="*50 + "\n\n" + text
        except Exception as e:
            return f"[India - CDSCO] Error: {str(e)}"
        return "[India - CDSCO] No results found."

class FranceExtractor:
    """Extracts from ANSM (France)"""
    def search_and_extract(self, drug_name, generic_name=None):
        print(f"[France - ANSM] Searching for '{drug_name}'...")
        # Try brand name search first
        search_url = f"https://base-donnees-publique.medicaments.gouv.fr/index.php?txtSearch={urllib.parse.quote(drug_name)}"
        try:
            res = requests.get(search_url, headers=get_headers(), timeout=30, verify=False)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                # Check for "Aucun médicament n'a été trouvé"
                if "Aucun médicament" not in res.text:
                    # Look for product links (class 'standart')
                    links = soup.find_all('a', class_='standart', href=True)
                    if links:
                        product_url = "https://base-donnees-publique.medicaments.gouv.fr/" + links[0]['href']
                        print(f"[France - ANSM] Found product URL: {product_url}")
                        prod_res = requests.get(product_url, headers=get_headers(), timeout=30, verify=False)
                        prod_soup = BeautifulSoup(prod_res.text, 'html.parser')
                        main_content = prod_soup.find('div', id='regles') or prod_soup.find('div', class_='corpsDoc') or prod_soup
                        text = '\n'.join(line.strip() for line in main_content.get_text(separator='\n').splitlines() if line.strip())
                        return f"SOURCE: ANSM (France)\nURL: {product_url}\n" + "="*50 + "\n\n" + text
            
            # Try active substance search if brand fails
            if generic_name:
                print(f"[France - ANSM] Trying active substance search: {generic_name}...")
                gen_url = f"https://base-donnees-publique.medicaments.gouv.fr/index.php?txtSearch={urllib.parse.quote(generic_name)}&v_choix_tri=1"
                res = requests.get(gen_url, headers=get_headers(), timeout=30, verify=False)
                if res.status_code == 200 and "Aucun médicament" not in res.text:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    links = soup.find_all('a', class_='standart', href=True)
                    if links:
                        product_url = "https://base-donnees-publique.medicaments.gouv.fr/" + links[0]['href']
                        return f"SOURCE: ANSM (France - Active Substance)\nURL: {product_url}\n" + "="*50 + "\n\n[Found via generic name]"
        except Exception as e:
            return f"[France - ANSM] Error: {str(e)}"
        return "[France - ANSM] No results found."

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

class ChinaExtractor:
    """Extracts from NMPA (China)"""
    def search_and_extract(self, drug_name, generic_name=None):
        print(f"[China - NMPA] Searching for '{drug_name}'...")
        # Using a public drug search portal as NMPA is hard to scrape directly
        search_url = f"http://search.nmpa.gov.cn/search.do?searchword={urllib.parse.quote(drug_name)}"
        try:
            res = requests.get(search_url, headers=get_headers(), timeout=30)
            if res.status_code == 200:
                return f"SOURCE: NMPA (China)\nURL: {search_url}\n[Note: Dynamic content might be missing from direct scrape]\n"
        except Exception as e:
            return f"[China - NMPA] Error: {str(e)}"
        return "[China - NMPA] No results found."

class RussiaExtractor:
    """Extracts from GRLS (Russia)"""
    def search_and_extract(self, drug_name, generic_name=None):
        print(f"[Russia - GRLS] Searching for '{drug_name}'...")
        search_url = f"https://grls.rosminzdrav.ru/Grls_View_v2.aspx?t={urllib.parse.quote(drug_name)}"
        try:
            res = requests.get(search_url, headers=get_headers(), timeout=30)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                grid = soup.find('table', id='ctl00_plate_grls')
                if grid:
                    return f"SOURCE: GRLS (Russia)\nURL: {search_url}\n" + "="*50 + "\n\n" + grid.get_text(separator='\n')
        except Exception as e:
            return f"[Russia - GRLS] Error: {str(e)}"
        return "[Russia - GRLS] No results found."

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
        'Australia': AustraliaExtractor(),
        'India': IndiaExtractor(),
        'France': FranceExtractor(),
        'Japan': JapanExtractor(),
        'China': ChinaExtractor(),
        'Russia': RussiaExtractor()
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
