import os
import logging
from datetime import datetime
from typing import Callable
from bs4 import BeautifulSoup
from webscraper import Webscraper
from dotenv import dotenv_values
import pytz
import uuid
from time import sleep

config = dotenv_values(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
COIN_GECKO_TABLE_NAME = config['COIN_GECKO_TABLE_NAME']
COIN_GECKO_URL = config['COIN_GECKO_URL']
TIMEZONE = config['TIMEZONE']

def scrape_coingecko_crypto_trend_ranking_results(soup: BeautifulSoup):
    logging.info("Starting to scrape the coingecko crypto trend ranking results")
    timezone = pytz.timezone(TIMEZONE)

    try:
        main_html_element = soup.find_next('main')
        if main_html_element is None:
            raise Exception("Main element not found")

        table_html_element = main_html_element.find_next('table')
        if table_html_element is None:
            raise Exception("Table element not found")

        tbody_html_element = table_html_element.find_next('tbody')
        if tbody_html_element is None:
            raise Exception("Tbody element not found")

        tr_elements = tbody_html_element.find_all('tr')
        if tr_elements is None or len(tr_elements) == 0:
            raise Exception("No table rows found")

        results = []
        assert len(tr_elements) >= 14

        for i in range(len(tr_elements)):
            td_html_elements = tr_elements[i].find_all('td')

            assert len(td_html_elements) >= 9

            crypto_name_html_element = td_html_elements[2].find_next('div', attrs={'class': 'tw-text-gray-700 dark:tw-text-moon-100 tw-font-semibold tw-text-sm tw-leading-5'})
            if crypto_name_html_element is None:
                raise Exception("Crypto name not found")

            tmp = str(crypto_name_html_element.text).split()
            crypto_name = tmp[0]
            crypto_symbol = tmp[1]

            ranking = i + 1

            first_change = td_html_elements[4].text.split()[0]
            second_change = td_html_elements[5].text.split()[0]
            third_change = td_html_elements[6].text.split()[0]
            market_cap = td_html_elements[7].text.split()[0]
            volume = td_html_elements[8].text.split()[0]

            logging.info(f"Scraped {ranking}, {crypto_name}, {crypto_symbol}, {first_change}, {second_change}, {third_change}, {market_cap}, {volume}")

            results.append({
                'id': str(uuid.uuid4()),
                'Crypto Name': crypto_name,
                'Crypto Symbol': crypto_symbol,
                'Ranking': ranking,
                '24hrs % Change': first_change,
                '7days % Change': second_change,
                '30days % Change': third_change,
                'Market Cap': market_cap,
                '24hrs Volume': volume,
                'Datetime': datetime.now(timezone).isoformat(),
            })

        return results

    except Exception as e:
        logging.error(f"Error getting the coingecko crypto trend ranking results: {e}")
        exit(1)

class CoinGeckoWebscraper(Webscraper):
    def __init__(self):
        super().__init__()

    def scrape(self, url: str, table_name: str, func: Callable):
        logging.info(f"Starting the webscraper on url: {url}")
        try:
            with self._driver:
                self._driver.get(url)

                sleep(2)

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

    webscraper = CoinGeckoWebscraper()
    webscraper.scrape(
        url=COIN_GECKO_URL,
        table_name=COIN_GECKO_TABLE_NAME,
        func=scrape_coingecko_crypto_trend_ranking_results)