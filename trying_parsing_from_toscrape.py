
import requests
import re
from bs4 import BeautifulSoup

def get_html(url):
    r = requests.get(url)
    return r.text

def get_page_data(html):
    soup = BeautifulSoup(html, 'lxml')
    quotes = soup.find_all('span', class_='text')
    return quotes

def write_data(response):
    for i in range(0, len(response)):
        print(response[i].text)
        print('\n')

def get_next_url(html):
    soup = BeautifulSoup(html, 'lxml')
    url = soup.find('li', class_='next')
    temp =  re.search('/page/\d*', str(url))
    if (temp == None):
        return None
    else:
        return temp.group()


url = 'https://quotes.toscrape.com/page/1'

while(url):
    html = get_html(url)
    response = get_page_data(html)
    write_data(response)
    if (get_next_url(html)):
        url = 'https://quotes.toscrape.com' + get_next_url(html)
    else:
        break

