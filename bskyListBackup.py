#!/usr/bin/env python3

BSKY_API_URL = "https://public.api.bsky.app"
BSKY_HANDLE = "chaosbengel.de"

import os

from argparse import ArgumentParser
from atproto import Client, models

BSKY_APP_PASS = os.environ.get("BSKY_APP_PASS")

class ListNotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)

def get_list_uri(list_name: str, client: Client) -> str:
    list_uri = None
    response = client.request.get(f"{BSKY_API_URL}/xrpc/app.bsky.graph.getLists?actor={BSKY_HANDLE}")
    for l in response.content['lists']:
        if l['name'] == list_name:
            list_uri = l['uri']
            break
    if list_uri is None:
        raise ListNotFoundException(f"Liste {list_name} konnte nicht gefunden werden.")
    return list_uri

def backup_list(list_uri: str, file: str, client: Client):
    bskylist = client.app.bsky.graph.get_list(
        models.AppBskyGraphGetList.Params(list=list_uri)
    )
    with open(file, 'w', encoding='utf-8') as f:
        for entry in bskylist.items:
            f.write(entry.subject.did + '\n')


def main():
    parser = ArgumentParser()
    parser.add_argument("list")
    parser.add_argument("file")
    args = parser.parse_args()
    client = Client()
    client.login(BSKY_HANDLE, BSKY_APP_PASS)
    list_uri = get_list_uri(args.list, client)
    backup_list(list_uri, args.file, client)


if __name__ == "__main__":
    main()