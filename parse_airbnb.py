import time
import random
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

input_string = 'https://www.airbnb.com/s/Mexico-City--Mexico/homes?checkin=2024-08-21&checkout=2024-09-21'

# Setup selenium (I am using chrome here, so chrome has to be installed on your system)
chromedriver_autoinstaller.install()
options = Options()
# if you set this to False if you want to see how the chrome window loads airbnb - useful for debugging
options.headless = True

# Add preferences to disable image loading
prefs = {
    "profile.managed_default_content_settings.images": 2
}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=options)

room_links_set = set()


def apply_filters(url):
    driver.get(url)
    time.sleep(2)
    try:
        # Click the category bar filter button
        category_bar_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="category-bar-filter-button"]'))
        )
        category_bar_button.click()

        # Click the "Entire home" filter button
        entire_home_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="type-of-place--Entire home"]'))
        )
        entire_home_button.click()

        # Enter maximum price
        price_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[id="price_filter_max"]'))
        )
        price_input.click()
        price_input.send_keys(Keys.BACKSPACE * 6)
        price_input.send_keys("5000")

        # Click the "Show 1,000+ places" button
        show_places_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href*="search_type=filter_change"]'))
        )
        show_places_button.click()

        # Wait a bit for filters to apply

        time.sleep(20)

    except Exception as e:
        print(f"An error occurred while applying filters: {e}")


def get_room_links_from_page():
    # Wait until the page loads
    timeout = 5 + random.randint(0, 10)  # Set reasonable timeout
    expectation = EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href^="/rooms"]'))
    WebDriverWait(driver, timeout).until(expectation)

    # Get the page source and parse it with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find all room links and add to set to ensure uniqueness
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith("/rooms"):
            full_link = f"https://www.airbnb.com{href.split('?')[0]}?adults=2&check_in=2024-08-21&check_out=2024-09-21"
            room_links_set.add(full_link)
    print(room_links_set)


# Navigate to the initial URL
driver.get(input_string)

# Apply filters
apply_filters(input_string)

# Get the initial set of room links
get_room_links_from_page()

while True:
    try:
        # Wait until the "Next" button is clickable and set a timeout
        timeout = 25  # You can adjust the timeout as needed
        time.sleep(3)
        next_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[aria-label="Next"]'))
        )
        next_page_url = next_button.get_attribute('href')

        # Add a 2-second timeout before proceeding to the next page

        # Navigate to the next page
        driver.get(next_page_url)

        # Get room links from the next page
        get_room_links_from_page()

    except Exception as e:
        # If there's no "Next" button or any other error occurs, break the loop
        break

# Convert set to list for further processing if needed
room_links = list(room_links_set)

# Print all unique room links
for link in room_links:
    print(link)

# Close the browser
driver.quit()
