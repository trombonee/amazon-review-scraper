from selectorlib import Extractor
import requests
from time import sleep
import json
import csv

class AmazonScraper():
	def __init__(self):
		urls = ['https://www.amazon.ca/s?k=electronics'] #List of desired search URLs
		csvFilename = 'electronicsOutout' 		 #Csv file name
		jsonFilename = 'electronicsOutput'		 #Json file name

		self.headers = {
			'dnt': '1',
	        'upgrade-insecure-requests': '1',
	        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36',
	        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
	        'sec-fetch-site': 'same-origin',
	        'sec-fetch-mode': 'navigate',
	        'sec-fetch-user': '?1',
	        'sec-fetch-dest': 'document',
	        'referer': 'https://www.amazon.com/',
	        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
		}

		self.searchExtractor = Extractor.from_yaml_file('search_results.yml')
		self.reviewExtractor = Extractor.from_yaml_file('reviews.yml')

		self.data = dict()

		for url in urls:
			self.data[url] = self.searchScrape(url)

		testData = []

		for url, urlData in self.data.items():
			if urlData is not None:
				for product in urlData['products']:
					r = requests.get('https://www.amazon.ca' + product['url'], headers=self.headers)
					if r.status_code > 500:
						if "To discuss automated access to Amazon data please contact" in r.status_code:
							print("Blocked by amazon. Use better proxies")
						else:
							print("Something happened: " + r.status_code)
					
					product['url'] = r.url
					if product['whole-price'] is not None and product['fraction-price'] is not None:
						price = product['whole-price'] + product['fraction-price']
					else:
						price = "N/A"
					product['price'] = price.replace(" ", "")
					product.pop('whole-price')
					product.pop('fraction-price')
					reviewUrl = self.getReviewUrl(r.url)
					reviewData = self.productScrape(reviewUrl)
					product['reviews'] = reviewData
					testData.append(product)

				filename = jsonFilename + '.jsonl'
				with open(filename, 'w') as outfile:
					jsonFormatted = json.dumps(urlData, indent=2)
					outfile.write(jsonFormatted)
					print("completed")

				self.writeToCsv(testData)

	def writeToCsv(self, products):
		filename = csvFilename + '.csv'
		with open(filename, 'w') as outfile:
			writer = csv.writer(outfile)
			for product in products:
				row = ["Product:", product["title"]]
				writer.writerow(row)
				row = ["URL:", product["url"]]
				writer.writerow(row)
				row = ["Price:", product["price"]]
				writer.writerow(row)
				row = ["Overall Rating:", product["overall-rating"]]
				writer.writerow(row)
				row = ["Reviews:"]
				writer.writerow(row)
				row = ["Title", "Rating", "Review", "Date", "Author"]
				writer.writerow(row)
				for page in product['reviews']:
					for review in page['productreview']:
						row = [review["reviewTitle"], review["rating"], review["review"], review["date"], review["author"]]
						try:
							writer.writerow(row)
						except:
							print("Error writing a review")
				row = [""]
				writer.writerow(row)

	def searchScrape(self, url):
		print("Downloading: " + str(url))

		r = requests.get(url, headers=self.headers)

		if r.status_code > 500:
			if "To discuss automated access to Amazon data please contact" in r.status_code:
				print("Blocked by amazon. Use better proxies")
			else:
				print("Something happened: " + r.status_code)

			return None

		return self.searchExtractor.extract(r.text)

	def getReviewUrl(self, url):
		splitUrl = url.split('/')

		count = 0
		for piece in splitUrl:
			if piece == 'dp':
				splitUrl[count] = 'product-reviews'
			count += 1

		splitUrl[-1] = 'ref=cm_cr_arp_d_viewopt_rvwer?pageNumber=1&reviewerType=avp_only_reviews'

		seperator = '/'

		return seperator.join(splitUrl)


	def productScrape(self, url):
		allReviews = []
		currPage = "pageNumber=1"

		while True:
			print("Downloading: " + str(url))

			r = requests.get(url, headers=self.headers)

			if r.status_code > 500:
				if "To discuss automated access to Amazon data please contact" in r.status_code:
					print("Blocked by amazon. Use better proxies")
				else:
					print("Something happened: " + r.status_code)
				return None

			reviews = self.reviewExtractor.extract(r.text)
			print(len(reviews))
			if reviews["productreview"] is None:
				return allReviews
			for r in reviews["productreview"]:
				if r["rating"] is not None:
					r["rating"] = r["rating"].split(" out")[0]
					r["date"] = r["date"].split("on ")[-1]
			allReviews.append(reviews)
			if len(reviews) < 10 and len(allReviews) > 5:
				break
			else:
				page, currNum = currPage.split("=")
				nextNum = int(currNum) + 1
				nextPage = page + "=" + str(nextNum)
				url = url.replace(currPage, nextPage)
				currPage = nextPage

		return allReviews

if __name__ == "__main__":
	scraper = AmazonScraper()
