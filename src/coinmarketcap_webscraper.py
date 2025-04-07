import os
import logging
from datetime import datetime
from typing import Callable
from bs4 import BeautifulSoup
from webscraper import Webscraper
from dotenv import dotenv_values
import pytz
import uuid

config = dotenv_values(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
COIN_MARKET_CAP_URL = config['COIN_MARKET_CAP_URL']
COIN_MARKET_CAP_TABLE_NAME = config['COIN_MARKET_CAP_TABLE_NAME']
TIMEZONE = config['TIMEZONE']

def scrape_coinmarketcap_crypto_trend_ranking_results(soup: BeautifulSoup):
    logging.info("Starting to scrape the coinmarketcap crypto trend ranking results")
    timezone = pytz.timezone(TIMEZONE)

    try:
        tbody_html_element = soup.find_next('tbody')
        if tbody_html_element is None:
            raise Exception("Tbody element not found")

        tr_elements = tbody_html_element.find_all('tr')
        if tr_elements is None or len(tr_elements) == 0:
            raise Exception("No table rows found")

        assert len(tr_elements) >= 9

        results = []

        for i in range(len(tr_elements)):
            td_html_elements = tr_elements[i].find_all('td')

            # Ranking
            ranking = td_html_elements[1].text

            # Crypto Name
            crypto_name = td_html_elements[2].find_next('p').text

            # Crypto Symbol
            crypto_symbol = td_html_elements[2].find_next('p', attrs={'class': 'coin-item-symbol'}).text

            # Price td
            span_html_element = td_html_elements[3].text

            # 24hrs Change
            first_change = td_html_elements[4].text

            # 7days Change
            second_change = td_html_elements[5].text

            # 30days Change
            third_change = td_html_elements[6].text

            # Market Cap
            marketCap = td_html_elements[7].text

            # 24hrs Volume
            volume = td_html_elements[8].text

            logging.info(f"Scraped {ranking}, {crypto_name}, {crypto_symbol}, {span_html_element}, {first_change}, {second_change}, {third_change}, {marketCap}, {volume}")

            results.append({
                'id': str(uuid.uuid4()),
                'Crypto Name': crypto_name,
                'Crypto Symbol': crypto_symbol,
                'Ranking': ranking,
                '24hrs % Change': first_change,
                '7days % Change': second_change,
                '30days % Change': third_change,
                'Market Cap': marketCap,
                '24hrs Volume': volume,
                'Datetime': datetime.now(timezone).isoformat(),
            })

        return results

    except Exception as e:
        logging.error(f"Error scraping the coinmarketcap crypto trend ranking results: {e}")
        exit(1)

class CoinMarketCapWebscraper(Webscraper):
    def __init__(self):
        super().__init__()

    def scrape(self, url: str, table_name: str, func: Callable):
        logging.info(f"Starting the webscraper on url: {url}")
        try:
            with self._driver:
                self._driver.get(url)

                soup = BeautifulSoup(self._driver.page_source, 'html5lib')
                results = func(soup)

                # Save the results to dynamodb
                self.save_to_dynamodb(table_name, results)
        except Exception as e:
            logging.error(f"Error getting the coin market cap url: {e}")
            exit(1)

if __name__ == "__main__":
    # Configure the logging
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    webscraper = CoinMarketCapWebscraper()
    webscraper.scrape(
        url=COIN_MARKET_CAP_URL,
        table_name=COIN_MARKET_CAP_TABLE_NAME,
        func=scrape_coinmarketcap_crypto_trend_ranking_results)
