import codecs
import json
import os
import re
from pathlib import Path

import requests
import scrapy


reader = codecs.getreader("utf-8")

class CanvasSpider(scrapy.Spider):
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
        j = json.loads(response.body_as_unicode())
        for course in j:
            yield self.build_request(context=f"courses/{course['id']}/modules", callback=self.parse_course_modules,
                                     meta={"course_name": course['name']})

    def parse_course_modules(self, response):
        base = response.url.split("?")[0]
        course = base.split("/")[6]
        j = json.loads(response.body_as_unicode())
        for i in j:
            meta = {
                "module_name": i['name'],
                "course_name": response.meta['course_name']
            }
            yield self.build_request(context=f"{course}/{i['id']}/items", callback=self.parse_module_items, meta=meta)
        yield from self.page_response(response, self.parse_module_items)

    def parse_module_items(self, response):
        pass

    def download(self, response):
        context = response.meta['path'] if response.meta['path'] else 'unknown_folder'
        path = Path(self.output_dir) / context
        path.mkdir(parents=True, exist_ok=True)
        r = requests.get(json.loads(response)['url'])
        print(r.headers['content-disposition'])

    def page_response(self, response, callback):
        if response.headers[b'Link']:
            # Check if there is more pages available
            next_page = re.findall(r"(?<=; rel=\"current\",\<)\S*(?=\>\;)",
                                   str(response.headers[b'Link']), re.MULTILINE)[0]
            if next_page:
                yield self.build_request(context='', callback=callback, url=next_page)

    # Optionally set the url argument to call that URL with `start_page` parameter instead
    def build_request(self, context, callback, meta=None, url=None):
        if not url:
            url = f"{self.base_url}/{context}?{self.start_page}"
        return scrapy.Request(url=f"{url}", callback=callback, headers=self.headers, meta=meta)
