import logging
import aiohttp
import ssl
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
import asyncio
from typing import Optional
import re
import os
from aiogram.client.default import DefaultBotProperties
from aiohttp import web



async def run_http_server():
    app = web.Application()

    async def handle(request):
        return web.Response(text="Bot is running!")

    async def health_check(request):
        return web.json_response({"status": "ok", "service": "yml-checker-bot"})

    app.router.add_get('/', handle)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=8080)
    await site.start()
    print("HTTP server started on port 8080")


API_TOKEN = os.getenv("API_TOKEN", "8374508374:AAGFkSRbZpTJ53QeS5wbpZVLzxOqvQ3BcR4")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

YML_PATHS = [
    # Основные универсальные пути
    "/yandex.xml",
    "/yml.xml",
    "/market.yml",
    "/yandex-market.xml",
    "/export/yml.xml",
    "/market.xml",
    "/yandex.yml",
    "/export.xml",

    # 1С-Битрикс
    "/bitrix/catalog_export/yandex.php",
    "/bitrix/catalog_export/yandex_run.php",
    "/bitrix/catalog_export/ym.php",
    "/bitrix/components/bitrix/catalog.export/.default/export.php",
    "/bitrix/catalog_export/export_BKi.xml",

    # InSales
    "/market.yml",

    # Ecwid
    "/market.xml",

    # CS-Cart
    "/yml.php",

    # OpenCart
    "/index.php?dispatch=yml.export",
    "/index.php?route=feed/yandex_market",
    "/index.php?route=extension/feed/yandex",

    # PrestaShop
    "/modules/yamarket/yml.xml",
    "/modules/yamarket/export.yml",
    "/modules/ymlfeed/export.xml",
    "/modules/yml/yandex_market.xml",

    # WooCommerce (WordPress)
    "/wp-content/uploads/yml/yandex.xml",
    "/wp-content/uploads/woo-yml.xml",
    "/wp-content/plugins/yml-for-yandex/export.xml",
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

    # Shopify
    "/apps/yandex/export.yml",

    # RetailCRM / МойСклад
    "/export/yandex.yml",
    "/exchange/yandex_market.xml",

    # UMI.CMS
    "/yandex-market.xml",
    "/umi-yml.xml",

    # Другие CMS и универсальные пути
    "/var/yml/yandex_market.xml",
    "/export/yml.php",
    "/feeds/yml.xml",
    "/yandex_market.xml",
    "/files/export/yandex.xml",
    "/upload/iblock/export/yandex.xml",
    "/upload/yandex.xml",
    "/catalog/export/yandex",
    "/api/yandex-market",
    "/data/feed/yandex.xml",
    "/feeds/yandex.xml",
    "/xml/yandex.xml",

    # Wildberries и Ozon
    "/seller-feed.xml",
    "/wb-feed.xml",
    "/ozon-feed.xml",
    "/market.yaml",
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
    url = url.strip()
    url = re.sub(r'^https?://', '', url)
    url = url.rstrip('/')
    return url


def is_yml_catalog(text: str) -> bool:
    text_clean = ' '.join(text.strip().split()).lower()

    # Основные обязательные признаки настоящего YML-каталога
    required_indicators = [
        "<yml_catalog",
        "<shop>",
        "<offers>",
        "<offer id=",
        "<category id=",
        "<currency id="
    ]

    # Дополнительные признаки
    secondary_indicators = [
        "yandex-market",
        "yandex.market",
        "</offer>",
        "</category>",
        "<price>",
        "<url>",
        "<picture>"
    ]

    # Проверка наличия слова "Yandex" в первых 7 строчках
    first_lines = text.split('\n')[:7]
    has_yandex_in_first_lines = any('yandex' in line.lower() for line in first_lines)

    # Основные проверки
    has_required = all(indicator in text_clean for indicator in required_indicators[:3])  

    if has_required:
        has_secondary = any(indicator in text_clean for indicator in secondary_indicators)
        # Если есть основные признаки И (дополнительные признаки ИЛИ Yandex в первых строках)
        return has_secondary or has_yandex_in_first_lines

    return False


def is_valid_yml_content(text: str) -> bool:
    """
    Более строгая проверка содержимого YML
    """
    # Проверяем базовую структуру
    if not is_yml_catalog(text):
        return False

    # Дополнительные проверки:
    text_lower = text.lower()

    if '<offers>' in text_lower and '</offers>' in text_lower:
        offers_start = text_lower.find('<offers>') + len('<offers>')
        offers_end = text_lower.find('</offers>')
        offers_content = text_lower[offers_start:offers_end].strip()

        if not offers_content or '<offer' not in offers_content:
            return False

    if '<categories>' in text_lower and '</categories>' in text_lower:
        categories_start = text_lower.find('<categories>') + len('<categories>')
        categories_end = text_lower.find('</categories>')
        categories_content = text_lower[categories_start:categories_end].strip()

        if not categories_content or '<category' not in categories_content:
            return False

    return True


async def check_yml(site: str) -> Optional[str]:
    schemes = ["https://", "http://"]
    connector = aiohttp.TCPConnector(ssl=ssl_context, limit=20)

    async with aiohttp.ClientSession(
            headers=HEADERS,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=15)
    ) as session:

        clean_site = clean_url(site)

        # Проверка для InSales
        if ".myinsales.ru" not in clean_site and "insales" not in clean_site:
            insales_url = f"https://{clean_site}.myinsales.ru/market.yml"
            try:
                async with session.get(insales_url, allow_redirects=True) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get('Content-Type', '').lower()
                        if any(x in content_type for x in
                               ['xml', 'text', 'application/xml', 'text/xml', 'application/yaml']):
                            text = await resp.text()
                            if is_valid_yml_content(text):
                                return insales_url
            except:
                pass

        # Проверка для Ecwid
        if ".ecwid.com" not in clean_site and "ecwid" not in clean_site:
            ecwid_url = f"https://{clean_site}.ecwid.com/market.xml"
            try:
                async with session.get(ecwid_url, allow_redirects=True) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get('Content-Type', '').lower()
                        if any(x in content_type for x in ['xml', 'text', 'application/xml', 'text/xml']):
                            text = await resp.text()
                            if is_valid_yml_content(text):
                                return ecwid_url
            except:
                pass

        # Проверка всех остальных путей
        for scheme in schemes:
            for path in YML_PATHS:
                url = f"{scheme}{clean_site}{path}"

                try:
                    logging.info(f"Проверяем: {url}")

                    async with session.get(url, allow_redirects=True) as resp:
                        if resp.status == 200:
                            content_type = resp.headers.get('Content-Type', '').lower()

                            if any(x in content_type for x in
                                   ['xml', 'text', 'application/xml', 'text/xml', 'application/yaml', 'text/yaml']):
                                text = await resp.text()

                                # Строгая проверка YML
                                if is_valid_yml_content(text):
                                    logging.info(f"✅ Найден настоящий YML: {url}")
                                    return url
                                else:
                                    logging.info(f"❌ Файл найден, но не является YML: {url}")

                except aiohttp.ClientConnectorError:
                    continue
                except aiohttp.ServerTimeoutError:
                    continue
                except Exception as e:
                    logging.warning(f"Ошибка для {url}: {e}")
                    continue

    return None


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! 👋 Введи название сайта (например: wildberries.ru), и я проверю YML каталог.")


@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = """
📖 Инструкция по использованию бота:

1. Просто отправьте мне домен сайта (например: wildberries.ru)
2. Я проверю более 50 популярных путей к YML-каталогам
3. Если найду настоящий YML - покажу прямую ссылку на него
4. Если не найду - покажу сообщение, что не удалось найти

💡 Примеры использования:
- `wildberries.ru`
- `ozon.ru`
- `example.com`

Бот поддерживает проверку для всех популярных CMS:
- 1С-Битрикс, InSales, Ecwid
- WooCommerce, Shopify
- OpenCart, PrestaShop, CS-Cart
- И многих других
    """
    await message.answer(help_text)


@dp.message(Command("check"))
async def check_command(message: Message):
    await message.answer("🔍 Для проверки сайта просто отправьте мне его домен (например: wildberries.ru)")


@dp.message(Command("about"))
async def about_command(message: Message):
    about_text = """
🤖 О боте

Этот бот помогает находить настоящие YML-каталоги на сайтах. YML (Yandex Market Language) - это формат для выгрузки товаров в маркетплейсы.

📊 Что умеет бот:
- Проверять более 50 популярных путей к YML-каталогам
- Работать с различными CMS и платформами
- Находить каталоги для Яндекс.Маркета, Wildberries, Ozon
- Автоматически определять структуру сайта
- Отличать настоящие YML-каталоги от пустых файлов

⚡ Быстро и удобно!
    """
    await message.answer(about_text)


@dp.message()
async def get_yml(message: Message):
    if message.text.startswith('/'):
        return

    site = message.text.strip()
    await message.answer(f"🔎 Проверяю {site}...")

    result_url = await check_yml(site)

    if result_url:
        await message.answer(f"✅ Найден YML-каталог:\n{result_url}")
    else:
        await message.answer("❌ Не получилось найти YML-каталог")


async def main():
    try:
        asyncio.create_task(run_http_server())
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
