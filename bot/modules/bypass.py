from time import time
from re import match
from asyncio import sleep as asleep
from pyrogram.filters import command
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from pyrogram.enums import MessageEntityType
from pyrogram.errors import QueryIdInvalid
from pyrogram.handlers import MessageHandler

from bot import config_dict, bot, LOGGER
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.bot_utils import sync_to_async

def convert_time(seconds):
    mseconds = seconds * 1000
    periods = [
        ('d', 86400000),
        ('h', 3600000),
        ('m', 60000),
        ('s', 1000),
        ('ms', 1)
    ]
    result = ''
    for period_name, period_seconds in periods:
        if mseconds >= period_seconds:
            period_value, mseconds = divmod(mseconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    if result == '':
        return '0ms'
    return result

def is_excep_link(url):
    return bool(
        match(
            # r"https?:\/\/.+\.(1tamilmv|gdtot|filepress|pressbee|gdflix|vifix|gdlink|ziddiflix|sharespark)\.\S+|https?:\/\/(sharer|onlystream|hubdrive|katdrive|drivefire|skymovieshd|toonworld4all|kayoanime|cinevood|gdflix|vifix|gdlink|ziddiflix|filepress|pressbee|filebee|appdrive)\.\S+",
            r"https?:\/\/.+\.(1tamilmv|gdtot|filepress|pressbee|sharespark)\.\S+|https?:\/\/(sharer|onlystream|katdrive|drivefire|skymovieshd|toonworld4all|kayoanime|cinevood|filepress|pressbee|filebee|appdrive)\.\S+",
            url,
        )
    )

async def bypass_check(client, message):
    uid = message.from_user.id
    if (reply_to := message.reply_to_message) and (reply_to.text is not None or reply_to.caption is not None):
        txt = reply_to.text or reply_to.caption
        entities = reply_to.entities or reply_to.caption_entities
    elif len(message.command) > 1:
        txt = message.text
        entities = message.entities
    else:
        return await message.reply('<i>No Link Provided!</i>')
    
    wait_msg = await message.reply("<i>Bypassing...</i>")
    start = time()

    tlinks, results, no = [], [], 0
    for enty in entities:
        if enty.type == MessageEntityType.URL:
            link = txt[enty.offset:(enty.offset+enty.length)]
        elif enty.type == MessageEntityType.TEXT_LINK:
            link = enty.url
        else:
            link = ''
        if link:
            LOGGER.info(f"Bypassing link: {link}")
            no += 1
            tlinks.append(link)
            try:
                result = await sync_to_async(direct_link_generator, link)
            except Exception as e:
                LOGGER.info(f"Failed to bypass: {link} | Error: {e}")
                result = e
            results.append(result)

    parse_data = []
    for result, link in zip(results, tlinks):
        if isinstance(result, Exception):
            bp_link = f"\n↦ <b>Bypass Error:</b> {result}"
        elif is_excep_link(link):
            bp_link = result
        elif isinstance(result, list):
            bp_link, ui = "", "↦"
            for ind, lplink in reversed(list(enumerate(result, start=1))):
                bp_link = f"\n{ui} <b>{ind}x Bypass Link:</b> {lplink}" + bp_link
                ui = "↦"
        else:
            bp_link = f"\n↦<b>Bypass Link:</b> {result}"
    
        if is_excep_link(link):
            parse_data.append(f"{bp_link}\n\n\n\n")
        else:
            parse_data.append(f'<b>Source Link:</b> {link}{bp_link}\n\n\n\n')
            
    end = time()

    if len(parse_data) != 0:
        parse_data[-1] = parse_data[-1] + f"↦ <b>Total Links : {no}</b>\n↦ <b>Results In <code>{convert_time(end - start)}</code></b> !\n↦ <b>By </b>{message.from_user.mention} ( #ID{message.from_user.id} )"
    tg_txt = "\n\n"
    for tg_data in parse_data:
        tg_txt += tg_data
        if len(tg_txt) > 4000:
            await wait_msg.edit(tg_txt, disable_web_page_preview=True)
            wait_msg = await message.reply("<i>Fetching...</i>", reply_to_message_id=wait_msg.id)
            tg_txt = ""
            await asleep(2.5)
    
    if tg_txt != "":
        await wait_msg.edit(tg_txt, disable_web_page_preview=True)
    else:
        await wait_msg.delete()

async def inline_query(client, query):
    answers = [] 
    string = query.query.lower()
    if string.startswith("!bp "):
        link = string.strip('!bp ')
        start = time()
        try:
            LOGGER.info(f"Bypassing link: {link}")
            bp_link = await sync_to_async(direct_link_generator, link)
            end = time()
            if not is_excep_link(link):
                bp_link = f"↦ <b>Source Link:</b> {link}\n┃\n↦ <b>Bypass Link:</b> {bp_link}"
            answers.append(InlineQueryResultArticle(
                title="✅️ Bypass Link Success !",
                input_message_content=InputTextMessageContent(
                    f'{bp_link}\n\n✎﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏\n\n🧭 <b>Took Only <code>{convert_time(end - start)}</code></b>',
                    disable_web_page_preview=True,
                ),
                description=f"Bypass via !bp {link}",
                reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('Bypass Again', switch_inline_query_current_chat="!bp ")]
                ])
            ))
        except Exception as e:
            LOGGER.info(f"Failed to bypass: {link} | Error: {e}")
            bp_link = f"<b>Bypass Error:</b> {e}"
            end = time()
            answers.append(InlineQueryResultArticle(
                title="❌️ Bypass Link Error !",
                input_message_content=InputTextMessageContent(
                    f'↦ <b>Source Link:</b> {link}\n┃\n↦ {bp_link}\n\n✎﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏\n\n🧭 <b>Took Only <code>{convert_time(end - start)}</code></b>',
                    disable_web_page_preview=True,
                ),
                description=f"Bypass via !bp {link}",
                reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('Bypass Again', switch_inline_query_current_chat="!bp ")]
                ])
            ))    
    else:
        answers.append(InlineQueryResultArticle(
                title="♻️ Bypass Usage: In Line",
                input_message_content=InputTextMessageContent(
                    "<b><i>Bypass Bot!</i></b>\n    \n    <i>A Powerful Elegant Multi Threaded Bot written in Python... which can Bypass Various Shortener Links, Scrape links, and More ... </i>\n    \nUsage: !bp [Single Link]",
                ),
                description="Bypass via !bp [link]",
                reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Channel", url="https://t.me/SonGoku_Vegeta"),
                        InlineKeyboardButton('Try Bypass', switch_inline_query_current_chat="!bp ")]
                ])
            ))
    try:
        await query.answer(
            results=answers,
            cache_time=0
        )
    except QueryIdInvalid:
        pass

bot.add_handler(MessageHandler(bypass_check, filters=command(
    BotCommands.BypassCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
