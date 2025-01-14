#!/usr/bin/env python3

from atproto import Client, IdResolver, models
from configparser import ConfigParser, NoOptionError
from pathlib import Path
from typing import Union



class ListNotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)



class BskyListTool:
    def __init__(self, handle: str=None, password: str=None, cred_file: Union[Path,str]=None,
                 token_file: Union[Path, str]=None):
        token = self._read_token_from_file(token_file)
        if cred_file is not Path:
            cred_file = Path(cred_file)
        file_handle = None
        file_pw = None
        if cred_file.exists():
           file_handle, file_pw =  self._parse_config_file(cred_file)
        if handle is None:
            if file_handle is None:
                raise ValueError('A bsky-handle was needed, but none was provided.')
            handle = file_handle
        if password is None:
            if file_pw is None:
                raise ValueError('An app password is needed, but none was provided')
            password = file_pw
        self.token_file = token_file
        self.handle = handle
        self.client = Client()
        self.resolver = IdResolver()
        if token is None:
            self.client.login(handle, password)
        else:
            self.client.login(session_string=token)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.save_token()

    @staticmethod
    def _parse_config_file(file: Path):
        config = ConfigParser()
        with open(file, 'r', encoding='utf-8') as f:
            config.read_string("[top]\n" + f.read())
        handle, password = None, None
        try:
            handle = config.get('top', 'my_handle')
            password = config.get('top', 'app_password')
        except NoOptionError:
            pass
        return handle, password

    @staticmethod
    def _read_token_from_file(file: Union[Path, str]) -> Union[str, None]:
        if file is not Path:
            file = Path(file)
        if file.exists():
            with open(file, 'r', encoding='utf-8') as f:
                token = f.read()
            return token
        else:
            return None

    def save_token(self):
        token = self.client.export_session_string()
        with open(self.token_file, 'w', encoding='utf-8') as f:
            f.write(token)

    def add_file_to_list(self, listname: str, file: Union[Path, str]) -> None:
        if file is not Path:
            file = Path(file)
        if not file.exists():
            raise FileNotFoundError(f'File {file} could not be found.')
        uri = self._get_list_uri(listname, self.handle)
        with open(file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    line = line.rstrip()
                    if line.startswith('@'):
                        line = line[1::]
                    if not line.startswith('did:'):
                        line = self.resolver.handle.resolve(line)
                    self.client.app.bsky.graph.listitem.create(
                        self.handle,
                        models.AppBskyGraphListitem.Record(
                            list=uri,
                            subject=line,
                            created_at=self.client.get_current_time_iso()
                        )
                    )

    def backup_list(self, listname: str, owner: str, file: Path):
        uri = self._get_list_uri(listname, owner)
        cursor = None
        with open(file, 'w', encoding='utf-8') as f:
            while True:
                bskylist = self.client.app.bsky.graph.get_list(
                    models.AppBskyGraphGetList.Params(list=uri, limit=100, cursor=cursor)
                )
                cursor = bskylist.cursor
                for entry in bskylist.items:
                    f.write(entry.subject.did + '\n')
                if cursor is None:
                    break

    def get_followers(self, handle: str, file: Union[Path, str]):
        cursor = None
        with open(file, 'w', encoding='utf-8') as f:
            while True:
                followers = self.client.get_followers(actor=handle, limit=100, cursor=cursor)
                cursor = followers.cursor
                for follower in followers.followers:
                    f.write(follower.did + '\n')
                if cursor is None:
                    break

    def get_likes(self, post_url: str, file: Union[Path, str]):
        at_uri = self._link_to_at_uri(post_url)
        cursor = None
        with open(file, 'w', encoding='utf-8') as f:
            while True:
                response = self.client.get_likes(uri=at_uri, limit=100, cursor=cursor)
                cursor = response.cursor
                for like in response.likes:
                    f.write(like.actor.did + '\n')
                if cursor is None:
                    break

    def _get_list_uri(self, listname: str, owner: str) -> str:
        response = self.client.app.bsky.graph.get_lists(
            models.AppBskyGraphGetLists.Params(
                actor=owner))
        for l in response.lists:
            if l['name'] == listname:
                uri = l['uri']
                break
        else:
            raise ListNotFoundException(f'List with name {listname} could not be found.')
        return uri

    def _link_to_at_uri(self, link: str) -> str:
        http_url = link.split('/')
        profile = http_url[4]
        rkey = http_url[6]
        did = self.client.resolve_handle(profile).did
        at_uri = f"at://{did}/app.bsky.feed.post/{rkey}"
        return at_uri


if __name__ == "__main__":
    from argparse import ArgumentParser
    p = ArgumentParser()
    subp = p.add_subparsers(dest='main_menu', required=True)
    list_parser = subp.add_parser('list')
    list_subp = list_parser.add_subparsers(dest='operation', required=True)
    add_p = list_subp.add_parser('add')
    add_p.add_argument('target_list_name')
    add_p.add_argument('file')
    fetch_p = subp.add_parser('fetch')
    fetch_subp = fetch_p.add_subparsers(dest='operation')
    f_list_p = fetch_subp.add_parser('list')
    f_list_p.add_argument('owner')
    f_list_p.add_argument('list_name')
    f_list_p.add_argument('file')
    follower_p = fetch_subp.add_parser('followers')
    follower_p.add_argument('handle')
    follower_p.add_argument('file')
    f_likes_p = fetch_subp.add_parser('likes')
    f_likes_p.add_argument('url')
    f_likes_p.add_argument('file')

    args = p.parse_args()
    with BskyListTool(cred_file='./config', token_file='./.bsky.token') as tool:
        match args.main_menu:
            case 'list':
                match args.operation:
                    case 'add':
                        tool.add_file_to_list(args.target_list_name, args.file)
                    case 'download':
                        tool.backup_list(args.list_name, args.owner, args.file)
                    case 'followers':
                        tool.get_followers(args.handle, args.file)
            case 'fetch':
                match args.operation:
                    case 'list':
                        tool.backup_list(args.list_name, args.owner, args.file)
                    case 'followers':
                        tool.get_followers(args.handle, args.file)
                    case 'likes':
                        tool.get_likes(args.url, args.file)
