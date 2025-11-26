# logger.py (упрощенная версия)
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

class Logger:
    def __init__(self):
        os.makedirs(LOGS_DIR, exist_ok=True)

    def _get_path(self, filename):
        return os.path.join(LOGS_DIR, filename)

    def log_impulse(self, token, price_change, curr_price, base_price, impulse_price):
        """Упрощенный лог импульса: время, монета, цена до/после, % изменения"""
        log = {
            'time': datetime.now().strftime("%H:%M:%S"),
            'token': token,
            'base_price': base_price,
            'impulse_price': impulse_price,
            'change_percent': round(price_change * 100, 2)  # Проценты с 2 знаками
        }
        self._write_to_file('impulses.jsonl', log)
        self.print_status(f"⚡ ИМПУЛЬС: {token} {price_change:+.2%}")

    def log_cex_data(self, token, base_price, impulse_price, cex_prices, interval):
        """Упрощенный лог CEX: время после импульса, монета, данные с бирж"""
        log = {
            'time_after_impulse': f"{interval}сек",
            'token': token,
            'dex_price': impulse_price,  # Цена на DEX в момент импульса
            'cex_prices': {}
        }
        
        for exchange, data in cex_prices.items():
            log['cex_prices'][exchange] = {
                'price': data['price'],
                'vs_base_percent': round(data['change_from_base'] * 100, 2),  # % от базовой цены
                'vs_impulse_percent': round(data['change_from_impulse'] * 100, 2)  # % от импульсной цены
            }

        self._write_to_file('cex_comparison.jsonl', log)
        self.print_status(f"📊 CEX данные: {token} через {interval}сек")

    def _write_to_file(self, filename, data):
        path = self._get_path(filename)
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            self.print_status(f"❌ Ошибка записи в {filename}: {e}")

    def print_status(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def clear_old_logs(self):
        try:
            files = ['impulses.jsonl', 'cex_comparison.jsonl', 'arbitrage.jsonl']
            for f in files:
                path = self._get_path(f)
                if os.path.exists(path):
                    os.remove(path)
                    self.print_status(f"🧹 Очищен файл: {f}")
        except Exception as e:
            self.print_status(f"⚠️ Не удалось очистить логи: {e}")

# Экспортируем объект
file_logger = Logger()