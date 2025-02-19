import asyncio
from bluesky import BlueSky, Post
from datetime import datetime
import requests
import streamlit as st

st.set_page_config(
    page_title="VioletSky",
    page_icon="🦋",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=dict(
        About=(
            '# Bluesky Alternative UI by '
            '[Victor](https://bsky.app/profile/did:plc:jfda6xfy4ncaf72omkvrbkko)'
        ),
    )
)

st.title('Experiments')

developer_mode = st.checkbox(
    label='DEVELOPER MODE',
)

# Save BlueSky object to keep logged in after form submit
my_sky = st.session_state.get('BlueSky', BlueSky())
if st.session_state.get('BlueSky') is None:
    st.session_state['BlueSky'] = my_sky

st.subheader(f'Display post')

# https://docs.bsky.app/docs/api/com-atproto-sync-get-blob
def get_blob(hostname, did, cid):
    url = f"https://{hostname}/xrpc/com.atproto.sync.getBlob"
    params = {"did": did, "cid": cid}
    response = requests.get(url, params=params)
    return response

async def draw_profile(
    profile: st.delta_generator.DeltaGenerator,
    sky: BlueSky,
    did: str,
    description: bool = True,
):
    r = await sky.get_profile(
        user=did,
    )
    if image_url := r.get('avatar'):
        with profile:
            profile_link = f'https://bsky.app/profile/{did}'
            st.write(
                f'[{r.get('displayName')}]({profile_link})'
            )
            st.image(
                image=image_url,
                width=80,
            )
            if description:
                with st.expander(label='DESCRIPTION'):
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
            f'[{post_url}]({post_url})'
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
        # Display reply information if message was a reply
        if hasattr(post_values, 'reply') and post_values.reply:
            reply_url = sky.convert_at_to_url(post_values.reply.parent.uri)
            reply_did, reply_tid = sky.get_did_tid_from_post(reply_url)
            reply_post = my_sky.get_post(
                user_did=reply_did,
                post_rkey=reply_tid,
            )
            root_url = sky.convert_at_to_url(post_values.reply.root.uri)
            with st.expander(label=f'Reply to {reply_url}'):
                st.write(
                    f'Reply to [message]({reply_url})'
                    f' — [Root message]({root_url})'
                )
                reply_profile_container, reply_container = st.columns(
                    spec=[1,5],
                    vertical_alignment='center'
                )
                asyncio.run(
                    draw_profile(
                        profile=reply_profile_container,
                        sky=sky,
                        did=reply_did,
                        description=False,
                    )
                )
                reply_container.code(
                    reply_post.value.text,
                    language=None,
                    wrap_lines=True,
                )
                st.write('⋮')
        st.write(post_time)
        st.code(
            body=f'{post_values.text}',
            language=None,
            wrap_lines=True,
        )
        if developer_mode:
            st.json(post_values, expanded=False)

        embed = post_values.embed
        if hasattr(embed, 'py_type'):
            match embed.py_type:
                case 'app.bsky.embed.images':
                    all_images = getattr(embed, 'images')
                    image_columns = st.columns(
                        len(all_images),
                        vertical_alignment='top',
                    )
                    for col, image_info in zip(image_columns, all_images):
                        image_link = image_info.image.ref.link
                        image_url = (
                            'https://cdn.bsky.app/img/feed_thumbnail/plain/'
                            f'{did}/{image_link}@jpeg'
                        )
                        col.image(
                            image=image_url,
                            width=300,
                            use_container_width=(
                                True if len(all_images) > 1
                                else None
                            ),
                            
                            caption=image_info.alt,
                        )
                case 'app.bsky.embed.video':
                    if embed.video.py_type == 'blob':
                        video_cid = embed.video.ref.link
                        response = get_blob(
                            hostname='bsky.social',  # Assume this
                            did=did,
                            cid=video_cid,
                        )
                        st.video(
                            data=response.content,
                            format=embed.video.mime_type,
                            loop=True,
                        )
                        if hasattr(embed.video, 'alt'):
                            st.caption(embed.video.alt)


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
            post_url=post_info.url,
        )
        

st.subheader(f'Feed Display')

with st.form(key='login', clear_on_submit=True):
    st.write(
        'Login with username and password. '
        'Recommended to use an [App Password](https://bsky.app/settings/app-passwords)'
    )
    username = st.text_input(
        label='Bluesky Username',
    )
    password = st.text_input(
        label='Bluesky or App Password',
        type='password',
    )
    login = st.form_submit_button()

    if login:
        my_sky.login_client(username=username, password=password)


with st.form(key='feed_display'):
    submitted = st.form_submit_button('Get Timeline')

    if submitted:
        feed = my_sky.client.get_timeline(
            limit=50,
            algorithm='reverse-chronological',
        )

        for feed_view in feed.feed:
            if developer_mode:
                st.json(feed_view.post, expanded=False)
            
            with st.container(border=True):
                if feed_view.reason:
                    if developer_mode:
                        st.json(feed_view.reason, expanded=False)
                    action_by = feed_view.reason.by.handle
                    st.write(f'Reposted by @{action_by}')
                display_post(
                    sky=my_sky,
                    post_url=my_sky.convert_at_to_url(feed_view.post.uri),
                    did=feed_view.post.author.did,
                    post_values=feed_view.post.record,
                )
        