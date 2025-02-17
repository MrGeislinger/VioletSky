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
        self.client: atproto.Client = atproto.Client()
    
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
        self.client.login(login=username, password=password)
    
    def convert_at_to_url(
        self,
        at_uri: str,
    ) -> str:
        # at://DID/app.bsky.feed.post/TID"
        url_str = (
            at_uri
            .replace(
                'at://',
                'https://bsky.app/profile/',
            )
            .replace(
                'app.bsky.feed.post',
                'post',
            )
        )
        return url_str

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

    def get_did_tid_from_post(
        self,
        url: str,
    ) -> tuple[str, str]:
        '''Get from URL (https://)

        Returns:
          DID (repository)
          TID (record key)
        '''
        # Split up URL
        # https://bsky.app/profile/{USER}/post/{POST}
        url_parts = url.split('/')

        did_candidate: str = url_parts[4]
        if self.is_did(did_candidate=did_candidate):
            did = did_candidate
        else:
            did = self.get_did_from_handle(did_candidate)
        tid = url_parts[6]
        return (did, tid)
        
    def resolve_post(
        self,
        url: str,
    ) -> Post:
        did, tid = self.get_did_tid_from_post(url)
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
    
    def post_reply(
        self,
        reply_to: Post,
        text: atproto.client_utils.TextBuilder | str,
        embed: atproto.models.AppBskyEmbedImages.Main | None,
    ) -> atproto.models.AppBskyFeedPost.CreateRecordResponse:
        '''Post a reply.'''
        old_post = self.client.app.bsky.feed.post.get(
            repo=reply_to.did,
            rkey=reply_to.tid,
        )
        root_post_ref = atproto.models.create_strong_ref(
            model=old_post.value.reply.root,
        )
        reply_post_ref = atproto.models.create_strong_ref(
            model=old_post,
        )
        post = self.client.send_post(
            text=text,
            embed=embed,
            reply_to=atproto.models.AppBskyFeedPost.ReplyRef(
                parent=reply_post_ref,
                root=root_post_ref,
            ),
        )
        return post
    
    def get_timeline(
        self,
        limit: int | None = 8,
    ) -> list[tuple[str]]:


        print('Home (Following):\n')

        # Get "Home" page. Use pagination (cursor + limit) to fetch all posts
        timeline = self.client.get_timeline(
            limit=limit,
            algorithm='reverse-chronological',
        )
        timeline_posts = []
        for feed_view in timeline.feed:
            action = 'New Post'
            if feed_view.reason:
                action_by = feed_view.reason.by.handle
                action = f'Reposted by @{action_by}'

            post = feed_view.post.record
            author = feed_view.post.author

            post_str = f'[{action}] {author.display_name}: {post.text}'
            timeline_posts.append(
                (feed_view.post, post_str)
            )
        return timeline_posts