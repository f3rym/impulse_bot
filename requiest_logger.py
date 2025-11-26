import time
import json
from datetime import datetime

class RequestLogger:
    def __init__(self):
        self.requests = []
        self.success_count = 0
        self.fail_count = 0
        
    def log_request(self, url, proxy, method="GET", status=None, response_time=None, error=None):
        """Логируем детали запроса"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        request_info = {
            'timestamp': timestamp,
            'method': method,
            'url': url,
            'proxy': self._safe_proxy_display(proxy),
            'status': status,
            'response_time': response_time,
            'error': error
        }
        
        self.requests.append(request_info)
        
        # Выводим в консоль
        self._print_request(request_info)
        
        # Обновляем счетчики (ФИКС: обрабатываем строковые статусы)
        if status == 200 or status == '200' or status == 'success':
            self.success_count += 1
        elif status is not None and status != 'TIMEOUT' and status != 'ERROR' and status != 'PROXY_ERROR':
            # Если статус не None и не строковая ошибка, считаем неудачей
            try:
                status_int = int(status)
                if status_int >= 400:
                    self.fail_count += 1
                else:
                    self.success_count += 1
            except (ValueError, TypeError):
                # Если не можем преобразовать в число, считаем неудачей
                self.fail_count += 1
        else:
            self.fail_count += 1
            
    def _safe_proxy_display(self, proxy):
        """Безопасное отображение прокси (скрываем пароль)"""
        if not proxy:
            return "Без прокси"
        
        # Скрываем пароль в логах
        if ':pass1234@' in proxy:
            return proxy.replace(':pass1234@', ':****@')
        return proxy
    
    def _print_request(self, request_info):
        """Красиво выводим информацию о запросе"""
        timestamp = request_info['timestamp']
        method = request_info['method']
        url_short = self._shorten_url(request_info['url'])
        proxy_short = self._shorten_proxy(request_info['proxy'])
        
        status = request_info['status']
        response_time = request_info['response_time']
        error = request_info['error']
        
        # Цветовая схема (ФИКС: обрабатываем строковые статусы)
        status_color = "🟡"  # по умолчанию желтый
        
        try:
            if status == 200 or status == '200':
                status_color = "🟢"
            elif isinstance(status, int) and status >= 400:
                status_color = "🔴"
            elif isinstance(status, str) and status.isdigit() and int(status) >= 400:
                status_color = "🔴"
            elif status in ['TIMEOUT', 'ERROR', 'PROXY_ERROR']:
                status_color = "🔴"
        except:
            pass
        
        # Основная строка
        main_line = f"{timestamp} | {method:6} | {url_short:40} | {proxy_short:30}"
        
        # Статус и время
        if status:
            main_line += f" | {status_color} {status}"
        if response_time:
            main_line += f" | {response_time:.2f}s"
        
        print(main_line)
        
        # Дополнительная информация (ошибки)
        if error:
            print(f"    └─ 🔴 ОШИБКА: {error}")
    
    def _shorten_url(self, url, max_length=40):
        """Сокращаем URL для отображения"""
        if len(url) <= max_length:
            return url
        
        # Оставляем начало и конец URL
        parts = url.split('/')
        if len(parts) > 4:
            return parts[0] + '//' + parts[2] + '/.../' + parts[-1]
        else:
            return url[:max_length-3] + '...'
    
    def _shorten_proxy(self, proxy, max_length=30):
        """Сокращаем прокси для отображения"""
        if len(proxy) <= max_length:
            return proxy
        
        # Оставляем только важные части
        if '@' in proxy:
            user_part, host_part = proxy.split('@', 1)
            # Сокращаем user часть
            if len(user_part) > 15:
                user_part = user_part[:12] + '...'
            short_proxy = user_part + '@' + host_part
        else:
            short_proxy = proxy
        
        if len(short_proxy) > max_length:
            return '...' + short_proxy[-(max_length-3):]
        
        return short_proxy
    
    def print_summary(self):
        """Печатаем статистику запросов"""
        print(f"\n📊 СТАТИСТИКА ЗАПРОСОВ:")
        print(f"   Успешных: {self.success_count}")
        print(f"   Неудачных: {self.fail_count}")
        print(f"   Всего: {len(self.requests)}")
        
        if self.requests:
            success_rate = (self.success_count / len(self.requests)) * 100
            print(f"   Успешность: {success_rate:.1f}%")

# Глобальный логгер
logger = RequestLogger()