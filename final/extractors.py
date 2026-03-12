import requests
import urllib.parse
import time
import io
from bs4 import BeautifulSoup
from pypdf import PdfReader
from utils import get_headers

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
        for i in range(1, 4):
            page_num = f"{i:04d}"
            search_url = f"https://www.pmda.go.jp/english/review-services/reviews/approved-information/drugs/{page_num}.html"
            try:
                res = requests.get(search_url, headers=get_headers(), timeout=30)
                if res.status_code != 200: continue
                
                soup = BeautifulSoup(res.text, 'html.parser')
                pdf_url = None
                
                for tr in soup.find_all('tr'):
                    cells = tr.find_all('td')
                    if not cells: continue
                    
                    brand_name_cell = cells[0].get_text().strip()
                    generic_name_cell = cells[1].get_text().strip() if len(cells) > 1 else ""
                    
                    if drug_name.lower() == brand_name_cell.lower() or f" {drug_name.lower()} " in f" {brand_name_cell.lower()} ":
                        if len(cells) >= 4:
                            a_tag = cells[3].find('a', href=True)
                            if a_tag and '.pdf' in a_tag['href'].lower():
                                pdf_url = a_tag['href']
                                break

                    if not pdf_url and generic_name:
                        query_comps = sorted([c.strip().lower() for c in generic_name.replace('/', ' ').replace(',', ' ').split() if len(c) > 3])
                        cell_comps = sorted([c.strip().lower() for c in generic_name_cell.replace('/', ' ').replace(',', ' ').split() if len(c) > 3])
                        
                        if query_comps and query_comps == cell_comps:
                            if len(cells) >= 4:
                                a_tag = cells[3].find('a', href=True)
                                if a_tag and '.pdf' in a_tag['href'].lower():
                                    pdf_url = a_tag['href']
                                    break
                
                if pdf_url:
                    if pdf_url.startswith('/'):
                        pdf_url = "https://www.pmda.go.jp" + pdf_url
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
                print(f"[Japan - PMDA] Page {page_num} error: {str(e)}")
                continue
                
        return "[Japan - PMDA] No results found or PDF could not be parsed."

class EUExtractor:
    """Extracts from EMA (Europe - European Medicines Agency)"""
    def search_and_extract(self, drug_name, generic_name=None):
        def slugify(text):
            if not text: return ""
            # Basic slugification for EMA URLs
            return text.lower().strip().replace(' ', '-').replace('/', '-')

        candidates = [slugify(drug_name)]
        if generic_name:
            # If multi-component, EMA often uses the first one or a combined slug
            main_generic = generic_name.split()[0] if generic_name.split() else ""
            if main_generic and main_generic.lower() != drug_name.lower():
                candidates.append(slugify(main_generic))
            candidates.append(slugify(generic_name))

        print(f"[EU - EMA] Searching for '{drug_name}' via candidate EPAR URLs...")
        
        for slug in candidates:
            if not slug: continue
            product_url = f"https://www.ema.europa.eu/en/medicines/human/EPAR/{slug}"
            try:
                print(f"[EU - EMA] Trying URL: {product_url}")
                res = requests.get(product_url, headers=get_headers(), timeout=30)
                if res.status_code != 200:
                    continue
                
                print(f"[EU - EMA] Found product page!")
                prod_soup = BeautifulSoup(res.text, 'html.parser')
                
                # Find the English PDF Product Information link
                pdf_url = None
                # EMA usually has a list of links with language codes
                for a in prod_soup.find_all('a', href=True):
                    href = a['href']
                    if 'product-information' in href.lower() and '_en.pdf' in href.lower():
                        pdf_url = href
                        break
                
                if not pdf_url:
                    # Fallback: Look for any PDF link that contains "product-information"
                    for a in prod_soup.find_all('a', href=True):
                        if 'product-information' in a['href'].lower() and a['href'].endswith('.pdf'):
                            pdf_url = a['href']
                            break
                
                if pdf_url:
                    if pdf_url.startswith('/'):
                        pdf_url = "https://www.ema.europa.eu" + pdf_url
                    print(f"[EU - EMA] Found Product Information PDF: {pdf_url}")
                    time.sleep(1)
                    pdf_res = requests.get(pdf_url, headers=get_headers(), timeout=45)
                    if pdf_res.status_code == 200:
                        pdf_file = io.BytesIO(pdf_res.content)
                        reader = PdfReader(pdf_file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        
                        if text.strip():
                            return f"SOURCE: EMA (Europe)\nURL: {pdf_url}\n" + "="*50 + "\n\n" + text

            except Exception as e:
                print(f"[EU - EMA] Error trying {slug}: {str(e)}")
                continue

        return "[EU - EMA] No results found or PDF could not be parsed."

class AustraliaExtractor:
    """Extracts from TGA eBS (Australia - Therapeutic Goods Administration)"""
    def search_and_extract(self, drug_name, generic_name=None):
        print(f"[AU - TGA] Searching for '{drug_name}'...")
        session = requests.Session()
        session.headers.update(get_headers())
        
        # TGA eBS search URL for PI
        base_url = "https://www.ebs.tga.gov.au/ebs/picmi/picmirepository.nsf/PICMI?OpenForm"
        try:
            # 1. Search for the drug
            search_url = f"{base_url}&t=pi&q={urllib.parse.quote(drug_name)}"
            res = session.get(search_url, timeout=30)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                pdf_path = None
                # Find the first PDF link that looks like a PI link
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if 'pdf?OpenAgent&id=CP-' in href and '-PI-' in href:
                        pdf_path = href
                        break
                
                if pdf_path:
                    if pdf_path.startswith('/'):
                        pdf_url = "https://www.ebs.tga.gov.au" + pdf_path
                    else:
                        pdf_url = "https://www.ebs.tga.gov.au/ebs/picmi/picmirepository.nsf/" + pdf_path
                        
                    print(f"[AU - TGA] Found PI PDF candidate: {pdf_url}")
                    
                    # 2. To get the PDF, we must "accept" the license.
                    # This involves setting a specific cookie and adding a 'd' parameter.
                    licence_res = session.get(pdf_url, timeout=30)
                    if licence_res.status_code == 200 and b'%PDF-' not in licence_res.content[:10]:
                        # Extract remoteaddr from the license page
                        licence_soup = BeautifulSoup(licence_res.text, 'html.parser')
                        remote_addr_tag = licence_soup.find('input', id='remoteaddr')
                        remote_addr = remote_addr_tag['value'] if remote_addr_tag else "127.0.0.1"
                        
                        # Generate the cookie value: YYYYMMDD + remoteaddr (no dots)
                        import datetime
                        str_utc_date = datetime.datetime.utcnow().strftime("%Y%m%d")
                        str_cookie_value = str_utc_date + remote_addr.replace('.', '')
                        
                        # Set the cookie
                        session.cookies.set("PICMIIAccept", str_cookie_value, domain="www.ebs.tga.gov.au", path="/")
                        
                        # Use the final URL with the 'd' parameter
                        final_pdf_url = pdf_url + "&d=" + str_cookie_value
                        print(f"[AU - TGA] Fetching PDF with license bypass: {final_pdf_url}")
                        pdf_res = session.get(final_pdf_url, timeout=45)
                    else:
                        pdf_res = licence_res

                    if pdf_res.status_code == 200:
                        if b'%PDF-' not in pdf_res.content[:10]:
                            return f"[AU - TGA] Error: Received HTML instead of PDF. License bypass failed."
                            
                        pdf_file = io.BytesIO(pdf_res.content)
                        reader = PdfReader(pdf_file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        
                        if text.strip():
                            return f"SOURCE: TGA (Australia)\nURL: {pdf_url}\n" + "="*50 + "\n\n" + text

        except Exception as e:
            return f"[AU - TGA] Error: {str(e)}"
        return "[AU - TGA] No results found or PDF could not be parsed."
