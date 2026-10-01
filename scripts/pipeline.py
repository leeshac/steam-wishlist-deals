#APIs used: Steam + CheapShark
from datetime import datetime
import json
from urllib import response
import requests
import pandas as pd
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()
steam_api_key = os.getenv("STEAM_API_KEY")

def load_steam_data(user_id):
    #load steam api and using user id get wishlist data
    url = "https://api.steampowered.com/IWishlistService/GetWishlist/v1/"
    response = requests.get(url, params={"key": steam_api_key, "steamid": user_id})

    #creating the folder name based on the current date
    today = datetime.today().date()
    folder_name = today.strftime("%Y-%m-%d")

    #create the folder if it doesn't exist
    os.makedirs(f"data/raw/{folder_name}", exist_ok=True)

    #save the response to a file in data/raw folder
    with open(f"data/raw/{folder_name}/steam_wishlist.json", "w") as f:
        json.dump(response.json(), f)

    raw_steam_data = response.json()

    return raw_steam_data

def clean_steam_data(raw_steam_data):
    #remove duplicates, null values and save to data/clean folder
    remove_duplicates = pd.DataFrame(raw_steam_data['response']['items']).drop_duplicates(subset=['appid'])
    remove_nulls = remove_duplicates.dropna(subset=['appid'])

    #convert from dataframe to json
    steam_data = remove_nulls.to_dict(orient='records')

    #creating the folder name based on the current date
    today = datetime.today().date()
    folder_name = today.strftime("%Y-%m-%d")

    #create the folder if it doesn't exist
    os.makedirs(f"data/clean/{folder_name}", exist_ok=True)

    #save the cleaned data to a file in data/clean folder
    with open(f"data/clean/{folder_name}/steam_wishlist_clean.json", "w") as f:
        json.dump(steam_data, f, indent=4)

    return steam_data

def load_cheapshark_data(steam_data):
    #extract app id from steam_data and use it to get price data from cheapshark api, store as list so we can loop through
    app_ids = [game['appid'] for game in steam_data]

    raw_cheapshark_data = []

    headers = {"User-Agent": "SteamWishlistDeals/1.0"}

    #loop through each app id and get price data from cheapshark api
    for app_id in app_ids:
        response = requests.get("https://www.cheapshark.com/api/1.0/deals",params={"steamAppID": app_id}, headers=headers)
        raw_cheapshark_data.append(response.json())

    #creating the folder name based on the current date
    today = datetime.today().date()
    folder_name = today.strftime("%Y-%m-%d")

    #create the folder if it doesn't exist
    os.makedirs(f"data/raw/{folder_name}", exist_ok=True)

    #save the response to a file in data/raw folder
    with open(f"data/raw/{folder_name}/cheapshark_deals.json", "w") as f:
        json.dump(raw_cheapshark_data, f, indent=4)

    return raw_cheapshark_data

def clean_cheapshark_data(raw_cheapshark_data):
     
    #flatten the list of responses
    flatten_data = [deal for game_deals in raw_cheapshark_data for deal in game_deals]

    #remove duplicates, null values and save to data/clean folder
    remove_duplicates = pd.DataFrame(flatten_data).drop_duplicates(subset=['dealID'])
    remove_nulls = remove_duplicates.dropna(subset=['dealID'])

    #convert from dataframe to json
    cheapshark_data = remove_nulls.to_dict(orient='records')

    #creating the folder name based on the current date
    today = datetime.today().date()
    folder_name = today.strftime("%Y-%m-%d")

    #create the folder if it doesn't exist
    os.makedirs(f"data/clean/{folder_name}", exist_ok=True)

    #save the cleaned data to a file in data/clean folder
    with open(f"data/clean/{folder_name}/cheapshark_deals_clean.json", "w") as f:
        json.dump(cheapshark_data, f, indent=4)

    return cheapshark_data

def create_final_datasets(stores_mapping, usd_to_gbp, cheapshark_data, con):

    #if cheapshark_data is empty, return empty dataframes
    if not cheapshark_data:
        return pd.DataFrame(), pd.DataFrame()
    
    #FIRST DATASET: app id, game name
    #take the cleaned cheapshark data and create a dataframe with app id and game name. normalise columns to have consistent naming conventions
    games_df = pd.DataFrame(cheapshark_data)[['steamAppID', 'title']].rename(columns={'steamAppID': 'app_id', 'title': 'game_name'}).drop_duplicates(subset=['app_id'])

    #convert app id to string
    games_df['app_id'] = games_df['app_id'].astype(str)

    #SECOND DATASET: app id, store name, sale price (usd), sale price (gbp), normal price (usd), normal price (gbp), discount percentage, timestamp
    #take the cleaned cheapshark data and create a dataframe with app id, store id, sale price (usd), normal price (usd). normalise columns to have consistent naming conventions
    prices_df = pd.DataFrame(cheapshark_data)[['steamAppID', 'storeID', 'salePrice', 'normalPrice', 'savings']].rename(columns={'steamAppID': 'app_id', 'storeID': 'store_id', 'salePrice': 'sale_price_usd', 'normalPrice': 'normal_price_usd', 'savings': 'discount_percentage'})

    #convert app id to string
    prices_df['app_id'] = prices_df['app_id'].astype(str)

    #convert sale price and normal price to numeric values
    prices_df['sale_price_usd'] = pd.to_numeric(prices_df['sale_price_usd'])
    prices_df['normal_price_usd'] = pd.to_numeric(prices_df['normal_price_usd'])

    #replace store id with store name using a mapping of store ids to store names
    prices_df['store_name'] = prices_df['store_id'].map(stores_mapping)

    #convert prices from USD to GBP and add a column for the converted prices
    prices_df['sale_price_gbp'] = prices_df['sale_price_usd'] * usd_to_gbp
    prices_df['normal_price_gbp'] = prices_df['normal_price_usd'] * usd_to_gbp

    #add timestamp to the dataset
    prices_df['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    #only keep prices that haven't already been recorded today
    today = datetime.today().date()
    existing_today = con.execute("""SELECT app_id, store_id FROM prices WHERE CAST(timestamp AS DATE) = ?""", [today]).fetchdf()

    #if there are existing prices for today, merge the two dataframes and only keep the rows that don't already exist in the database
    if not existing_today.empty:
        #convert app id to string
        existing_today['app_id'] = existing_today['app_id'].astype(str)

        #merge the two dataframes and only keep the rows that don't already exist in the database
        prices_df = prices_df.merge(existing_today, on=['app_id', 'store_id'], how='left', indicator=True)
        prices_df = prices_df[prices_df['_merge'] == 'left_only'].drop(columns=['_merge'])

    #add games that don't already exist
    con.execute("""
    INSERT INTO games (app_id, game_name) 
    SELECT app_id, game_name
    FROM games_df
    WHERE NOT EXISTS (
    SELECT 1
    FROM games
    WHERE games.app_id = games_df.app_id)
    """)

    #add new prices as new rows
    if not prices_df.empty:
        con.execute("""
        INSERT INTO prices (app_id, store_id, sale_price_usd, normal_price_usd, discount_percentage, store_name, sale_price_gbp, normal_price_gbp, timestamp)
        SELECT app_id, store_id, sale_price_usd, normal_price_usd, discount_percentage, store_name, sale_price_gbp, normal_price_gbp, timestamp
        FROM prices_df
        """)

    #this runs once to create the tables in the database
    #con.execute("""CREATE TABLE games AS SELECT * FROM games_df""")
    #con.execute("""CREATE TABLE prices AS SELECT * FROM prices_df""")

    return games_df, prices_df


def main(user_id):
    #load stores.json data into a dictionary to be used for mapping store ids to store names
    with open("data/stores.json", "r") as f:
        stores_data = json.load(f)  
    stores_mapping = {store["storeID"]: store["storeName"] for store in stores_data}

    #fetch usd to gbp exchange rate from exchangerate-api.com and save to a variable
    response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
    exchange_rate_data = response.json()
    usd_to_gbp = exchange_rate_data['rates']['GBP']

    #load steam data and save raw data
    raw_steam_data = load_steam_data(user_id)
    print("Raw Steam Data:")

    #clean steam data and save cleaned data
    steam_data = clean_steam_data(raw_steam_data)
    print("Cleaned Steam Data:")

    #load cheapshark data and save raw data
    raw_cheapshark_data = load_cheapshark_data(steam_data)
    print("Raw CheapShark Data:")

    #clean cheapshark data and save cleaned data
    cheapshark_data = clean_cheapshark_data(raw_cheapshark_data)
    print("Cleaned CheapShark Data:")

    con = duckdb.connect(database='data/steam_wishlist_deals.duckdb',read_only=False)

    games_df, prices_df = create_final_datasets(stores_mapping, usd_to_gbp, cheapshark_data, con)
    print("Final Datasets:")

    #extract app id from steam_data and use it to loop through queries to get top 4 cheapest store prices for each game in the wishlist.
    wishlist_app_ids = [str(game['appid']) for game in steam_data]

    cheapest_query = """
    WITH cheapest_stores AS (
    SELECT g.game_name, p.app_id, p.store_name, p.sale_price_gbp, p.normal_price_gbp, p.discount_percentage
    FROM prices p
    JOIN games g
    ON p.app_id = g.app_id
    WHERE p.app_id = ANY(?)
    AND CAST(p.timestamp AS DATE) = ?
    AND p.store_name != 'Steam'
    QUALIFY ROW_NUMBER() OVER (
    PARTITION BY p.app_id
    ORDER BY p.sale_price_gbp ASC) <= 4)

    SELECT game_name, app_id, store_name, sale_price_gbp, normal_price_gbp, discount_percentage
    FROM cheapest_stores

    UNION ALL

    SELECT g.game_name, p.app_id, p.store_name, p.sale_price_gbp, p.normal_price_gbp, p.discount_percentage
    FROM prices p
    JOIN games g
    ON p.app_id = g.app_id
    WHERE p.app_id = ANY(?)
    AND CAST(p.timestamp AS DATE) = ?
    AND p.store_name = 'Steam'

    ORDER BY app_id, sale_price_gbp ASC
    """

    today = datetime.today().date()

    cheapest_stores_df = con.execute(cheapest_query, (wishlist_app_ids, today, wishlist_app_ids, today)).fetchdf()

    print("Cheapest Stores Data:")
    print(cheapest_stores_df)

    return cheapest_stores_df
