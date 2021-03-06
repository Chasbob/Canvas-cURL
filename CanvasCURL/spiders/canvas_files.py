import codecs
import json
import os
import re
from copy import copy
from pathlib import Path

import requests
import scrapy

reader = codecs.getreader("utf-8")


class CanvasSpider(scrapy.Spider):
    name = "canvas_files"
    token = os.environ['TOKEN']
    headers = {"Authorization": f" Bearer {token}"}
    base_url = 'https://canvas.bham.ac.uk/api/v1'
    start_page = 'page=1&per_page=10'
    output_prefix = ''

    def start_requests(self):
        urls = [f"{self.base_url}/courses?{self.start_page}"]
        for url in urls:
            yield scrapy.Request(url=url,
                                 callback=self.parse,
                                 headers=self.headers)

    def parse(self, response, **kwargs):
        j = json.loads(response.body_as_unicode())
        meta = response.copy().meta
        for course in j:
            meta = copy(meta)
            meta['course_id'] = course['id']
            meta['course_name'] = str(course['name']).strip()
            # parse modules
            yield from self.build_request(
                context=f"courses/{meta['course_id']}/modules",
                callback=self.parse_course,
                meta=meta)
            # parse folders
            yield from self.build_request(
                context=f"courses/{meta['course_id']}/folders",
                callback=self.parse_folders,
                meta=meta)
        yield from self.page_response(response, self.parse)

    def parse_course(self, response):
        j = json.loads(response.body_as_unicode())
        for i in j:
            if i:
                meta = response.copy().meta
                meta['folder_name'] = str(i['name']).strip()
                yield from self.build_request(
                    context=
                    f"courses/{meta['course_id']}/modules/{i['id']}/items",
                    callback=self.parse_module_items,
                    meta=meta)
        yield from self.page_response(response, self.parse_course)

    def parse_folders(self, response):
        folders = json.loads(response.body_as_unicode())
        for folder in folders:
            meta = response.copy().meta
            meta['folder_name'] = str(folder['full_name']).strip()
            # parse files in folder
            yield from self.build_request(context='',
                                          callback=self.parse_files,
                                          meta=meta,
                                          url=folder['files_url'])
            # parse folders in folder
            yield from self.build_request(context='',
                                          callback=self.parse_folders,
                                          meta=meta,
                                          url=folder['folders_url'])

    def parse_files(self, response):
        files = json.loads(response.body_as_unicode())
        meta = response.copy().meta
        for file in files:
            yield self.yield_file(file, meta['course_name'],
                                  meta['folder_name'])

    def parse_module_items(self, response):
        items = json.loads(response.body_as_unicode())
        meta = response.copy().meta
        for item in items:
            if item['type'] == 'File':
                yield from self.build_request(context='',
                                              callback=self.parse_file,
                                              meta=meta,
                                              url=item['url'])
            elif item['type'] == 'Page':
                yield from self.build_request(context='',
                                              callback=self.parse_module_html,
                                              meta=meta,
                                              url=item['url'])

        yield from self.page_response(response=response,
                                      callback=self.parse_module_items)

    def parse_module_html(self, response):
        meta = response.copy().meta
        j = json.loads(response.body_as_unicode())
        a_selectors = scrapy.selector.Selector(text=j['body']).xpath('//a')
        selector: scrapy.selector.Selector
        for selector in a_selectors:
            url = selector.xpath('@href').extract_first()
            if url:
                if str(url).startswith('/courses') or 'files' in url:
                    name = selector.xpath('@title').extract_first()
                    # Some rubbish checks to make sure the file gets a name
                    if not name:
                        name = selector.xpath('text()').extract_first()
                    if not name:
                        name = re.sub('/', '_', url)
                    if not name:
                        print(str(selector.get()))
                    yield self.yield_file(file={
                        'display_name': name,
                        'filename': name,
                        'url': url
                    },
                                          course_name=meta['course_name'],
                                          folder_name=meta['folder_name'])

    def yield_file(self, file, course_name, folder_name):
        path = Path(self.output_prefix) / course_name / folder_name
        return {
            'course_name': course_name,
            'folder_name': folder_name,
            'display_name': file['display_name'],
            'filename': file['filename'],
            'path': str(path),
            'url': str(file['url'])
        }

    def parse_file(self, response):
        meta = response.copy().meta
        file = json.loads(response.body_as_unicode())
        yield self.yield_file(file, meta['course_name'], meta['folder_name'])

    def page_response(self, response, callback):
        if response.headers[b'Link']:
            # Check if there is more pages available
            next_page = re.findall(r"(?<=; rel=\"current\",\<)\S*(?=\>\;)",
                                   str(response.headers[b'Link']),
                                   re.MULTILINE)[0]
            if next_page:
                meta = response.copy().meta
                yield from self.build_request(context='',
                                              callback=callback,
                                              url=next_page,
                                              meta=meta)

    # Optionally set the url argument to call that URL with `start_page` parameter instead
    def build_request(self, context, callback, meta=None, url=None):
        if not url:
            url = f"{self.base_url}/{context}?{self.start_page}"
        yield scrapy.Request(url=f"{url}",
                             callback=callback,
                             headers=self.headers,
                             meta=meta)
