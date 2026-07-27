"""Configuration for the price-collection pipeline."""
from .paths import DEFAULT_PRICE_CSV

# Medications to track (generic name, strength, quantity)
MEDICATIONS = [
    {"name": "Metformin", "strength": "500mg", "quantity": 30},
    {"name": "Lisinopril", "strength": "10mg", "quantity": 30},
    {"name": "Atorvastatin", "strength": "20mg", "quantity": 30},
    {"name": "Amoxicillin", "strength": "500mg", "quantity": 30},
]

# US States/Locations to check (use postal codes or cities)
LOCATIONS = [
    {"zipcode": "90210", "city": "Beverly Hills, CA"},  # California
    {"zipcode": "10001", "city": "New York, NY"},        # New York
    {"zipcode": "60601", "city": "Chicago, IL"},         # Illinois
    {"zipcode": "77001", "city": "Houston, TX"},         # Texas
]

# User agent to avoid being blocked
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Request timeout
REQUEST_TIMEOUT = 10

# Data storage
OUTPUT_FILE = str(DEFAULT_PRICE_CSV)
