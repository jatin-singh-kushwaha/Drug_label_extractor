import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


def build_drugs_url(drug_name):
    """Build Drugs.com URL from drug name"""
    drug_slug = drug_name.strip().lower().replace(" ", "-")
    return f"https://www.drugs.com/{drug_slug}.html"


def extract_with_browser(url):
    """Extract page content using real browser automation"""

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Run in background
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    print("Opening browser and loading page...")
    driver.get(url)

    time.sleep(5)  # wait for full page load

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    # Remove unnecessary elements
    for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
        tag.decompose()

    main_content = soup.find("article")
    if not main_content:
        main_content = soup.body

    text = main_content.get_text(separator="\n")

    # Clean formatting
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = '\n'.join(chunk for chunk in chunks if chunk)

    return clean_text


def main():
    drug_name = input("Enter the drug name: ")

    url = build_drugs_url(drug_name)
    print(f"\nFetching data from: {url}")

    try:
        text = extract_with_browser(url)
    except Exception as e:
        print(f"Error occurred: {e}")
        return

    if not text or len(text) < 100:
        print("No meaningful content extracted.")
        return

    filename = f"{drug_name.replace(' ', '_').lower()}_drugscom.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"DRUG INFORMATION: {drug_name.upper()}\n")
        f.write("=" * 60 + "\n\n")
        f.write(text)

    print(f"\n✅ Extraction complete! Saved to {filename}")


if __name__ == "__main__":
    main()