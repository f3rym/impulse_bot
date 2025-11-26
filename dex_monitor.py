import aiohttp
import asyncio
import time
import random

from config import TOKENS, PROXIES, USE_PROXIES
from logger import file_logger  # << основной логгер (импульсы, cex)
from requiest_logger import logger as request_logger  # << лог запросов

class DexMonitor:
    def __init__(self, impulse_detector, cex_monitor):
        self.impulse_detector = impulse_detector
        self.cex_monitor = cex_monitor

        self.current_prices = {}
        self.last_update = {}
        self.request_count = 0

        self.proxy_index = 0
        self.failed_proxies = set()
        self.working_proxies = set()

    def get_proxy(self):
        """Выдаёт прокси по кругу + учитывает нерабочие"""
        if not USE_PROXIES or not PROXIES:
            return None

        if len(self.failed_proxies) >= len(PROXIES):
            self.failed_proxies.clear()
            file_logger.print_status("🔄 Сброс черного списка прокси")

        proxy = PROXIES[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(PROXIES)
        return proxy

    async def fetch_price_dexscreener(self, session, token_address, symbol):
        start_time = time.time()
        random_param = random.random()

        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}?r={random_param}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

        proxy_url = self.get_proxy() if USE_PROXIES else None

        try:
            timeout = aiohttp.ClientTimeout(total=20)

            async with session.get(
                url,
                headers=headers,
                timeout=timeout,
                proxy=proxy_url,
                ssl=False
            ) as response:

                response_time = time.time() - start_time
                status_code = int(response.status)

                # лог запроса (успех)
                request_logger.log_request(
                    url=url,
                    proxy=proxy_url,
                    status=status_code,
                    response_time=response_time
                )

                if status_code == 200:
                    data = await response.json()

                    if data.get("pairs"):
                        price_str = data["pairs"][0].get("priceUsd")
                        if price_str:
                            price = float(price_str)
                            file_logger.print_status(f"✅ {symbol}: ${price:.8f}")
                            return price

                    file_logger.print_status(f"❌ Нет данных о цене для {symbol}")
                    return None

                # Ошибки (403, 429 и т.п.)
                if status_code == 403:
                    file_logger.print_status(f"❌ 403 Forbidden - IP не в белом списке")

                if status_code == 429:
                    file_logger.print_status(f"⏳ Rate Limit — задержка")

                return None

        except asyncio.TimeoutError:
            response_time = time.time() - start_time

            request_logger.log_request(
                url=url,
                proxy=proxy_url,
                status="TIMEOUT",
                response_time=response_time,
                error="Таймаут"
            )

            file_logger.print_status(f"⏰ Таймаут для {symbol}")
            return None

        except aiohttp.ClientProxyConnectionError:
            response_time = time.time() - start_time

            request_logger.log_request(
                url=url,
                proxy=proxy_url,
                status="PROXY_ERROR",
                response_time=response_time,
                error="Ошибка подключения к прокси"
            )

            file_logger.print_status(f"🔌 Ошибка подключения к прокси для {symbol}")

            if proxy_url:
                self.failed_proxies.add(proxy_url)

            return None

        except Exception as e:
            response_time = time.time() - start_time

            request_logger.log_request(
                url=url,
                proxy=proxy_url,
                status="ERROR",
                response_time=response_time,
                error=str(e)
            )

            file_logger.print_status(f"❌ Неизвестная ошибка для {symbol}: {e}")
            return None

    async def monitor_all_tokens(self):
        print(f"\n🎯 ЗАПУСК СКАНИРОВАНИЯ {len(TOKENS)} ТОКЕНОВ")
        print("=" * 80)

        connector = aiohttp.TCPConnector(limit=10, ssl=False)

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []

            # создаём задачи
            for symbol, address in TOKENS.items():
                tasks.append((symbol, self.fetch_price_dexscreener(session, address, symbol)))

            # собираем результаты
            results = []
            for symbol, task in tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=25.0)
                    results.append(result)
                except asyncio.TimeoutError:
                    file_logger.print_status(f"⏰ Общий таймаут для {symbol}")
                    results.append(None)
                except Exception as e:
                    file_logger.print_status(f"❌ Ошибка задачи для {symbol}: {e}")
                    results.append(None)

            impulses_detected = 0
            successful_tokens = 0

            print(f"\n📊 РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ:")
            print("-" * 50)

            for (symbol, address), result in zip(TOKENS.items(), results):
                if result is None:
                    print(f"  {symbol}: ❌ Нет данных")
                    continue

                successful_tokens += 1
                old_price = self.current_prices.get(symbol)
                self.current_prices[symbol] = result

                # проверка на импульс
                impulse, base_price, impulse_price = self.impulse_detector.update_price(symbol, result)

                if impulse:
                    impulses_detected += 1

                    # логируем импульс (в процентах тоже)
                    file_logger.log_impulse(symbol, impulse, result, base_price, impulse_price)

                    print(f"⚡ IMPULSE {symbol}: ${result:.8f} ({impulse:+.2%})")
                    print(f"   База: ${base_price:.8f} → Импульс: ${impulse_price:.8f}")

                    # запускаем CEX мониторинг
                    asyncio.create_task(
                        self.cex_monitor.track_cex_after_impulse(symbol, base_price, impulse_price)
                    )

                else:
                    # обычное обновление
                    if old_price and old_price > 0:
                        change = ((result - old_price) / old_price) * 100
                        arrow = "🔼" if change > 0 else "🔻"

                        if abs(change) >= 0.5:
                            print(f"  {symbol}: ${result:.8f} ({change:+.2f}% {arrow})")
                        else:
                            print(f"  {symbol}: ${result:.8f}")
                    else:
                        print(f"  {symbol}: ${result:.8f}")

            print(f"\n📈 ИТОГИ: Успешно {successful_tokens}/{len(TOKENS)} | Импульсы: {impulses_detected}")

            request_logger.print_summary()

            return impulses_detected
