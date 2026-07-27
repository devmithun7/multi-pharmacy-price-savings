"""Simple GoodRx price scraper."""
import requests
from bs4 import BeautifulSoup

from ..config import USER_AGENT, REQUEST_TIMEOUT
from ..utils import log_error, format_price, get_timestamp


class GoodRxScraper:
    def __init__(self):
        self.base_url = "https://www.goodrx.com"
        self.headers = {"User-Agent": USER_AGENT}
        self.source = "GoodRx"

    def search_medication(self, medication_name, strength, zipcode):
        """Search for a medication on GoodRx. Returns a list of price records."""
        results = []

        search_query = f"{medication_name} {strength}".replace(" ", "+")
        url = f"{self.base_url}/search?q={search_query}"

        try:
            print(f"Searching GoodRx for {medication_name} {strength} in {zipcode}...")

            params = {"location": zipcode}
            response = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # GoodRx uses dynamic content, so this may return nothing without JS.
            price_elements = soup.find_all(class_="price")

            if not price_elements:
                print(f"  No prices found for {medication_name} - GoodRx may require JavaScript rendering")
                log_error(self.source, f"{medication_name} {strength}", zipcode, "No prices found (JS required)")
                return results

            for elem in price_elements[:5]:  # Limit to top 5 results
                try:
                    pharmacy_elem = elem.find_parent().find(class_="pharmacy-name")
                    pharmacy = pharmacy_elem.text.strip() if pharmacy_elem else "Unknown"

                    price = format_price(elem.text.strip())
                    if price:
                        results.append({
                            "timestamp": get_timestamp(),
                            "source": self.source,
                            "medication": medication_name,
                            "strength": strength,
                            "pharmacy": pharmacy,
                            "price": price,
                            "location": zipcode,
                            "url": url,
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
