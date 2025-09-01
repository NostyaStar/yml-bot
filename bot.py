import logging
import aiohttp
import ssl
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
import asyncio
from typing import Optional
import re
import os

API_TOKEN = os.getenv('BOT_TOKEN', "8374508374:AAGFkSRbZpTJ53QeS5wbpZVLzxOqvQ3BcR4")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

YML_PATHS = [
    # Основные пути
    "/yandex.xml",
    "/yml.xml",
    "/market.yml",
    "/yandex-market.xml",
    "/export/yml.xml",

    # Wildberries и другие крупные магазины
    "/seller-feed.xml",
    "/wb-feed.xml",
    "/ozon-feed.xml",
    "/market.yaml",

    # Bitrix
    "/bitrix/catalog_export/yandex.php",
    "/bitrix/components/bitrix/catalog.export/.default/export.php",

    # WordPress
    "/wp-content/uploads/yml/yandex.xml",
    "/wp-content/uploads/feed-yml-0.xml",
    "/wp-content/uploads/feed-yml-1.xml",
    "/wp-content/uploads/feed-yml-2.xml",
    "/wp-content/uploads/feed-yml-3.xml",
    "/wp-content/uploads/feed-yml-4.xml",
    "/wp-content/uploads/feed-yml-5.xml",
    "/wp-content/uploads/feed-yml-6.xml",
    "/wp-content/uploads/feed-yml-7.xml",
    "/wp-content/uploads/feed-yml-8.xml",
    "/wp-content/uploads/feed-yml-9.xml",

    # Другие CMS
    "/yml.php",
    "/modules/yamarket/export.yml",
    "/index.php?route=feed/yandex_market",
    "/apps/yandex/export.yml",
    "/export/yandex.yml",
    "/exchange/yandex_market.xml",

    # Дополнительные пути
    "/upload/iblock/export/yandex.xml",
    "/upload/yandex.xml",
    "/catalog/export/yandex",
    "/api/yandex-market",
    "/data/feed/yandex.xml",
    "/feeds/yandex.xml",
    "/xml/yandex.xml",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,*/*;q=0.5",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def clean_url(url: str) -> str:
    """Очищает URL от протокола и лишних символов"""
    url = url.strip()
    url = re.sub(r'^https?://', '', url)
    url = url.rstrip('/')
    return url


def is_yml_catalog(text: str) -> bool:
    """Проверяет, является ли текст YML-каталогом"""
    text_lower = text.lower()

    yml_indicators = [
        "<yml_catalog",
        "yandex-market",
        "yandex.market",
        "market.yml",
        "яндекс.маркет",
        "offer id=",
        "currency id=",
        "category id=",
        "<shop>",
        "<offers>",
        "<categories>"
    ]

    main_indicators = ["<yml_catalog", "yandex-market", "yandex.market"]

    has_main_indicator = any(indicator in text_lower for indicator in main_indicators)
    has_any_indicator = any(indicator in text_lower for indicator in yml_indicators)
    is_xml_like = text.strip().startswith('<?xml') or '<' in text and '>' in text

    return has_main_indicator or (has_any_indicator and is_xml_like)


async def check_yml(site: str) -> Optional[str]:
    """Проверяем все популярные пути YML и возвращаем рабочую ссылку или главную"""
    schemes = ["https://", "http://"]
    connector = aiohttp.TCPConnector(ssl=ssl_context, limit=20)

    async with aiohttp.ClientSession(
            headers=HEADERS,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=15)
    ) as session:

        clean_site = clean_url(site)

        for scheme in schemes:
            for path in YML_PATHS:
                url = f"{scheme}{clean_site}{path}"

                try:
                    async with session.get(url, allow_redirects=True) as resp:
                        if resp.status == 200:
                            content_type = resp.headers.get('Content-Type', '').lower()
                            if any(x in content_type for x in ['xml', 'text', 'application/xml', 'text/xml']):
                                text = await resp.text()
                                if is_yml_catalog(text):
                                    return url

                except Exception:
                    continue

        # Если YML не найден, возвращаем главную страницу
        for scheme in schemes:
            main_url = f"{scheme}{clean_site}"
            try:
                async with session.get(main_url, timeout=5) as resp:
                    if resp.status == 200:
                        return main_url
            except:
                continue

    return None


@dp.message(CommandStart())
async def start(message: Message):
    welcome_text = """
    🤖 <b>YML Validator Bot</b>

    Я помогу найти YML-каталоги на вашем сайте!

    📋 <b>Доступные команды:</b>
    /check - Проверить сайт
    /help - Помощь и инструкция
    /about - О боте

    🚀 <b>Просто отправьте мне адрес сайта!</b>
    """
    await message.answer(welcome_text, parse_mode='HTML')


@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = """
    📖 <b>Инструкция по использованию:</b>

    1. Отправьте адрес сайта (например: example.com)
    2. Бот проверит более 50 возможных путей к YML-каталогам
    3. Если найдет - вернет ссылку на каталог
    4. Если нет - вернет ссылку на главную страницу

    🔍 <b>Поддерживаемые CMS:</b>
    • 1С-Битрикс
    • WordPress + WooCommerce
    • OpenCart
    • CS-Cart
    • PrestaShop
    • InSales
    • Ecwid

    💡 <b>Совет:</b> Можно отправлять сайты без http/https
    """
    await message.answer(help_text, parse_mode='HTML')


@dp.message(Command("about"))
async def about_command(message: Message):
    about_text = """
    ℹ️ <b>О YML Validator Bot</b>

    Этот бот создан для автоматического поиска YML-каталогов на сайтах.

    <b>Возможности:</b>
    • Проверка 50+ путей к YML-каталогам
    • Поддержка всех популярных CMS
    • Автоматическое определение протокола
    • Быстрая асинхронная проверка

    <b>Технологии:</b>
    • Python 3.11+
    • Aiogram 3.x
    • AsyncIO для быстрых запросов
    """
    await message.answer(about_text, parse_mode='HTML')


@dp.message(Command("check"))
async def check_command(message: Message):
    await message.answer("🔍 Отправьте мне адрес сайта для проверки (например: example.com)")


@dp.message(F.text & ~F.text.startswith('/'))
async def handle_website(message: Message):
    site = message.text.strip()

    await message.answer(f"🔎 Проверяю {site}...")

    result_url = await check_yml(site)

    if result_url:
        await message.answer(f"✅ <b>Найден YML каталог:</b>\n<code>{result_url}</code>", parse_mode='HTML')
    else:
        await message.answer("❌ YML каталог не найден")


async def set_bot_commands():
    """Устанавливаем команды бота"""
    commands = [
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="help", description="Помощь и инструкция"),
        types.BotCommand(command="check", description="Проверить сайт"),
        types.BotCommand(command="about", description="О боте")
    ]
    await bot.set_my_commands(commands)


async def main():
    """Запуск бота с бесконечным циклом"""
    await set_bot_commands()
    await bot.set_my_description("🤖 Бот для поиска YML-каталогов на сайтах")

    while True:
        try:
            logger.info("Бот запущен...")
            await dp.start_polling(bot)
        except Exception as e:
            logger.error(f"Ошибка: {e}, перезапуск через 10 секунд...")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())