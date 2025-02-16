import asyncio
import atproto
from dataclasses import dataclass
import dotenv
import httpx
import os

@dataclass
class Post:
    did: str
    tid: str
    url: str | None = None


class BlueSky:
    '''
    '''

    def __init__(
        self,
        verbose: bool = False,
    ):
        self._verbose: bool = verbose
        self.client: atproto.Client | None = None
    
    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, value):
        self._verbose = value 

    def login_client(self):
        dotenv.load_dotenv('.env')
        username = os.getenv('BSKY_USERNAME')
        password = os.getenv('BSKY_PASSWORD')
        if self.verbose:
            print(f'{username=}')
        self.client = atproto.Client()
    
    def get_did_from_handle(
        self,
        user_handle: str,
    ):
        resp = self.client.resolve_handle(user_handle)
        return resp.did

    def is_did(
        self,
        did_candidate: str,
    ) -> bool:
        '''Determine if a given string is a valid DID (repository)'''
        # TODO: Actual validation
        return did_candidate[:3] == 'did'

    def resolve_post(
        self,
        url: str,
    ) -> Post:
        '''Get from URL 

        Returns:
          DID (repository)
          TID (record key)
        '''
        # Split up URL
        # https://bsky.app/profile/{USER}/post/{POST}
        url_parts = (
            url
            .replace('https://', '')
            .replace('http://', '')
            .split('/')
        )
        # TODO: check if did string
        did_candidate: str = url_parts[2]
        if self.is_did(did_candidate=did_candidate):
            did = did_candidate
        else:
            did = self.get_did_from_handle(did_candidate)
        tid = url_parts[4]
        return Post(did=did, tid=tid, url=url)

    def get_uri(
        self,
        user_did,
        post_rkey,
    ) -> str:
        '''Get at://... URI'''
        quote_post_uri = f'at://{user_did}/app.bsky.feed.post/{post_rkey}'
        return quote_post_uri

    async def get_profile(
        self,
        user: str
    ) -> dict | None:
        url = (
            'https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?'
            f'actor={user}'
        )
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                # Raise an exception for bad status codes (4xx or 5xx)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                print(f'HTTP Error: {exc}')
                return None
            except httpx.RequestError as exc:
                print(f'Request Error: {exc}')
                return None
            except Exception as exc:  # Catch other potential exceptions
                print(f'An unexpected error occurred: {exc}')
                return None

    def get_post(
        self,
        post_url: str | None = None,
        user: str | None = None,
        user_did: str | None = None,
        post_rkey: str | None = None,
    ) -> atproto.models.AppBskyFeedPost.GetRecordResponse:
        '''Define (post_url) OR ( (user OR user_did) AND post_rkey )
        '''
        # TODO: Ensure at least one is defined.
        if post_url:
            post = self.resolve_post(post_url)
        else:
            user_did = (
                user_did if user_did
                else self.client.resolve_handle(user).did
            )
            post = Post(did=user_did, tid=post_rkey)

        
        full_post = self.client.get_post(
            profile_identify=post.did,
            post_rkey=post.tid,
        )
        return full_post