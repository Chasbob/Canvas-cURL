import json
import sys
from pathlib import Path

import requests
import fire


def save(item, prefix, max_file_size):
    try:
        path = prefix / Path(item['path'])
        url = item['url']
        path.mkdir(parents=True, exist_ok=True)
        file_name = item['display_name']
        file: Path = path / file_name
        if not file.is_file():
            try:
                download(path, file_name, url, max_file_size)
            except IOError:
                if not (path / item['filename']).is_file():
                    download(path, item['filename'], url, max_file_size)
        else:
            print(f"{file} exists!")
    except Exception as exception:
        print(exception)


def download(path, file_name, url, max_file_size):
    response: requests.Response = requests.get(url, stream=True)
    total = response.headers.get('content-length')

    if total > max_file_size:
        print(f'File too large!\tSkipping...')
        return
    print(f'Downloading {file_name}')
    with open(path / file_name, 'wb') as file:
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
                sys.stdout.write('\r[{}{}]'.format('█' * done,
                                                   '.' * (50 - done)))
                sys.stdout.flush()
        sys.stdout.write('\n')


def gen_items(file: str):
    with open(file) as json_file:
        items = json.load(json_file)
        for i in items:
            yield i


def main(items, prefix, max_file_size=154157394):
    for item in gen_items(items):
        save(item, prefix, max_file_size)


if __name__ == "__main__":
    fire.Fire(main)
