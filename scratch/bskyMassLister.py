#!/usr/bin/env python3

BSKY_API_URL = "https://public.api.bsky.app"
BSKY_HANDLE = "chaosbengel.de"
TARGET_LIST = "Hatespam"


import os

from argparse import ArgumentParser
from atproto import Client, models, IdResolver



BSKY_APP_PW = os.environ.get("BSKY_APP_PASS")

class ListNotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)


def add_user_to_list(did: str, list_uri: str, client: Client):
    client.app.bsky.graph.listitem.create(
        BSKY_HANDLE,
        models.AppBskyGraphListitem.Record(
            list=list_uri,
            subject=did,
            created_at=client.get_current_time_iso()
        )
    )

def get_user_did(handle: str, resolver: IdResolver):
    return resolver.handle.resolve(handle)

def get_list_uri(list_name: str, client: Client) -> str:
    list_uri = None
    response = client.request.get(f"{BSKY_API_URL}/xrpc/app.bsky.graph.getLists?actor={BSKY_HANDLE}")
    for l in response.content['lists']:
        if l['name'] == TARGET_LIST:
            list_uri = l['uri']
            break
    if list_uri is None:
        raise ListNotFoundException(f"Liste {TARGET_LIST} konnte nicht gefunden werden.")
    return list_uri


def main():
    argparser = ArgumentParser()
    argparser.add_argument("filename")
    args = argparser.parse_args()
    client = Client()
    resolver = IdResolver()
    client.login(BSKY_HANDLE, BSKY_APP_PW)
    list_uri = get_list_uri(TARGET_LIST, client)
    with open(args.filename, 'r') as f:
        for entry in f:
            if entry.strip():
                entry = entry.rstrip()
                if entry.startswith("@"):
                    entry = entry[1::]
                if not entry.startswith("did:"):
                    entry = get_user_did(entry, resolver)
                add_user_to_list(entry, list_uri, client)


if __name__ == "__main__":
    main()
