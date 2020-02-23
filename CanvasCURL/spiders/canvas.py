import codecs
import json
import os
import re

import scrapy


reader = codecs.getreader("utf-8")

class QuotesSpider(scrapy.Spider):
    name = "canvas"
    token = os.environ['TOKEN']
    headers = {"Authorization": f" Bearer {token}"}
    base_url = 'https://canvas.bham.ac.uk/api/v1'
    start_page = 'page=1&per_page=10'
    output_dir = './output'

    def start_requests(self):
        urls = [
            f"{self.base_url}/courses?{self.start_page}"
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse, headers=self.headers)

    def parse(self, response):
        yield from self.page_response(response, self.parse)
        page = response.url.split("/")[-2]
        j = json.loads(response.body_as_unicode())
        for course in j:
            yield self.build_request(context=f"courses/{course['id']}/modules", callback=self.parse_course_modules)


    def parse_course_modules(self, response):
        base = response.url.split("?")[0]
        j = json.loads(response.body_as_unicode())
        for i in j:
            print(f"{base}/{i['id']}/items")

    def page_response(self, response, callback):
        if response.headers[b'Link']:
            # Check if there is more pages available
            next_page = re.findall(r"(?<=; rel=\"current\",\<)\S*(?=\>\;)",
                                   str(response.headers[b'Link']), re.MULTILINE)[0]
            if next_page:
                yield self.build_request(context='', callback=callback, url=next_page)

    # Optionally set the url argument to call that URL with `start_page` parameter instead
    def build_request(self, context, callback, meta=None, url=None):
        if url:
            return scrapy.Request(url=f"{url}?{self.start_page}", callback=callback, headers=self.headers, meta=meta)
        else:
            return scrapy.Request(url=f"{self.base_url}/{context}?{self.start_page}", callback=callback,
                                  headers=self.headers, meta=meta)
