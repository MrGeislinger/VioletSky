import asyncio
from bluesky import BlueSky, Post
from datetime import datetime
import streamlit as st

st.title('Experiments')

my_sky = BlueSky()
my_sky.login_client()

st.subheader(f'Display post')


async def draw_profile(
    profile: st.delta_generator.DeltaGenerator,
    sky: BlueSky,
    did: str,
):
    r = await sky.get_profile(
        user=did,
    )
    # profile.write(r)
    if image_url := r.get('avatar'):
        # container_avatar, container_name = profile.columns(2)
        with profile:
            profile_link = f'https://bsky.app/profile/{did}'
            st.write(
                f'[{r.get('displayName')}]({profile_link})'
            )
            st.image(
                image=image_url,
                width=80,
            )
            st.write(r.get('description'))

def display_post(
    sky: BlueSky,
    post_values,
    post_url: str | None = None,
    did: str | None = None,
    border: bool = True,
):
    profile_container, post_container = st.columns(
        spec=[1,3],
        vertical_alignment='top',
        border=border,
    )

    if did:
        asyncio.run(
            draw_profile(
                profile=profile_container,
                sky=sky,
                did=did,
            )
        )
    with post_container:
        post_link = st.markdown(
            f'[POST:]({post_url})'
        )
        # Convert to readable time format
        post_time: str = (
            datetime.fromisoformat(
                post_values.created_at
            )
            .strftime(
                '%a %d %b %Y - %H:%M:%S'
            )
        )
        st.write(post_time)
        st.code(
            body=f'{post_values.text}',
            language=None,
            wrap_lines=True,
        )
        st.json(post_values, expanded=False)

        embed = post_values.embed
        if hasattr(embed, 'media'):
            embed = getattr(embed, 'media')
        if hasattr(embed, 'images'):
            all_media = getattr(embed, 'images')  # Get the 'embeds' attribute if 'images' doesn't exist, but 'embeds' does
        else:
            all_media = list()

        if all_media:
            image_columns = st.columns(
                len(all_media),
                vertical_alignment='top',
            )
            for col, image_info in zip(image_columns, all_media):
                image_link = image_info.image.ref.link
                image_url = (
                    'https://cdn.bsky.app/img/feed_thumbnail/plain/'
                    f'{did}/{image_link}@jpeg'
                )
                col.image(
                    image=image_url,
                    width=300,
                    use_container_width=(
                        True if len(all_media) > 1
                        else None
                    ),
                    
                    caption=image_info.alt,
                )

with st.form(key='display_post'):
    post_url = st.text_input(
        label='input_post',
        help='Enter a URL of a post '
    )
    submitted = st.form_submit_button('Display Post')

    if submitted:
        post_info: Post = my_sky.resolve_post(post_url)
        # Use DID & TID directly since we possibly already queried them
        post = my_sky.get_post(
            user_did=post_info.did,
            post_rkey=post_info.tid,
        )

        st.write('### Post Details')
        did = post_info.did
        st.write(post_info)
    
        display_post(
            sky=my_sky,
            did=did,
            post_values=post.value,
        )
        

st.subheader(f'Feed Display')

with st.form(key='feed_display'):
    submitted = st.form_submit_button('Get Timeline')

    if submitted:
        feed = my_sky.client.get_timeline(
            limit=50,
            algorithm='reverse-chronological',
        )

        for feed_view in feed.feed:
            st.json(feed_view.post, expanded=False)
            
            with st.container(border=True):
                if feed_view.reason:
                    st.json(feed_view.reason, expanded=False)
                    action_by = feed_view.reason.by.handle
                    st.write(f'Reposted by @{action_by}')
                display_post(
                    sky=my_sky,
                    post_url=(
                        feed_view.post.uri  # at://DID/app.bsky.feed.post/TID"
                        .replace(
                            'at://',
                            'https://bsky.app/profile/',
                        )
                        .replace(
                            'app.bsky.feed.post',
                            'post',
                        )
                    ),
                    did=feed_view.post.author.did,
                    post_values=feed_view.post.record,
                )
        