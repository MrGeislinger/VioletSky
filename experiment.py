import asyncio
from bluesky import BlueSky, Post
from datetime import datetime
import streamlit as st

st.title('Experiments')

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


with st.form(key='display_post'):
    post_url = st.text_input(
        label='input_post',
        help='Enter a URL of a post '
    )
    submitted = st.form_submit_button('Display Post')

    if submitted:
        my_sky = BlueSky()
        my_sky.login_client()
        post_info: Post = my_sky.resolve_post(post_url)
        # Use DID & TID directly since we possibly already queried them
        post = my_sky.get_post(
            user_did=post_info.did,
            post_rkey=post_info.tid,
        )

        st.write('### Post Details')
        # TODO: Get actual did from URI
        did = post_info.did
        st.write(post_info)
    

        #
        text = post.value.text
        with st.container(border=True):
            # Make a thin then wide column
            profile_container, post_container = st.columns(
                [1,3],
                border=True,
            )
            asyncio.run(
                draw_profile(
                    profile=profile_container,
                    sky=my_sky,
                    did=did,
                )
            )
            with post_container:
                st.markdown(
                    f'[POST:]({post_url})'
                )
                # Convert to readable time format
                post_time: str = (
                    datetime.fromisoformat(
                        post.value.created_at
                    )
                    .strftime(
                        '%a %d %b %Y - %H:%M:%S'
                    )
                )
                st.write(post_time)
                st.write(
                    f'{text}'
                )

                embed = post.value.embed
                if hasattr(embed, 'media'):
                    embed = getattr(embed, 'media')
                if hasattr(embed, 'images'):
                    all_media = getattr(embed, 'images')  # Get the 'embeds' attribute if 'images' doesn't exist, but 'embeds' does
                else:
                    all_media = list()

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


