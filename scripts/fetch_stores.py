'''
Short script to fetch the list of stores from the CheapShark API and save it to a JSON file.
This has been separated from the main pipeline script to avoid unnecessary API calls and to keep the code organised.
'''

import requests
import json

def fetch_stores():
    #fetch the list of stores from the CheapShark API
    headers = {"User-Agent": "SteamWishlistDeals/1.0"}
    response = requests.get("https://www.cheapshark.com/api/1.0/stores", headers=headers)
    stores = response.json()

    #save the list of stores to a JSON file
    with open("data/stores.json", "w") as f:
        json.dump(stores, f, indent=4)

    return

if __name__ == "__main__":
    fetch_stores()