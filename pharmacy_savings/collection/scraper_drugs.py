"""Simple Drugs.com price scraper."""
import requests
from bs4 import BeautifulSoup

from ..config import USER_AGENT, REQUEST_TIMEOUT
from ..utils import log_error, format_price, get_timestamp


class DrugsScraper:
    def __init__(self):
        self.base_url = "https://www.drugs.com"
        self.headers = {"User-Agent": USER_AGENT}
        self.source = "Drugs.com"

    def search_medication(self, medication_name, strength, zipcode):
        """Search for a medication on Drugs.com. Returns a list of price records."""
        results = []

        search_query = f"{medication_name} {strength}".replace(" ", "-").lower()
        url = f"{self.base_url}/search?q={search_query}"

        try:
            print(f"Searching Drugs.com for {medication_name} {strength} in {zipcode}...")

            params = {"location": zipcode}
            response = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            drug_links = soup.find_all("a", {"data-type": "drug"})
            if not drug_links:
                print(f"  No drug links found for {medication_name}")
                log_error(self.source, f"{medication_name} {strength}", zipcode, "No results found")
                return results

            drug_url = drug_links[0].get("href")
            if not drug_url.startswith("http"):
                drug_url = self.base_url + drug_url

            response = requests.get(drug_url, headers=self.headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            price_section = soup.find("div", class_="prices")
            if not price_section:
                print(f"  No pricing information available for {medication_name}")
                log_error(self.source, f"{medication_name} {strength}", zipcode, "No pricing section")
                return results

            for row in price_section.find_all("tr")[:5]:  # Limit to top 5
                try:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        pharmacy = cols[0].text.strip()
                        price = format_price(cols[1].text.strip())
                        if price and pharmacy:
                            results.append({
                                "timestamp": get_timestamp(),
                                "source": self.source,
                                "medication": medication_name,
                                "strength": strength,
                                "pharmacy": pharmacy,
                                "price": price,
                                "location": zipcode,
                                "url": drug_url,
                            })
                            print(f"  {pharmacy}: ${price}")
                except Exception:
                    continue

        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            print(f"  Error: {error_msg}")
            log_error(self.source, f"{medication_name} {strength}", zipcode, error_msg)
        except Exception as e:
            error_msg = f"Parsing error: {str(e)}"
            print(f"  Error: {error_msg}")
            log_error(self.source, f"{medication_name} {strength}", zipcode, error_msg)

        return results

    def scrape_all(self, medications, locations):
        """Scrape prices for all medications and locations."""
        all_results = []
        for med in medications:
            for loc in locations:
                all_results.extend(
                    self.search_medication(med["name"], med["strength"], loc["zipcode"])
                )
        return all_results
