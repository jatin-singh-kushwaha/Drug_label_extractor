import requests
from bs4 import BeautifulSoup
import json
import urllib.parse
import sys
import time
import random
import urllib3
import io
import re
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

class DrugParser:
    """Parses medicine text files into JSON fields"""
    @staticmethod
    def extract_sections(text, country):
        data = {
            "dosage": "Not found",
            "description": "Not found",
            "reaction": "Not found"
        }
        
        if country == 'us':
            # US FDA Label Sections
            # Avoid the Table of Contents by ensuring the match is NOT followed by tabs or subsection lists (\t)
            # Full sections usually have the number and title on their own line with no trailing tab.
            dosage_match = re.search(r'\n2\s+DOSAGE AND ADMINISTRATION\s*\n(?!\s*2\.\d)(.*?)(?=\n[3-9]\s+[A-Z\s]{5,}|\n1\d\s+[A-Z\s]{5,}|$)', text, re.S | re.I)
            desc_match = re.search(r'\n11\s+DESCRIPTION\s*\n(?!\s*11\.\d)(.*?)(?=\n12\s+[A-Z\s]{5,}|$)', text, re.S | re.I)
            reaction_match = re.search(r'\n6\s+ADVERSE REACTIONS\s*\n(?!\s*6\.\d)(.*?)(?=\n7\s+DRUG INTERACTIONS|\n[8-9]\s+[A-Z\s]{5,}|$)', text, re.S | re.I)
            
            # Fallback for Highlights section if Full Prescribing info match failed
            if not dosage_match:
                dosage_match = re.search(r'DOSAGE AND ADMINISTRATION\s*\n(.*?)(?=\n[A-Z\s]{10,}|$)', text, re.S | re.I)
            if not reaction_match:
                reaction_match = re.search(r'ADVERSE REACTIONS\s*\n(.*?)(?=\n[A-Z\s]{10,}|$)', text, re.S | re.I)
        
        elif country == 'uk':
            # UK SmPC Sections
            dosage_match = re.search(r'4\.2\s+Posology and method of administration(.*?)(?=\n4\.3|\n\d\s+[A-Z]|$)', text, re.S | re.I)
            desc_match = re.search(r'2\.\s+Qualitative and quantitative composition(.*?)(?=\n3\.|\n\d\s+[A-Z]|$)', text, re.S | re.I)
            reaction_match = re.search(r'4\.8\s+Undesirable effects(.*?)(?=\n4\.9|\n\d\s+[A-Z]|$)', text, re.S | re.I)
            
        elif country == 'japan':
            # Japan PMDA Report Sections
            dosage_match = re.search(r'Dosage and Administration\s*\n(.*?)(?=\n[A-Z][a-z]|$)', text, re.S)
            desc_match = re.search(r'Chemical Structure\s*\n(.*?)(?=\n\d\.|$)', text, re.S)
            # Find the Safety section within the review report
            reaction_match = re.search(r'Clinical Efficacy and Safety\s*\n(.*?)(?=\n\d\.|$)', text, re.S | re.I)
            if not reaction_match:
                reaction_match = re.search(r'Toxicity\s*\n(.*?)(?=\n\d\.|$)', text, re.S | re.I)

        if dosage_match: data["dosage"] = dosage_match.group(1).strip()
        if desc_match: data["description"] = desc_match.group(1).strip()
        if reaction_match: data["reaction"] = reaction_match.group(1).strip()
        
        return data

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
        # Search multiple pages of the PMDA drug list
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
                    
                    # 1. Precise Brand Name match (case-insensitive, whole word)
                    if drug_name.lower() == brand_name_cell.lower() or f" {drug_name.lower()} " in f" {brand_name_cell.lower()} ":
                        if len(cells) >= 4:
                            a_tag = cells[3].find('a', href=True)
                            if a_tag and '.pdf' in a_tag['href'].lower():
                                pdf_url = a_tag['href']
                                break

                    # 2. Strict Generic Name match
                    if not pdf_url and generic_name:
                        # Normalize generic name from query
                        query_comps = sorted([c.strip().lower() for c in generic_name.replace('/', ' ').replace(',', ' ').split() if len(c) > 3])
                        # Normalize generic name from cell
                        cell_comps = sorted([c.strip().lower() for c in generic_name_cell.replace('/', ' ').replace(',', ' ').split() if len(c) > 3])
                        
                        # Compare sets of components (order-independent)
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
        "remicade": "infliximab",
        "yescarta": "axicabtagene ciloleucel"
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
    
    all_extracted_data = {}

    for country, extractor in extractors.items():
        print(f"--- Processing {country} ---")
        result_text = extractor.search_and_extract(drug_name, generic_name)
        
        if result_text and "No results found" not in result_text and "Error:" not in result_text:
            base_filename = f"label_{country.lower()}_{drug_name.replace(' ', '_').lower()}"
            txt_filename = f"{base_filename}.txt"
            json_filename = f"{base_filename}.json"
            
            # Save Text File
            try:
                with open(txt_filename, 'w', encoding='utf-8') as f:
                    f.write(result_text)
                print(f"-> Success! Saved text to {txt_filename}")
            except Exception as e:
                print(f"-> Failed to save {txt_filename}: {str(e)}")
                continue

            # Parse and Save JSON File
            try:
                parsed_data = DrugParser.extract_sections(result_text, country.lower())
                parsed_data["medicine"] = drug_name.upper()
                parsed_data["source"] = country
                
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(parsed_data, f, indent=4)
                print(f"-> Success! Extracted fields saved to {json_filename}\n")
                
                all_extracted_data[country] = parsed_data
            except Exception as e:
                print(f"-> Failed to parse/save {json_filename}: {str(e)}\n")
        else:
            print(f"-> No data for {country}.\n")

    # Save a combined summary if any data was found
    if all_extracted_data:
        summary_filename = f"summary_{drug_name.replace(' ', '_').lower()}.json"
        with open(summary_filename, 'w', encoding='utf-8') as f:
            json.dump(all_extracted_data, f, indent=4)
        print(f"Global summary for {drug_name.upper()} saved to {summary_filename}")

if __name__ == '__main__':
    main()
