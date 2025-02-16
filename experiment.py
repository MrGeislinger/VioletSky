import asyncio
from bluesky import BlueSky
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


with st.form(key='display_post'):
    post = st.text_input(
        label='input_post',
        help='Enter a URL of a post '
    )
    submitted = st.form_submit_button('Display Post')

    if submitted:
        my_sky = BlueSky()
        my_sky.login_client()
        post = my_sky.get_post(post)

        st.write('### Post Details')
        # TODO: Get actual did from URI
        did = 'did:plc:jfda6xfy4ncaf72omkvrbkko'
    

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
                    '_:blue[POST:]_'
                )
                st.write(post.value.created_at)
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

                for image_info in all_media:
                    image_link = image_info.image.ref.link
                    image_url = (
                        f'https://cdn.bsky.app/img/feed_thumbnail/plain/{did}/{image_link}@jpeg'
                    )
                    st.image(
                        image=image_url,
                        width=200,
                        caption=image_info.alt,
                    )


