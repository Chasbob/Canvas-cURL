import json
import sys
from pathlib import Path

import requests


def save(item):
    try:
        path = './output' / Path(item['path'])
        url = item['url']
        path.mkdir(parents=True, exist_ok=True)
        file_name = item['display_name']
        file = path / file_name
        if not file.is_file():
            try:
                with open(path / file_name, 'wb') as file:
                    download(file, file_name, url)
            except IOError as e:
                if not (path / item['filename']).is_file():
                    with open(path / item['filename'], 'wb') as file:
                        download(file, item['filename'], url)
        else:
            print(f"{file} exists!")
    except Exception as exception:
        print(exception)


def download(file, file_name, url):
    print("Downloading %s" % file_name)
    response = requests.get(url, stream=True)
    total = response.headers.get('content-length')

    if total is None:
        file.write(response.content)
    else:
        downloaded = 0
        total = int(total)
        for data in response.iter_content(
                chunk_size=max(int(total / 1000), 1024 * 1024)):
            downloaded += len(data)
            file.write(data)
            done = int(50 * downloaded / total)
            sys.stdout.write('\r[{}{}]'.format('█' * done, '.' * (50 - done)))
            sys.stdout.flush()
    sys.stdout.write('\n')


def gen_items(file: str):
    with open(file) as json_file:
        items = json.load(json_file)
        for i in items:
            yield i


if __name__ == "__main__":
    for item in gen_items(sys.argv[len(sys.argv) - 1]):
        save(item)
