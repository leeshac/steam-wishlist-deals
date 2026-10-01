## Steam Wishlist Deals

### What I built and who for

I built **Steam Wishlist Deals** for people who have games in their Steam wishlist and want to compare prices across Steam and other online game stores.

The purpose of the project is to help Steam users make better informed purchasing decisions by showing them the current deals available for games on their wishlist as a Steam user could miss a cheaper price on another store simply because they are unaware the game is being sold elsewhere. 

### The data

The project uses data from the **Steam Web API** and **CheapShark API**, with an additional **exchange-rate API** used to convert prices from USD to GBP.

#### Steam Web API

**Documentation:**

* [Steam Web API](https://developer.valvesoftware.com/wiki/Steam_Web_API)
* [Steam Web API reference](https://steamwebapi.azurewebsites.net/)

The official Steam Web API documentation was useful for understanding the API, but I found the Steam Web API reference easier to navigate when identifying the available endpoints.

The project uses the Steam wishlist endpoint:

```text
https://api.steampowered.com/IWishlistService/GetWishlist/v1
```

From this endpoint, I extract the App IDs of games in a user's Steam wishlist.

#### CheapShark API

**Documentation:**

* [CheapShark API Documentation](https://apidocs.cheapshark.com/)

The project uses the following CheapShark endpoints:

```text
https://www.cheapshark.com/api/1.0/deals
https://www.cheapshark.com/api/1.0/stores
```

The **deals** endpoint provides the current pricing information for games across stores, including sale price, normal price, discount percentage, store ID and other game information.

The **stores** endpoint provides the mapping between store IDs and store names, which is used to make the pricing data easier to understand.

#### Exchange rates

The project also uses [ExchangeRate-API](https://www.exchangerate-api.com/) to convert USD prices into GBP:

```text
https://api.exchangerate-api.com/v4/latest/USD
```

This allows the final output to display prices in GBP rather than leaving the CheapShark prices in USD.

### How it works

The project follows an ETL-style pipeline, extracting data from multiple APIs, cleaning and transforming it, storing historical pricing data in DuckDB, and lastly displaying the results through Streamlit.

#### 1. Extract Steam wishlist data

The user enters their Steam ID into the Streamlit application.

The Steam API is then queried to retrieve the games in their wishlist. The raw API response is saved to:

```text
data/raw/YYYY-MM-DD/
```

#### 2. Clean Steam data

The Steam wishlist data is cleaned by:

* Removing duplicate App IDs
* Removing records with missing App IDs
* Saving the cleaned data as JSON

The cleaned data is stored in:

```text
data/clean/YYYY-MM-DD/
```

The AppID is then used to query CheapShark for pricing information.

#### 3. Extract and clean CheapShark data

For each game in the Steam wishlist, the CheapShark **deals** endpoint is queried.

The raw responses are saved to the corresponding date folder in:

```text
data/raw/YYYY-MM-DD/
```

The CheapShark responses are then flattened into a single dataset and cleaned by:

* Removing duplicate deal IDs
* Removing records without a deal ID
* Saving the cleaned data to:

```text
data/clean/YYYY-MM-DD/
```

Games that do not have the corresponding CheapShark data are not included in the final dataset.

#### 4. Transform the data

The cleaned CheapShark data is transformed into two datasets.

**Games dataset:**

```text
app_id
game_name
```

This provides a lookup between the Steam AppID and the game name.

**Prices dataset:**

```text
app_id
store_id
store_name
sale_price_usd
normal_price_usd
sale_price_gbp
normal_price_gbp
discount_percentage
timestamp
```

Then at this stage:

* Store IDs are mapped to store names.
* USD prices are converted to GBP using the exchange-rate API.
* A timestamp is added to each price record.
* Price data is retained as historical records rather than replacing previous data.

#### 5. Store the data in DuckDB

The transformed datasets are loaded into a DuckDB database.

The `games` table stores the game lookup data, while the `prices` table stores the historical price snapshots.

#### 6. Query the cheapest deals

The final SQL query retrieves pricing data recorded on the date the pipeline is executed.

For each game, it selects:

* The Steam price
* The four cheapest non-Steam prices

This gives up to **five prices** per game, allowing the Steam price to be directly compared with the cheapest alternatives available from other stores.

#### 7. Display the results

The final results are displayed using Streamlit.

The user enters their Steam ID and selects **Find Deals**. The application then displays a separate table for each game in their wishlist.

The tables include a colour legend to make the comparison easier to see:

* **Steam deal** — identifies the Steam price
* **Best deal** — identifies the cheapest available price

Only pricing data from the current execution date is displayed, so the results represent the deals from that day rather than mixing current prices with historical prices.

### How to run it

#### 1. Clone the repository

Clone the repository and navigate into the project directory.

#### 2. Install the dependencies

The required Python packages and versions are listed in `requirements.txt`.

```bash
pip install -r requirements.txt
```

#### 3. Set up the API key

Use `.env.example` as a template to create a `.env` file and add your Steam API key.

#### 4. Run the application

From the project directory, run:

```bash
streamlit run scripts/app.py
```

The Streamlit application will open in your browser. Enter a Steam ID and select **Find Deals** to fetch and display the available deals.

### What I would do next

With more time, I would automate the pipeline so that it runs automatically at regular intervals rather than only when a user executes the application. For example, a local cron job could run the pipeline on a schedule and continue building the historical price dataset.

Once enough historical data had been collected, I would add a dashboard showing how game prices and discounts change over time. This could include price history graphs and patterns in the frequency and amount of discounts across different stores.

With a longer period of historical data, the project could also be extended to investigate whether there are patterns in price changes and potentially build models to forecast future price changes or identify periods when a game is more likely to go on sale.

This would take the project beyond just reporting the current cheapest price and towards providing users with additional insight into whether they may want to purchase now or wait.

### Where AI helped

AI was used to aid development throughout the project. It helped me think through architectural decisions and structure the pipeline into clear stages such as extraction, cleaning, transformation and loading.

It also helped me learn Streamlit, which I had not used before, including understanding its syntax and debugging issues while building the interface. I used AI for Python syntax that I had forgotten and for learning the DuckDB library syntax, as this was my first project using this library.