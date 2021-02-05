import asyncio
import logging
import os
import typing
import uuid
from urllib.parse import urljoin

import aioboto3
import aiohttp
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import File, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.message import ContentType
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.executor import start_webhook

API_TOKEN = os.environ["API_TOKEN"]

# webhook settings
WEBHOOK_HOST = os.environ["WEBHOOK_HOST_ADDR"]
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = urljoin(WEBHOOK_HOST, WEBHOOK_PATH)

# webserver settings
WEBAPP_HOST = "0.0.0.0"  # or ip
WEBAPP_PORT = os.environ["PORT"]

# ml server settings
ML_SERVER_REQUEST_TIMEOUT = 1200

logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


class NSTInput(StatesGroup):
    waiting_for_content = State()
    waiting_for_algo_select = State()
    waiting_for_style = State()
    waiting_for_additional_styles = State()
    waiting_for_output = State()


all_style_markup = InlineKeyboardMarkup()
process_markup = InlineKeyboardMarkup()

PROCESS_BUTTON_NAME = "Apply multi-style NST"
PROCESS_ACTION = "apply_plain_nst"

style_factory = CallbackData("style", "action", "style_name")

PLAIN_NST_ACTION = "plain_nst"
PLAIN_NST_STYLE_NAME = "Multi-style NST, requires at least 1 image"

ALL_STYLES_DICT = {
    PLAIN_NST_STYLE_NAME: PLAIN_NST_ACTION,
    "Cezanne": "style_cezanne",
    "Ukiyoe": "style_ukiyoe",
    "Monet": "style_monet",
    "Vangogh": "style_vangogh",
    "Summer2Winter": "summer2winter_yosemite",
    "Winter2Summer": "winter2summer_yosemite",
}

READY_STYLE_ACTION_LIST = [
    v for k, v in ALL_STYLES_DICT.items() if v != PLAIN_NST_ACTION
]

cmd_factory = CallbackData("command", "action")

process_markup.add(
    InlineKeyboardButton(
        PROCESS_BUTTON_NAME,
        callback_data=cmd_factory.new(action=PROCESS_ACTION),
    )
)

for style, style_action in ALL_STYLES_DICT.items():
    all_style_markup.add(
        InlineKeyboardButton(
            style,
            callback_data=style_factory.new(
                action=style_action,
                style_name=style
            ),
        )
    )


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

DEFAULT_FAST_DEV_RUN = os.getenv("DEFAULT_FAST_DEV_RUN", "True") == "True"

AUTHOR_CONTACT = os.getenv("AUTHOR_CONTACT", "author")


@dp.message_handler(commands="start", state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Conversation's entry point
    """
    current_state = await state.get_state()
    if current_state is not None and not current_state.endswith("waiting_for_content"):
        if current_state.endswith("waiting_for_style"):
            what_was_done_str = "uploaded content image"
        elif current_state.endswith("waiting_for_additional_styles"):
            what_was_done_str = "uploaded content and style images"
        elif current_state.endswith("waiting_for_algo_select"):
            what_was_done_str = "selected stylization algorithm"
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

    await go_to_waiting_for_content(message.chat.id)


async def go_to_waiting_for_content(chat_id):
    # Set state
    await NSTInput.waiting_for_content.set()

    await bot.send_message(
        chat_id,
        (
            "Please upload an image with content"
            + " to which stylization is to be applied"
        )
    )


@dp.message_handler(commands="cancel", state="*")
async def cmd_cancel(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
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
        )
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


@dp.message_handler(
    commands=["fast_dev_run_true",
              "fast_dev_run_false"],
    state="*")
async def cmd_fast_dev_run(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
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
            await message.reply(
                "Uploaded document is not an image as was expected"
            )
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
async def content_image_handler(message: types.Message, state: FSMContext):
    """
    Upload content image
    """
    image_url = await get_image_url_from_message(message)
    if image_url:
        async with state.proxy() as data:
            data["content_url"] = image_url
            if "fast_dev_run" not in data:
                data["fast_dev_run"] = DEFAULT_FAST_DEV_RUN
        await NSTInput.next()
        await message.reply(
            ("Please choose the styling algorithm from the list below"),
            reply_markup=all_style_markup,
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


@dp.message_handler(
    content_types=ContentType.ANY,
    state=NSTInput.waiting_for_content
    )
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
async def style_image_handler(message: types.Message, state: FSMContext):
    """
    Upload style image
    """
    image_url = await get_image_url_from_message(message)
    if image_url:
        async with state.proxy() as data:
            if "style" not in data:
                data["style"] = []
            data["style"].append(image_url)
        await NSTInput.waiting_for_additional_styles.set()
        await message.reply(
            (
                "Please upload more style images (for multi-style transfer)"
                + f" or press {PROCESS_BUTTON_NAME}"
                + " command to perform stylization of the content image with"
                + " the style images that are already uploaded"
            ),
            reply_markup=process_markup,
        )
    else:
        current_state = await state.get_state()
        try_again_msg = (
            "Please try again to upload one or several images with styles"
            + " to apply"
        )
        if current_state.endswith("waiting_for_style"):
            await message.reply(try_again_msg)
        else:
            await message.reply(
                try_again_msg + f" or press {PROCESS_BUTTON_NAME}",
                reply_markup=process_markup,
            )


@dp.callback_query_handler(
    style_factory.filter(action=READY_STYLE_ACTION_LIST),
    state=NSTInput.waiting_for_algo_select,
)
async def ready_style_selected_handler(
    call_q: types.CallbackQuery,
    callback_data: typing.Dict[str, str],
    state: FSMContext
):
    """
    Choose name of style from ready-to-apply styles
    """
    await NSTInput.waiting_for_output.set()
    async with state.proxy() as data:
        content_url = data["content_url"]
        style_code_name = callback_data["action"]
        style_pretty_name = callback_data["style_name"]
        fast_dev_run = data["fast_dev_run"]
        for key in ("content_url", "style"):
            data.pop(key, None)
        await call_q.message.reply(
            (
                f"Selected style is {style_pretty_name},"
                + " performing the stylization..."
            )
        )

        asyncio.create_task(
            apply_style_on_ml_backend(
                call_q.message.chat.id,
                state,
                fast_dev_run,
                content_url,
                style_code_name,
            )
        )


@dp.callback_query_handler(
    style_factory.filter(action=PLAIN_NST_ACTION),
    state=NSTInput.waiting_for_algo_select,
)
async def plain_nst_algo_selected_handler(
    call_q: types.CallbackQuery,
    callback_data: typing.Dict[str, str],
    state: FSMContext
):
    await bot.send_message(
        call_q.from_user.id,
        "Please upload one or more (for multi-style transfer) images",
    )
    await NSTInput.next()


async def print_please_upload_styles(prefix, message):
    await message.reply(
        (
            prefix
            + " please try again to upload one or several images"
            + " with styles to apply"
        )
    )


@dp.message_handler(
    state=NSTInput.waiting_for_style,
    content_types=ContentType.ANY
)
async def wrong_style_other_handler(message: types.Message):
    await print_please_upload_styles("Wrong file type", message)


@dp.callback_query_handler(
    cmd_factory.filter(action=PROCESS_ACTION),
    state=NSTInput.waiting_for_additional_styles,
)
async def style_name_handler(
    call_q: types.CallbackQuery,
    callback_data: typing.Dict[str, str],
    state: FSMContext
):
    await NSTInput.waiting_for_output.set()
    async with state.proxy() as data:
        content_url = data["content_url"]
        style_url_list = data["style"]
        fast_dev_run = data["fast_dev_run"]
        for key in ("content_url", "style"):
            data.pop(key, None)
        await call_q.message.reply(
            (
                "Performing the stylization based on"
                + f" {len(style_url_list)} style image(s)..."
            )
        )
        asyncio.create_task(
            apply_style_on_ml_backend(
                call_q.message.chat.id,
                state,
                fast_dev_run,
                content_url,
                PLAIN_NST_ACTION,
                style_url_list=style_url_list,
            )
        )


@dp.message_handler(
    state=NSTInput.waiting_for_additional_styles,
    content_types=ContentType.ANY,
)
async def wrong_add_style_other_handler(message: types.Message):
    await print_please_upload_styles("Wrong file type", message)


@dp.message_handler(
    lambda message: message.text.lower() not in COMMAND_NAMES_LIST,
    state=NSTInput.waiting_for_additional_styles,
)
async def wrong_add_style_handler(message: types.Message):
    await print_please_upload_styles("Wrong style name", message)


async def print_style_in_progress(message):
    await message.reply(
        (
            "Stylization is in process, please wait or execute"
            + " /cancel command to interrupt this stylization"
        )
    )


@dp.message_handler(
    state=NSTInput.waiting_for_output,
    content_types=ContentType.ANY
)
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
            "I fell asleep due to user inactivity...and forgot everything(..."
            + " Now I'm awake, let's start from scratch!"
        )
    )
    await go_to_waiting_for_content(message.chat.id)


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
                    bucket_name=S3_BUCKET_WITH_RESULTS_NAME,
                    key=resulted_notebook_key
                )
                await resulted_notebook_obj.delete()
            except Exception as e:
                logging.error(e)


async def print_ml_server_error(chat_id):
    await bot.send_message(
        chat_id,
        (
            "Stylization failed due to some reason, possibly inference"
            + f" infrastructure is down, please contact {AUTHOR_CONTACT}"
        ),
    )


async def apply_style_on_ml_backend(
    chat_id, state, fast_dev_run, content_url, model_name, style_url_list=None
):
    try:
        prefix_str = f"s3://{S3_BUCKET_WITH_RESULTS_NAME}/{S3_RESULTS_PREFIX}"
        uuid_str = uuid.uuid4().hex
        styled_image_file_name = f"styled_image_{chat_id}_{uuid_str}.jpeg"
        styled_image_path = f"{prefix_str}/{styled_image_file_name}"
        resulted_notebook_file_name = f"resulted_notebook_{chat_id}_{uuid_str}.ipynb"
        resulted_notebook_path = f"{prefix_str}/{resulted_notebook_file_name}"
        timeout = aiohttp.ClientTimeout(total=ML_SERVER_REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            param_dict = {
                "FAST_DEV_RUN": fast_dev_run,
                "CONTENT_IMAGE_PATH_OR_URL": content_url,
                "STYLED_IMAGE_PATH_OR_URL": styled_image_path,
                "RESULTED_NOTEBOOK_PATH_OR_URL": resulted_notebook_path,
                "MODEL_NAME": model_name,
            }

            if style_url_list is not None:
                param_dict["STYLE_IMAGE_PATH_OR_URL_LIST"] = style_url_list

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
        await print_ml_server_error(chat_id)

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

    logging.info(f"DEFAULT_FAST_DEV_RUN = {DEFAULT_FAST_DEV_RUN}")

    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=False,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )