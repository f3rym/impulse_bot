import json
from collections import defaultdict
import os

class StatsAnalyzer:
    def __init__(self):
        self.impulse_data = []
        self.cex_data = []
    
    def load_impulse_data(self, filename='logs/impulses.jsonl'):
        try:
            if not os.path.exists(filename):
                print("Файл с импульсами не найден")
                return
                
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self.impulse_data.append(data)
            print(f"📈 Загружено импульсов: {len(self.impulse_data)}")
        except Exception as e:
            print(f"Ошибка загрузки импульсов: {e}")
    
    def load_cex_data(self, filename='logs/cex_comparison.jsonl'):
        try:
            if not os.path.exists(filename):
                print("Файл с CEX данными не найден")
                return
                
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self.cex_data.append(data)
            print(f"📊 Загружено CEX записей: {len(self.cex_data)}")
        except Exception as e:
            print(f"Ошибка загрузки CEX данных: {e}")
    
    def analyze_arbitrage_opportunities(self):
        opportunities = defaultdict(list)
        
        for cex_record in self.cex_data:
            token = cex_record['token']
            
            if 'cex_data' in cex_record:
                for exchange, data in cex_record['cex_data'].items():
                    if abs(data['change_from_base']) >= 0.02:  # 2% порог
                        opportunities[token].append({
                            'exchange': exchange,
                            'interval': cex_record['interval_sec'],
                            'difference': data['change_from_base'],
                            'cex_price': data['price'],
                            'dex_price': cex_record['base_price'],
                            'timestamp': cex_record['time']
                        })
        
        return opportunities
    
    def calculate_average_delays(self):
        delays = defaultdict(list)
        
        for cex_record in self.cex_data:
            token = cex_record['token']
            interval = cex_record['interval_sec']
            
            if 'cex_data' in cex_record:
                for exchange, data in cex_record['cex_data'].items():
                    if abs(data['change_from_base']) >= 0.01:
                        delays[exchange].append(interval)
        
        avg_delays = {}
        for exchange, delay_list in delays.items():
            if delay_list:
                sorted_delays = sorted(delay_list)
                avg_delays[exchange] = sorted_delays[len(sorted_delays) // 2]
        
        return avg_delays
    
    def generate_report(self):
        self.load_impulse_data()
        self.load_cex_data()
        
        print("\n" + "="*60)
        print("ОТЧЕТ ПО СТАТИСТИКЕ АРБИТРАЖА")
        print("="*60)
        
        print(f"📈 Всего импульсов: {len(self.impulse_data)}")
        print(f"📊 Всего CEX записей: {len(self.cex_data)}")
        
        # Анализ CEX данных
        if self.cex_data:
            total_cex_checks = sum(1 for record in self.cex_data if 'cex_data' in record)
            print(f"🔍 Всего проверок CEX: {total_cex_checks}")
        
        delays = self.calculate_average_delays()
        if delays:
            print("\n⏱️ СРЕДНИЕ ЗАДЕРЖКИ DEX → CEX:")
            for exchange, delay in delays.items():
                print(f"   {exchange:15}: {delay} сек")
        
        opportunities = self.analyze_arbitrage_opportunities()
        if opportunities:
            print(f"\n💰 АРБИТРАЖНЫЕ ВОЗМОЖНОСТИ (>2%):")
            profitable_count = 0
            total_opportunities = 0
            
            for token, opps in opportunities.items():
                if opps:
                    profitable_count += 1
                    total_opportunities += len(opps)
                    print(f"   {token}: {len(opps)} случаев")
                    for opp in opps[:2]:  # Показываем первые 2 случая
                        print(f"     - {opp['exchange']} ({opp['interval']}сек): {opp['difference']:+.2%}")
            
            print(f"\n🎯 ИТОГО: {profitable_count} токенов, {total_opportunities} арбитражных случаев")
            
            if delays:
                fastest_exchange = min(delays, key=delays.get)
                print(f"⚡ Самая быстрая биржа: {fastest_exchange} ({delays[fastest_exchange]}сек)")
        else:
            print(f"\n❌ Арбитражные возможности не обнаружены")