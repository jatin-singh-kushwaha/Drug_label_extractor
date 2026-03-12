import sys
import json
from extractors import USExtractor, UKExtractor, JapanExtractor, EUExtractor, AustraliaExtractor
from parser import DrugParser

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
        'EU': EUExtractor(),
        'AU': AustraliaExtractor(),
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
