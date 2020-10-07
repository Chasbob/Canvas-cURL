import re
import sys
import os
import json
from pathlib import Path
import requests


def save(item):
    path = './output' / Path(item['path'])
    url = item['url']
    path.mkdir(parents=True, exist_ok=True)
    file_name = item['display_name']
    file = path / file_name
    if not file.is_file():
        with open(path / file_name, 'wb') as f:
            print("Downloading %s" % file_name)
            response = requests.get(url, stream=True)
            total = response.headers.get('content-length')

            if total is None:
                f.write(response.content)
            else:
                downloaded = 0
                total = int(total)
                for data in response.iter_content(
                        chunk_size=max(int(total / 1000), 1024 * 1024)):
                    downloaded += len(data)
                    f.write(data)
                    done = int(50 * downloaded / total)
                    sys.stdout.write('\r[{}{}]'.format('█' * done,
                                                       '.' * (50 - done)))
                    sys.stdout.flush()
        sys.stdout.write('\n')

    else:
        print(f"{file} exists!")


def gen_items(file: str):
    with open(file) as json_file:
        items = json.load(json_file)
        for item in items:
            yield item


if __name__ == "__main__":
    for item in gen_items(sys.argv[len(sys.argv) - 1]):
        save(item)
