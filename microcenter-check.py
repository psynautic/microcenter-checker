import requests

from Adafruit_IO import *
from bs4 import BeautifulSoup
from persistentdict import PersistentDict

ADAFRUIT_KEY = '*******************'

if __name__ == '__main__':
    url = 'http://www.microcenter.com/search/search_results.aspx?Ntk=all&sortby=match&N=4294966996+4294963348+4294845156&myStore=true'
    store_id = '075'
    product_ids = ['476019', '476020']

    storecookie = requests.cookies.RequestsCookieJar()
    storecookie.set('storeSelected', store_id, domain='.microcenter.com', path='/')

    response = requests.request('GET', url, cookies=storecookie)

    soup = BeautifulSoup(response.content, 'html.parser')
    products = soup.find('section', id='mainContent').article.article.ul.find_all('li', class_='product_wrapper')

    found_products = {}
    for product in products:
        for pid in product_ids:
            if product.find(attrs={'data-id': pid}):
                found_products[pid] = product
                break

    if found_products:
        aio = Client(ADAFRUIT_KEY)
        with PersistentDict('/tmp/products-found.json', 'c', format='json') as storage:

            # update what products were already found so we dont continually update them
            found_ids = set(found_products.keys())
            not_found = found_ids.symmetric_difference(product_ids)

            stored_ids = set(storage.get('found', [])) or set()
            storage['found'] = stored_ids.difference(not_found)
            storage['found'].update(found_ids)
            storage['found'] = list(storage['found'])
            storage.sync()

        for pid in found_ids - stored_ids:
            brand = found_products[pid].find('a', class_='ProductLink_{}'.format(pid)).attrs['data-brand']
            name = found_products[pid].find('a', class_='ProductLink_{}'.format(pid)).attrs['data-name']
            message = '{} {} is onsale!\n'.format(brand, name)
            message += found_products[pid].find('div', class_='stock').text.strip('\n')
            message += found_products[pid].find('div', class_='clearance').text.strip('\r').strip('\n')
            aio.send('microcenter-checker', message)
            print(message)
    else:
        print('still out of stock')

