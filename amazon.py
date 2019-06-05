import re
import imp
from  bs4 import BeautifulSoup
from urlparse import urlparse
import chardet
import urllib2
import json

api = imp.load_source('api','/var/bot/dump_/scraper/api/amazonapi.py')

AMAZON_ACCESS_KEY = ''
#Insert yorur access key from Amazon
AMAZON_SECRET_KEY = ''
#Insert yorur secret key from Amazon
AMAZON_ASSOC_TAG = ''
#Insert yorur tag from Amazon

asin_regex = r'/(\w{10})'
isbn_regex = r'/(\d{10})'

class amazon:
    def __init__(self, content, url, header):
        self.dict= {}
        self.content = content
        self.header = header
        self.url = url

    def findWholeWord(w):
        return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search

    def fetch(self):	    
    	if self.content:
    		self.soup = BeautifulSoup(self.content, 'lxml')
		return self.get_amazon_product_meta(self.url)

    def get_amazon_item_id(self,url):
        # return either ASIN or ISBN
        asin_search = re.search(asin_regex, url)
        isbn_search = re.search(isbn_regex, url)
        for search in asin_search, isbn_search:
    	    if search:
    		return search.group(1)
        return None
    
    def re_encode(self,string):
        try:
            string = string.encode('ascii', 'ignore')
        except Exception as e:
            string = string.encode('UTF-8')
            print e
        return string

    def get_links(self):
        links = []
        host = urlparse( self.url ).hostname
        scheme = urlparse( self.url ).scheme
        domain_link = scheme+'://'+host     
        
        for a in self.soup.find_all(href=True):            
            href = self.re_encode(a['href'])
            if not href or len(href) <= 1:
                continue
            elif ('javascript:' in href.lower()) or ('review' in href.lower()) or ('gift-cards' in href.lower()) or ('images' in href.lower()):
                continue
            else:
                href = href.strip()
            if href[0] == '/':
                href = (domain_link + href).strip()
            elif href[:4] == 'http':
                href = href.strip()
            elif href[0] != '/' and href[:4] != 'http':
                href = ( domain_link + '/' + href ).strip()
            if '#' in href:
                indx = href.index('#')
                href = href[:indx].strip()
            if href in links:
                continue

            links.append(self.re_encode(href))

        return links    

    def get_brdcrm(self):
        brdcrm_div = self.soup.find('div',{'id':'wayfinding-breadcrumbs_feature_div'})
        if brdcrm_div:
            brdcrm_list = []
            for a in brdcrm_div.findAll('a'):
                brdcrm_list.append(self.re_encode(a.text.strip()))
            if len(brdcrm_list) > 0:
                self.dict['brdcrm'] = brdcrm_list
        return brdcrm_list

    def get_prod_spec(self):
        prod_spec = []
        spec_div = self.soup.find('div', {'id':'prodDetails'})
        if spec_div:
            spec_cont = spec_div.find('div', {'class':'container'}).find('div',{'class':'section techD'})
            spec_table = spec_cont.find('table')
            for tr in spec_table.findAll('tr'):
                left = tr.find('td',{'class':'label'})
                right = tr.find('td', {'class':'value'})
                if left and right:
                    prod_spec.append((self.re_encode(left.text).strip(), self.re_encode(right.text).strip()))
        else:
            spec_div = self.soup.find('div', {'id':'technicalSpecifications_feature_div'})
            if spec_div:
                spec_table = spec_div.find('table')
                for tr in spec_table.findAll('tr'):
                    left = tr.find('td',{'class':'td1'})
                    right = tr.find('td', {'class':'td2'})
                    if left and right:
                        prod_spec.append((self.re_encode(left.text).strip(), self.re_encode(right.text).strip()))
            else:
                spec_div = self.soup.find('div', {'id':'detail-bullets_feature_div'})
                if spec_div:
                    spec_cont = spec_div.find('div', {'class':'content'})
                    spec_ul = spec_cont.find('ul')
                    for li in spec_ul.findAll('li'):
                        line = li.text
                        left = li
                        right = li
                        if "ASIN" in line:
                            break

                        ind = line.index(':')
                        left = line[:ind]
                        right = line[ind+1:]    
                        prod_spec.append((self.re_encode(left).strip(),self.re_encode(right).strip()))

                else:
                    spec_div = self.soup.find('div', {'id':'detail_bullets_id'})
                    if spec_div:
                        for li in spec_div.findAll('li'):                    
                            txt = li.text
                            if('Average Customer Review:' in txt) : break

                            ind = txt.index(':')
                            left = txt[:ind]
                            right = txt[ind+1:]    
                            prod_spec.append((self.re_encode(left).strip(),self.re_encode(right).strip()))
                    else:
                        spec_div = self.soup.find('table', {'id':'technical-details-table'})
                        if spec_div:
                            for tr in spec_div.findAll('tr'):
                                tds = tr.findAll('td')
                                if len(tds) == 2:
                                    left = tds[0].text
                                    right = tds[1].text
                                    prod_spec.append((self.re_encode(left).strip(),self.re_encode(right).strip()))                                            
                    
        if len(prod_spec) > 0:
            self.dict['spec'] = prod_spec

        return prod_spec

    def get_amazon_product_meta(self,url):
        # the input URL is always of amazon
        amazon = api.AmazonAPI(AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_ASSOC_TAG, region="US")
  

        product_dict = dict()

        try:
            item_id = self.get_amazon_item_id(url)

            if item_id:

                product = amazon.lookup(ItemId=item_id)   
                
                # product.price_and_currency returns in the form (price, currency)
                product_price = product.price_and_currency[0]
                

                if product_price:
                    brdcrms = list()

                    nodes = product.browse_nodes
                    while(nodes):
                        node = nodes.pop()
                        if node.name not in brdcrms:
                            brdcrms.append(str(node.name))
                        nodes.extend(node.ancestors)
                    
                    product_dict['brdcrm'] = brdcrms
                    product_dict['title'] = product.title
                    product_dict['mrp_price'] = str(product.mrp_price)
                    product_dict['selling_price'] = str(product.lowest_price)
                    product_dict['img'] = product.large_image_url
                    product_dict['spec'] = self.get_prod_spec()
        except amazon.api.AsinNotFound as e: 
            # log this ASIN
            print e
            pass

        try:
            product_dict['a_href'] = self.get_links()
        except Exception as e:
            print e

        return product_dict
