from dotenv import load_dotenv

load_dotenv()

TOKENS = {
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "POPCAT": "7GCBgQ6JgqiM5FmKqwbx4vxTfA2j7qwcVjYsvwRk7QpW", 
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
}

LBANK_SYMBOL_MAPPING = {

    "BONK": "bonk_usdt",
    "POPCAT": "popcat_usdt", 
    "WIF": "wif_usdt",
}

SETTINGS = {
    'scan_frequency': 10, # повторная попытка ловли импульса тайминг
    'impulse_threshold': 0.000001, # при каком проценте импульс ловим
    'cex_check_intervals': [5, 10, 30, 60] # тайминг по которому на сех бирже смотрим после импульса
}

CEX_EXCHANGES = ['gateio_spot', 'gateio_futures']

PROXIES = []
USE_PROXIES = False

def parse_proxy_line(line):
    try:
        line = line.strip()
        if not line:
            return None
            
        if '@' in line:
            credentials, hostport = line.split('@', 1)
            if ':' in credentials:
                user, password = credentials.split(':', 1)
            else:
                user = credentials
                password = 'pass1234'  
                
            if ':' in hostport:
                host, port = hostport.split(':', 1)
            else:
                host = hostport
                port = '2510'  
                
            proxy_url = f"http://{user}:{password}@{host}:{port}"
            return proxy_url
            
        else:
            if ':' in line:
                host, port = line.split(':', 1)
                return f"http://{host}:{port}"
            else:
                return f"http://{line}:2510"
                
    except Exception as e:
        print(f"❌ Ошибка парсинга прокси '{line}': {e}")
        return None

def load_proxies_from_file(filename='proxy.txt'):
    """Загружаем прокси из файла"""
    global PROXIES
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxy_url = parse_proxy_line(line)
                    if proxy_url:
                        PROXIES.append(proxy_url)
        
        print(f"✅ Загружено {len(PROXIES)} прокси из {filename}")
        
        if PROXIES:
            print("📋 Примеры прокси:")
            for i, proxy in enumerate(PROXIES[:3]):
                print(f"  {i+1}. {proxy}")
            if len(PROXIES) > 3:
                print(f"  ... и еще {len(PROXIES) - 3}")
                
    except Exception as e:
        print(f"❌ Ошибка загрузки прокси: {e}")
        PROXIES = []

load_proxies_from_file()