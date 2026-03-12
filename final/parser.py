import re
from utils import clean_text

class DrugParser:
    """Parses medicine text files into JSON fields"""
    
    @staticmethod
    def strip_toc(text, country):
        """Removes TOC to avoid parsing titles instead of content"""
        if country == 'us':
            # Look for the actual start of the Full Prescribing Information content
            # Often marked by the Boxed Warning or Section 1 after the TOC
            main_start = re.search(r'\nBOXED WARNING\s*\n\(What is this\?\)', text, re.I)
            if not main_start:
                # Fallback: Find the second occurrence of "1 INDICATIONS AND USAGE" 
                # (The first is usually in the TOC)
                matches = list(re.finditer(r'\n1\s+INDICATIONS AND USAGE', text, re.I))
                if len(matches) > 1:
                    return text[matches[-1].start():]
                elif matches:
                    return text[matches[0].start():]
            else:
                return text[main_start.start():]
        elif country == 'uk' or country == 'eu' or country == 'au':
            # UK, EU and AU SmPC/PI TOC usually ends at section 1
            main_start = re.search(r'\n1\.\s+NAME OF THE MEDICINAL PRODUCT|\n1\.\s+NAME OF THE MEDICINE', text, re.I)
            if main_start:
                return text[main_start.start():]
        elif country == 'japan':
            # Japan Review Reports often repeat titles in the Table of Contents
            # We look for the first major section after the TOC
            main_start = re.search(r'\n1\.\s+Origin or History', text, re.I)
            if main_start:
                return text[main_start.start():]
        return text

    @staticmethod
    def extract_sections(raw_text, country):
        text = DrugParser.strip_toc(raw_text, country)
        
        data = {
            "indications": "Not found",
            "dosage": "Not found",
            "contraindications": "Not found",
            "warnings": "Not found",
            "reaction": "Not found",
            "description": "Not found",
            "regulatory_text": "Not found"
        }
        
        def get_best_match(pattern, text):
            # We use re.findall/finditer but restrict it to only the first large block 
            # to avoid catching references at the end of the file
            matches = list(re.finditer(pattern, text, re.S | re.I))
            if not matches: return None
            # Return the first match that is significantly long (likely the real section)
            for m in matches:
                if len(m.group(1)) > 100:
                    return m
            return matches[0]

        if country == 'us':
            # US Patterns - Using strict numbering anchors
            indications_match = get_best_match(r'\n1\s+INDICATIONS AND USAGE\s*\n(.*?)(?=\n[2-9]\s+[A-Z\s]{5,}|$)', text)
            dosage_match = get_best_match(r'\n2\s+DOSAGE AND ADMINISTRATION\s*\n(.*?)(?=\n[3-9]\s+[A-Z\s]{5,}|$)', text)
            contra_match = get_best_match(r'\n4\s+CONTRAINDICATIONS\s*\n(.*?)(?=\n[5-9]\s+[A-Z\s]{5,}|$)', text)
            warnings_match = get_best_match(r'\n5\s+WARNINGS AND PRECAUTIONS\s*\n(.*?)(?=\n[6-9]\s+[A-Z\s]{5,}|$)', text)
            desc_match = get_best_match(r'\n11\s+DESCRIPTION\s*\n(.*?)(?=\n12\s+[A-Z\s]{5,}|$)', text)
            reaction_match = get_best_match(r'\n6\s+ADVERSE REACTIONS\s*\n(.*?)(?=\n[7-9]\s+[A-Z\s]{5,}|$)', text)
            
            # Revised Date is almost always near the top or bottom
            reg_match = re.search(r'(Revised:\s*\d+/\d+)', raw_text, re.I)
            
            # Boxed warning is usually at the very beginning of the full prescribing info
            boxed_warning = re.search(r'WARNING: [A-Z\s]{10,}.*?(?=\n1\s+INDICATIONS|$)', text, re.S | re.I)

            if indications_match: data["indications"] = clean_text(indications_match.group(1))
            if dosage_match: data["dosage"] = clean_text(dosage_match.group(1))
            if contra_match: data["contraindications"] = clean_text(contra_match.group(1))
            if warnings_match: 
                data["warnings"] = clean_text(warnings_match.group(1))
                if boxed_warning:
                    data["warnings"] = "BOXED WARNING:\n" + clean_text(boxed_warning.group(0)) + "\n\n" + data["warnings"]
            if desc_match: data["description"] = clean_text(desc_match.group(1))
            if reaction_match: data["reaction"] = clean_text(reaction_match.group(1))
            if reg_match: data["regulatory_text"] = reg_match.group(1).strip()

        elif country == 'uk':
            # UK Patterns - SmPC standard numbering (4.1 to 4.8)
            indications_match = re.search(r'\n4\.1\s+Therapeutic indications(.*?)(?=\n4\.2|$)', text, re.S | re.I)
            dosage_match = re.search(r'\n4\.2\s+Posology and method of administration(.*?)(?=\n4\.3|$)', text, re.S | re.I)
            contra_match = re.search(r'\n4\.3\s+Contraindications(.*?)(?=\n4\.4|$)', text, re.S | re.I)
            warnings_match = re.search(r'\n4\.4\s+Special warnings and precautions for use(.*?)(?=\n4\.5|$)', text, re.S | re.I)
            desc_match = re.search(r'\n2\.\s+Qualitative and quantitative composition(.*?)(?=\n3\.|$)', text, re.S | re.I)
            reaction_match = re.search(r'\n4\.8\s+Undesirable effects(.*?)(?=\n4\.9|$)', text, re.S | re.I)
            reg_match = re.search(r'\n10\.\s+DATE OF REVISION OF THE TEXT\s*\n(.*?)(?=\n|$)', text, re.S | re.I)

            if indications_match: data["indications"] = clean_text(indications_match.group(1))
            if dosage_match: data["dosage"] = clean_text(dosage_match.group(1))
            if contra_match: data["contraindications"] = clean_text(contra_match.group(1))
            if warnings_match: data["warnings"] = clean_text(warnings_match.group(1))
            if desc_match: data["description"] = clean_text(desc_match.group(1))
            if reaction_match: data["reaction"] = clean_text(reaction_match.group(1))
            if reg_match: data["regulatory_text"] = clean_text(reg_match.group(1))

        elif country == 'eu':
            # EU SmPCs follow the same standard numbering as the UK (EMA standard)
            indications_match = re.search(r'\n4\.1\s+Therapeutic indications(.*?)(?=\n4\.2|$)', text, re.S | re.I)
            dosage_match = re.search(r'\n4\.2\s+Posology and method of administration(.*?)(?=\n4\.3|$)', text, re.S | re.I)
            contra_match = re.search(r'\n4\.3\s+Contraindications(.*?)(?=\n4\.4|$)', text, re.S | re.I)
            warnings_match = re.search(r'\n4\.4\s+Special warnings and precautions for use(.*?)(?=\n4\.5|$)', text, re.S | re.I)
            desc_match = re.search(r'\n2\.\s+Qualitative and quantitative composition(.*?)(?=\n3\.|$)', text, re.S | re.I)
            reaction_match = re.search(r'\n4\.8\s+Undesirable effects(.*?)(?=\n4\.9|$)', text, re.S | re.I)
            
            # EMA Date of revision is usually at the end of Annex I
            reg_match = re.search(r'\n10\.\s+DATE OF REVISION OF THE TEXT\s*\n(.*?)(?=\n|$)', text, re.S | re.I)

            if indications_match: data["indications"] = clean_text(indications_match.group(1))
            if dosage_match: data["dosage"] = clean_text(dosage_match.group(1))
            if contra_match: data["contraindications"] = clean_text(contra_match.group(1))
            if warnings_match: data["warnings"] = clean_text(warnings_match.group(1))
            if desc_match: data["description"] = clean_text(desc_match.group(1))
            if reaction_match: data["reaction"] = clean_text(reaction_match.group(1))
            if reg_match: data["regulatory_text"] = clean_text(reg_match.group(1))

        elif country == 'au':
            # Australia TGA PI standard numbering (aligned with EMA)
            indications_match = re.search(r'\n4\.1\s+Therapeutic indications(.*?)(?=\n4\.2|$)', text, re.S | re.I)
            dosage_match = re.search(r'\n4\.2\s+Dose and method of administration(.*?)(?=\n4\.3|$)', text, re.S | re.I)
            contra_match = re.search(r'\n4\.3\s+Contraindications(.*?)(?=\n4\.4|$)', text, re.S | re.I)
            warnings_match = re.search(r'\n4\.4\s+Special warnings and precautions for use(.*?)(?=\n4\.5|$)', text, re.S | re.I)
            desc_match = re.search(r'\n2\.\s+Qualitative and quantitative composition(.*?)(?=\n3\.|$)', text, re.S | re.I)
            reaction_match = re.search(r'\n4\.8\s+Adverse effects(.*?)(?=\n4\.9|$)', text, re.S | re.I)
            reg_match = re.search(r'\n10\.\s+DATE OF REVISION(.*?)(?=\n|$)', text, re.S | re.I)

            if indications_match: data["indications"] = clean_text(indications_match.group(1))
            if dosage_match: data["dosage"] = clean_text(dosage_match.group(1))
            if contra_match: data["contraindications"] = clean_text(contra_match.group(1))
            if warnings_match: data["warnings"] = clean_text(warnings_match.group(1))
            if desc_match: data["description"] = clean_text(desc_match.group(1))
            if reaction_match: data["reaction"] = clean_text(reaction_match.group(1))
            if reg_match: data["regulatory_text"] = clean_text(reg_match.group(1))
            
        elif country == 'japan':
            # Japan PMDA - Using standard English headings
            indications_match = re.search(r'\nIndication\s*\n(.*?)(?=\nDosage and Administration|$)', text, re.S | re.I)
            dosage_match = re.search(r'\nDosage and Administration\s*\n(.*?)(?=\nApproval Conditions|\nReview Report|$)', text, re.S | re.I)
            warnings_match = re.search(r'Safety\s*\n(.*?)(?=\nClinical Efficacy|$)', text, re.S | re.I)
            desc_match = re.search(r'Chemical Structure\s*\n(.*?)(?=\n\d\.|$)', text, re.S | re.I)
            reaction_match = re.search(r'Clinical Efficacy and Safety\s*\n(.*?)(?=\n\d\.|$)', text, re.S | re.I)
            
            reg_match = re.search(r'Pharmaceuticals and Medical Devices Agency\s*(.*?)(?=\nReview Report|$)', text, re.S | re.I)

            if indications_match: data["indications"] = clean_text(indications_match.group(1))
            if dosage_match: data["dosage"] = clean_text(dosage_match.group(1))
            if warnings_match: data["warnings"] = clean_text(warnings_match.group(1))
            if desc_match: data["description"] = clean_text(desc_match.group(1))
            if reaction_match: data["reaction"] = clean_text(reaction_match.group(1))
            if reg_match: data["regulatory_text"] = clean_text(reg_match.group(1))

        return data
