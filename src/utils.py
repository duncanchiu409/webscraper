import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Example of waiting for a specific element to be present
def wait_for_element(driver, xpath, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        logging.info(f"Element found: {xpath}")
        return element
    except Exception as e:
        logging.error(f"Error waiting for element: {e}")
        return None

def wait_for_element_value(driver, xpath, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.text_to_be_present_in_element_value((By.XPATH, xpath), value)
        )
        logging.info(f"Element value found: {xpath}")
        return element
    except Exception as e:
        logging.error(f"Error waiting for element value: {e}")
        return None