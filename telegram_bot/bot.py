import asyncio
import logging
import os
import uuid
from urllib.parse import urljoin

import aioboto3
import aiohttp
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import File
from aiogram.types.message import ContentType
from aiogram.utils.executor import start_webhook

API_TOKEN = os.environ["API_TOKEN"]

# webhook settings
WEBHOOK_HOST = os.environ["WEBHOOK_HOST_ADDR"]
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = urljoin(WEBHOOK_HOST, WEBHOOK_PATH)

# webserver settings
WEBAPP_HOST = "0.0.0.0"  # or ip
WEBAPP_PORT = os.environ["PORT"]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


class NSTInput(StatesGroup):
    waiting_for_content = State()
    waiting_for_style = State()
    waiting_for_additional_styles = State()
    waiting_for_output = State()


READY_STYLES = {
    "Cezanne": "style_cezanne_pretrained",
    "Ukiyoe": "style_ukiyoe_pretrained",
}


READY_STYLES_MARKUP = types.ReplyKeyboardMarkup(
    resize_keyboard=True, one_time_keyboard=True, selective=True
)
READY_STYLE_NAMES_LIST = list(READY_STYLES.keys())
READY_STYLES_MARKUP.add(*READY_STYLE_NAMES_LIST)


S3_BUCKET_WITH_RESULTS_NAME = os.environ["S3_BUCKET_WITH_RESULTS_NAME"]
S3_RESULTS_PREFIX = os.environ["S3_RESULTS_PREFIX"]


NST_ENDPOINT = urljoin(os.environ["ML_SERVER_HOST_ADDR"], "run-style-transfer")

COMMAND_NAMES_LIST = [
    "/start",
    "/cancel",
    "/help",
    "/fast_dev_run_true",
    "/fast_dev_run_false",
]

DEFAULT_FAST_DEV_RUN = bool(os.getenv("DEFAULT_FAST_DEV_RUN", "True") == "True")

AUTHOR_CONTACT = os.getenv("AUTHOR_CONTACT", "author")


@dp.message_handler(commands="start", state="*")
async def cmd_start(message: types.Message, context: FSMContext):
    """
    Conversation's entry point
    """
    current_state = await context.get_state()
    if current_state is not None and not current_state.endswith("waiting_for_content"):
        if current_state.endswith("waiting_for_style"):
            what_was_done_str = "uploaded content image"
        elif current_state.endswith("waiting_for_additional_styles"):
            what_was_done_str = "uploaded content and style images"
        else:
            what_was_done_str = "launched stylization"
        logging.info(current_state)
        await message.reply(
            (
                f"You have already {what_was_done_str}, to start"
                + " all anew you please execute /cancel command"
            )
        )
        return

    await go_to_waiting_for_content(message)


async def go_to_waiting_for_content(message):
    # Set state
    await NSTInput.waiting_for_content.set()

    await message.reply(
        (
            "Please upload an image with content"
            + " to which stylization is to be applied"
        )
    )


@dp.message_handler(commands="cancel", state="*")
async def cmd_cancel(message: types.Message, context: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await context.get_state()
    if current_state is None:
        return
    elif current_state.endswith("waiting_for_content"):
        await message.reply(
            (
                "Nothing to cancel, please upload an image with"
                + " content to which stylization is to be applied"
            )
        )
        return

    logging.info("Cancelling state %r", current_state)
    # Cancel state and inform user about it
    await NSTInput.waiting_for_content.set()
    # And remove keyboard (just in case)
    await message.reply(
        (
            "Cancelled stylization, to start new stylization please upload"
            + " an image with content to which stylization is to be applied"
        ),
        reply_markup=types.ReplyKeyboardRemove(),
    )


@dp.message_handler(commands="help", state="*")
async def cmd_help(message: types.Message):
    """
    Show help
    """
    await message.reply(
        (
            "Execute /start to start stylization of a new image, /cancel"
            + " to cancel current stylization and to start a new one"
        )
    )


@dp.message_handler(commands=["fast_dev_run_true", "fast_dev_run_false"], state="*")
async def cmd_fast_dev_run(message: types.Message, context: FSMContext):
    async with context.proxy() as data:
        data["fast_dev_run"] = message.get_command().lower() == "/fast_dev_run_true"


async def get_image_url_from_message(message: types.Message):
    if message.photo:
        photo_size_list = message.photo
        file_id = photo_size_list[-1].file_id
    elif message.document:
        mime_type = message.document.mime_type
        if mime_type and mime_type.startswith("image"):
            file_id = message.document.file_id
        else:
            await message.reply("Uploaded document is not an image as was expected")
            return None
    else:
        await message.reply("Expected an image")
        return None
    result: File = await bot.get_file(file_id)
    return f"https://api.telegram.org/file/bot{API_TOKEN}/{result.file_path}"


@dp.message_handler(
    state=NSTInput.waiting_for_content,
    content_types=[ContentType.PHOTO, ContentType.DOCUMENT],
)
async def content_image_handler(message: types.Message, context: FSMContext):
    """
    Upload content image
    """
    image_url = await get_image_url_from_message(message)
    if image_url:
        async with context.proxy() as data:
            data["content_url"] = image_url
            if "fast_dev_run" not in data:
                data["fast_dev_run"] = DEFAULT_FAST_DEV_RUN
        await NSTInput.next()
        await message.reply(
            (
                "Please upload one or several images with styles to apply"
                + " or choose one of ready-to-apply-styles from the keyboard"
            ),
            reply_markup=READY_STYLES_MARKUP,
        )
    else:
        await message.reply(
            (
                "Please try again to upload an image with content"
                + " to which stylization is to be applied"
            )
        )


async def print_image_expected(message):
    await message.reply(
        (
            "An image is expected, please try again to upload"
            + " an image with content to which stylization is to be applied"
        )
    )


@dp.message_handler(content_types=ContentType.ANY, state=NSTInput.waiting_for_content)
async def content_other_handler(message: types.Message):
    print_image_expected(message)


@dp.message_handler(
    lambda message: message.text.lower() not in COMMAND_NAMES_LIST,
    state=NSTInput.waiting_for_content,
)
async def wrong_content_handler(message: types.Message):
    print_image_expected(message)


@dp.message_handler(
    state=[NSTInput.waiting_for_style, NSTInput.waiting_for_additional_styles],
    content_types=[ContentType.PHOTO, ContentType.DOCUMENT],
)
async def style_image_handler(message: types.Message, context: FSMContext):
    """
    Upload style image
    """
    image_url = await get_image_url_from_message(message)
    if image_url:
        async with context.proxy() as data:
            if "style" not in data:
                data["style"] = []
            data["style"].append(image_url)
        await NSTInput.waiting_for_additional_styles.set()
        await message.reply(
            (
                "Please upload another one or several style images"
                + " or execute /process"
                + " command to perform stylization of the content image with"
                + " the style images that are already chosen"
            ),
            reply_markup=types.ReplyKeyboardRemove(),
        )
    else:
        await message.reply(
            (
                "Please try again to upload one or several images with styles"
                + " to apply or choose one of ready-to-apply-styles from"
                + " the keyboard"
            ),
            reply_markup=READY_STYLES_MARKUP,
        )


@dp.message_handler(
    lambda message: message.text in READY_STYLE_NAMES_LIST,
    state=NSTInput.waiting_for_style,
)
async def style_name_handler(message: types.Message, context: FSMContext):
    """
    Choose name of style from ready-to-apply styles
    """
    await NSTInput.waiting_for_output.set()
    async with context.proxy() as data:
        content_url = data["content_url"]
        style_name = READY_STYLES[message.text]
        data["style"] = style_name
        fast_dev_run = data["fast_dev_run"]
        for key in ("content_url", "style"):
            data.pop(key, None)
        await message.reply(
            f"Chosen style is {message.text}, performing the stylization...",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        asyncio.create_task(
            process_cyclegan(
                message.chat.id, context, fast_dev_run, content_url, style_name
            )
        )


async def print_style_content(message):
    await message.reply(
        (
            "Wrong style name, please try again to upload one or several images"
            + " with styles to apply or choose one of ready-to-apply-styles"
            + " from the keyboard"
        )
    )


@dp.message_handler(
    lambda message: message.text not in READY_STYLE_NAMES_LIST
    and message.text.lower() not in COMMAND_NAMES_LIST,
    state=NSTInput.waiting_for_style,
)
async def wrong_style_name_handler(message: types.Message):
    await print_style_content(message)


@dp.message_handler(state=NSTInput.waiting_for_style, content_types=ContentType.ANY)
async def wrong_style_other_handler(message: types.Message):
    await print_style_content(message)


@dp.message_handler(state=NSTInput.waiting_for_additional_styles, commands="process")
async def cmd_process(message: types.Message, context: FSMContext):
    await NSTInput.waiting_for_output.set()
    async with context.proxy() as data:
        content_url = data["content_url"]
        style_url_list = data["style"]
        fast_dev_run = data["fast_dev_run"]
        for key in ("content_url", "style"):
            data.pop(key, None)
        await message.reply(
            (
                f"Chosen are {len(style_url_list)} style images,"
                + " performing the stylization..."
            )
        )
        asyncio.create_task(
            process_nst(
                message.chat.id, context, fast_dev_run, content_url, style_url_list
            )
        )


async def print_wrong_content(message):
    await message.reply(
        (
            "Wrong content, please upload another one or several style"
            + " images or execute /process command to perform stylization"
            + " of the content image with the style images that are already chosen"
        )
    )


@dp.message_handler(
    state=NSTInput.waiting_for_additional_styles,
    content_types=ContentType.ANY,
)
async def wrong_add_style_other_handler(message: types.Message):
    await print_wrong_content(message)


@dp.message_handler(
    lambda message: message.text.lower() not in COMMAND_NAMES_LIST + ["/process"],
    state=NSTInput.waiting_for_additional_styles,
)
async def wrong_add_style_handler(message: types.Message):
    await print_wrong_content(message)


async def print_style_in_progress(message):
    await message.reply(
        (
            "Stylization is in process, please wait or execute"
            + " /cancel command to interrupt this stylization"
        )
    )


@dp.message_handler(state=NSTInput.waiting_for_output, content_types=ContentType.ANY)
async def wrong_output_other_handler(message: types.Message):
    await print_style_in_progress(message)


@dp.message_handler(
    lambda message: message.text.lower() not in COMMAND_NAMES_LIST,
    state=NSTInput.waiting_for_output,
)
async def wrong_output_handler(message: types.Message):
    await print_style_in_progress(message)


@dp.message_handler(content_types=ContentType.ANY)
async def default_content_handler(message: types.Message):
    await default_handler(message)


@dp.message_handler()
async def default_handler(message: types.Message):
    await message.reply(
        (
            "I fell asleep due to user inactivity... Now I'm awake, let's start from scratch!"
        )
    )
    await go_to_waiting_for_content(message)


async def get_and_send_styled_image(
    chat_id, styled_image_key, caption, resulted_notebook_key=None
):
    async with aioboto3.resource(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name=os.environ["REGION_NAME"],
    ) as s3:
        image_obj = await s3.Object(
            bucket_name=S3_BUCKET_WITH_RESULTS_NAME, key=styled_image_key
        )
        image_resp = await image_obj.get()
        image_body = image_resp["Body"]
        image_bytes = await image_body.read()
        await bot.send_photo(chat_id, image_bytes, caption=caption)
        await image_obj.delete()
        if resulted_notebook_key is not None:
            try:
                resulted_notebook_obj = await s3.Object(
                    bucket_name=S3_BUCKET_WITH_RESULTS_NAME, key=resulted_notebook_key
                )
                await resulted_notebook_obj.delete()
            except Exception as e:
                logging.error(e)


async def process_cyclegan(chat_id, state, fast_dev_run, content_url, style_name):
    try:
        raise Exception("Not yet implemented!")
    except Exception as e:
        logging.error(e)
        await bot.send_message(
            chat_id,
            (
                "Stylization failed due to some reason, possibly inference"
                + "infrastructure is down, please contact {AUTHOR_CONTACT}"
            ),
        )
    await state.set_state(NSTInput.waiting_for_content)
    await bot.send_message(
        chat_id,
        (
            "To start new stylization please upload an image"
            + " with content to which stylization is to be applied"
        ),
    )


async def process_nst(chat_id, state, fast_dev_run, content_url, style_url_list):
    try:
        prefix_str = f"s3://{S3_BUCKET_WITH_RESULTS_NAME}/{S3_RESULTS_PREFIX}"
        uuid_str = uuid.uuid4().hex
        styled_image_file_name = f"styled_image_{chat_id}_{uuid_str}.jpeg"
        styled_image_path = f"{prefix_str}/{styled_image_file_name}"
        resulted_notebook_file_name = f"resulted_notebook_{chat_id}_{uuid_str}.ipynb"
        resulted_notebook_path = f"{prefix_str}/{resulted_notebook_file_name}"
        timeout = aiohttp.ClientTimeout(total=1200)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            param_dict = {
                "FAST_DEV_RUN": fast_dev_run,
                "CONTENT_IMAGE_PATH_OR_URL": content_url,
                "STYLE_IMAGE_PATH_OR_URL_LIST": style_url_list,
                "STYLED_IMAGE_PATH_OR_URL": styled_image_path,
                "RESULTED_NOTEBOOK_PATH_OR_URL": resulted_notebook_path,
                "MODEL_NAME": "plain_nst",
            }
            logging.info(param_dict)
            resp = await session.get(
                NST_ENDPOINT,
                json=param_dict,
            )
            logging.info(await resp.text())
            logging.info(resp.status)
            assert resp.status == 200
        styled_image_key = f"{S3_RESULTS_PREFIX}/{styled_image_file_name}"
        resulted_notebook_key = f"{S3_RESULTS_PREFIX}/{resulted_notebook_file_name}"
        await get_and_send_styled_image(
            chat_id,
            styled_image_key,
            caption="NST styled image",
            resulted_notebook_key=resulted_notebook_key,
        )
    except Exception as e:
        logging.error(e)
        await bot.send_message(
            chat_id,
            (
                "Stylization failed due to some reason, possibly inference"
                + f"infrastructure is down, please contact {AUTHOR_CONTACT}"
            ),
        )
    await state.set_state(NSTInput.waiting_for_content)
    await bot.send_message(
        chat_id,
        (
            "To start new stylization please upload an image with"
            + " content to which stylization is to be applied"
        ),
    )


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    # insert code here to run it after start


async def on_shutdown(dp):
    logging.warning("Shutting down..")

    # insert code here to run it before shutdown

    # Remove webhook (not acceptable in some cases)
    # await bot.delete_webhook()

    # Close DB connection (if used)
    await dp.storage.close()
    await dp.storage.wait_closed()

    logging.warning("Bye!")


if __name__ == "__main__":

    logging.info(f'DEFAULT_FAST_DEV_RUN = {DEFAULT_FAST_DEV_RUN}')

    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=False,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )