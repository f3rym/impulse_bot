import aiohttp
import asyncio
from logger import file_logger
from config import PROXIES, USE_PROXIES, SETTINGS, LBANK_SYMBOL_MAPPING


class CEXMonitor:
    def __init__(self):
        self.cex_prices = {}
        self.active_monitoring = {}
        self.proxy_index = 0
        self.failed_proxies = set()
        
        # Кэш для символов LBank (чтобы не запрашивать каждый раз)
        self.lbank_symbols_cache = None
        # Маппинг символов для LBank
        self.lbank_symbol_mapping = LBANK_SYMBOL_MAPPING

    # ——————————————————————————————————————————
    def get_proxy(self):
        if not USE_PROXIES or not PROXIES:
            return None

        if len(self.failed_proxies) >= len(PROXIES):
            self.failed_proxies.clear()
            file_logger.print_status("🔄 Сброс нерабочих прокси")

        proxy = PROXIES[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(PROXIES)
        return proxy

    def mark_proxy_failed(self, proxy):
        if proxy:
            self.failed_proxies.add(proxy)

    # ——————————————————————————————————————————
    # LBank API методы
    # ——————————————————————————————————————————
    
    async def fetch_lbank_symbols(self, session):
        if self.lbank_symbols_cache:
            return self.lbank_symbols_cache
        
        url = "https://api.lbank.info/v2/currencyPairs.do"
    
        try:
            async with session.get(url, timeout=10, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict) and 'data' in data:
                        symbols = data['data']
                    else:
                        symbols = data
                    
                    self.lbank_symbols_cache = symbols
                    file_logger.print_status(f"✅ Получено {len(symbols)} символов с LBank")
                    return symbols
        except Exception as e:
            file_logger.print_status(f"❌ Ошибка получения символов LBank: {e}")
        return []

    def find_lbank_symbol(self, symbol, all_symbols):

        # Пробуем маппинг из конфига
        if symbol in self.lbank_symbol_mapping:
            mapped_symbol = self.lbank_symbol_mapping[symbol]
            if mapped_symbol in all_symbols:
                file_logger.print_status(f"✅ Найден маппинг для {symbol} -> {mapped_symbol}")
                return mapped_symbol
            else:
                file_logger.print_status(f"⚠️ Маппинг {mapped_symbol} не найден на LBank")

        # Пробуем автоматические варианты
        variants = [
            f"{symbol.lower()}_usdt",
            f"{symbol.lower()}usdt",
            symbol.lower()
        ]
        
        for variant in variants:
            if variant in all_symbols:
                file_logger.print_status(f"✅ Автоматически найден символ {symbol} -> {variant}")
                return variant
                
        file_logger.print_status(f"❌ Символ {symbol} не найден на LBank")
        return None

    async def fetch_lbank_spot(self, session, symbol):

        all_symbols = await self.fetch_lbank_symbols(session)
        if not all_symbols:
            file_logger.print_status(f"❌ Не удалось получить список символов LBank для {symbol}")
            return None
        
    # Ищем подходящий символ
        lbank_symbol = self.find_lbank_symbol(symbol, all_symbols)
        if not lbank_symbol:
            return None

        url = "https://api.lbank.info/v2/ticker.do"
        params = {'symbol': lbank_symbol}
    
        proxy = self.get_proxy() if USE_PROXIES else None
    
        try:
            async with session.get(
                url,
                params=params,
                timeout=10,
                proxy=proxy,
                ssl=False
            ) as response:

                if response.status == 403:
                    self.mark_proxy_failed(proxy)
                    file_logger.print_status(f"❌ LBank 403 Forbidden для {symbol}")
                    return None

                if response.status != 200:
                    file_logger.print_status(f"❌ LBank HTTP {response.status} для {symbol}")
                    return None

                data = await response.json()
            
            # Обрабатываем новый формат ответа:
            # {
            #   "msg":"Success",
            #   "result":"true", 
            #   "data":[
            #     {
            #       "symbol":"bonk_usdt",
            #       "ticker":{
            #         "high":0.00000987,
            #         "vol":334882456835,
            #         "low":0.00000941,
            #         "change":0.21,
            #         "turnover":3236786.2791,
            #         "latest":0.00000949
            #       }
            #     }
            #   ],
            #   "error_code":0,
            #   "ts":1764170058765
            # }
            
                if (data.get('result') == 'true' and 
                    'data' in data and 
                    len(data['data']) > 0 and
                    'ticker' in data['data'][0] and
                    'latest' in data['data'][0]['ticker']):
                
                    price = float(data['data'][0]['ticker']['latest'])
                    file_logger.print_status(f"✅ LBank {symbol}: ${price:.8f}")
                    return price
                else:
                    file_logger.print_status(f"❌ Нет данных цены для {symbol} на LBank")
                    return None
        except Exception as e:
            file_logger.print_status(f"❌ Ошибка LBank для {symbol}: {e}")
            return None
    # ——————————————————————————————————————————
    # Gate.io методы (остаются как были)
    # ——————————————————————————————————————————
    
    async def _fetch_gateio_price(self, session, url, params, symbol, api_name):
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }

        proxy = self.get_proxy() if USE_PROXIES else None

        try:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=10,
                proxy=proxy,
                ssl=False
            ) as response:

                if response.status == 403:
                    self.mark_proxy_failed(proxy)
                    return None

                if response.status != 200:
                    file_logger.print_status(
                        f"❌ Gate.io {api_name} HTTP {response.status} — {symbol}"
                    )
                    return None

                data = await response.json()

                if not data:
                    return None

                last = data[0].get("last")
                if not last:
                    return None

                price = float(last)
                file_logger.print_status(f"✅ Gate.io {api_name} {symbol}: ${price:.8f}")
                return price

        except Exception as e:
            file_logger.print_status(f"❌ Ошибка Gate.io {api_name} для {symbol}: {e}")
            return None

    async def fetch_gateio_futures(self, session, symbol):
        gate_symbol = f"{symbol}_USDT"
        return await self._fetch_gateio_price(
            session,
            "https://api.gateio.ws/api/v4/futures/usdt/tickers",
            {"contract": gate_symbol},
            symbol,
            "Futures"
        )

    async def fetch_gateio_spot(self, session, symbol):
        gate_symbol = f"{symbol}_USDT"
        return await self._fetch_gateio_price(
            session,
            "https://api.gateio.ws/api/v4/spot/tickers",
            {"currency_pair": gate_symbol},
            symbol,
            "Spot"
        )

    # ——————————————————————————————————————————
    # Основные методы мониторинга
    # ——————————————————————————————————————————
    
    async def check_symbol_availability(self, symbol):
        """Проверяет доступность символа на всех CEX"""
        file_logger.print_status(f"🔍 Проверка доступности {symbol}...")

        connector = aiohttp.TCPConnector(ssl=False, limit=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Запускаем все проверки параллельно
            tasks = [
                self.fetch_gateio_futures(session, symbol),
                self.fetch_gateio_spot(session, symbol),
                self.fetch_lbank_spot(session, symbol)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Обрабатываем результаты
        result = {
            "gateio_futures": not isinstance(results[0], Exception) and results[0] is not None,
            "gateio_spot": not isinstance(results[1], Exception) and results[1] is not None,
            "lbank_spot": not isinstance(results[2], Exception) and results[2] is not None
        }

        return result

    async def monitor_cex_prices(self, symbol):
        """Получает цены со всех CEX бирж"""
        connector = aiohttp.TCPConnector(ssl=False, limit=10)

        async with aiohttp.ClientSession(connector=connector) as session:
            # Запускаем все запросы параллельно
            tasks = [
                self.fetch_gateio_futures(session, symbol),
                self.fetch_gateio_spot(session, symbol),
                self.fetch_lbank_spot(session, symbol)
            ]
            
            futures_price, spot_price, lbank_price = await asyncio.gather(
                *tasks, return_exceptions=True
            )

        # Собираем результаты
        result = {}
        if not isinstance(futures_price, Exception) and futures_price is not None:
            result["gateio_futures"] = futures_price
        if not isinstance(spot_price, Exception) and spot_price is not None:
            result["gateio_spot"] = spot_price
        if not isinstance(lbank_price, Exception) and lbank_price is not None:
            result["lbank_spot"] = lbank_price

        self.cex_prices[symbol] = result
        return result

    async def track_cex_after_impulse(self, symbol, base_price, impulse_price):
        """Трекинг цен на CEX после импульса"""
        if symbol in self.active_monitoring:
            return

        self.active_monitoring[symbol] = True

        try:
            intervals = SETTINGS["cex_check_intervals"]

            file_logger.print_status(
                f"🎯 CEX мониторинг {symbol}, "
                f"импульс: {(impulse_price - base_price) / base_price:+.2%}"
            )

            # Проверяем доступность
            availability = await self.check_symbol_availability(symbol)
            available = [ex for ex, ok in availability.items() if ok]

            if not available:
                file_logger.print_status(f"❌ {symbol} не найден на CEX биржах")
                return

            file_logger.print_status("📊 Доступно на: " + ", ".join(available))

            # Цикл мониторинга
            for interval in intervals:
                await asyncio.sleep(interval)

                cex_data = await self.monitor_cex_prices(symbol)
                if not cex_data:
                    file_logger.print_status(f"{interval} сек — ❌ нет данных")
                    continue

                # Собираем данные для записи
                record = {}
                for ex, price in cex_data.items():
                    change_base = (price - base_price) / base_price
                    change_imp = (price - impulse_price) / impulse_price

                    record[ex] = {
                        "price": price,
                        "change_from_base": change_base,
                        "change_from_impulse": change_imp
                    }

                # Запись в лог
                file_logger.log_cex_data(
                    symbol,
                    base_price,
                    impulse_price,
                    record,
                    interval
                )

                # Вывод в консоль
                line = f"{interval} сек: "
                for ex, d in record.items():
                    line += (
                        f"{ex} {d['change_from_base']:+.2%}  "
                        f"({d['change_from_impulse']:+.2%})  "
                    )

                print(line)

            file_logger.print_status(f"✅ Мониторинг CEX завершен: {symbol}")

        finally:
            if symbol in self.active_monitoring:
                del self.active_monitoring[symbol]

    # ——————————————————————————————————————————
    # Дополнительные методы для отладки
    # ——————————————————————————————————————————
    
    async def check_lbank_availability(self):
        """Проверяет доступность всех монет из маппинга на LBank"""
        file_logger.print_status("🔍 Проверка доступности монет на LBank...")
        
        connector = aiohttp.TCPConnector(ssl=False, limit=10)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            all_symbols = await self.fetch_lbank_symbols(session)
            if not all_symbols:
                file_logger.print_status("❌ Не удалось получить список символов LBank")
                return []
                
            available = []
            unavailable = []
            
            for symbol in self.lbank_symbol_mapping.keys():
                lbank_symbol = self.find_lbank_symbol(symbol, all_symbols)
                if lbank_symbol:
                    available.append(f"{symbol} -> {lbank_symbol}")
                else:
                    unavailable.append(symbol)
                    
            file_logger.print_status(f"\n📊 Доступность монет на LBank:")
            file_logger.print_status(f"✅ Доступно ({len(available)}):")
            for item in available:
                file_logger.print_status(f"   {item}")
                
            if unavailable:
                file_logger.print_status(f"❌ Недоступно ({len(unavailable)}):")
                for symbol in unavailable:
                    file_logger.print_status(f"   {symbol}")
                    
            return available