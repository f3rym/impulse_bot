import asyncio
import time
from detector import ImpulseDetector
from dex_monitor import DexMonitor
from cex_monitor import CEXMonitor
from stats_analyzer import StatsAnalyzer
from logger import file_logger as logger
from config import SETTINGS, CEX_EXCHANGES

class CryptoMonitor:
    def __init__(self):
        self.impulse_detector = ImpulseDetector(threshold=SETTINGS['impulse_threshold'])
        self.cex_monitor = CEXMonitor()
        self.dex_monitor = DexMonitor(self.impulse_detector, self.cex_monitor)
        
        self.stats = {
            'start_time': None,
            'total_cycles': 0,
            'total_impulses': 0
        }
        self.is_running = True
    
    async def run(self):
        self.stats['start_time'] = time.time()
        logger.print_status("🚀 Старт мониторинга (публичные API)")
        logger.print_status(f"⚙️  Скорость сканирования: {SETTINGS['scan_frequency']} сек")
        logger.print_status(f"⚙️  Порог импульса: {SETTINGS['impulse_threshold']*100}%")
        logger.print_status(f"⚙️  CEX бирж: {len(CEX_EXCHANGES)}")
        logger.print_status("💡 Для остановки нажмите Ctrl+C")
        
        try:
            while self.is_running:
                cycle_start = time.time()
                self.stats['total_cycles'] += 1
                
                impulses = await self.dex_monitor.monitor_all_tokens()
                self.stats['total_impulses'] += impulses
                
                execution_time = time.time() - cycle_start
                wait_time = SETTINGS['scan_frequency'] - execution_time
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
  
                    
        except KeyboardInterrupt:
            await self.shutdown(" Остановка по Ctrl+C")
        except Exception as e:
            await self.shutdown(f"❌ Ошибка: {e}")
    
    async def shutdown(self, message):
        """Корректное завершение работы"""
        logger.print_status(message)
        self.is_running = False
        
        
        self._print_final_stats()
        
        try:
            analyzer = StatsAnalyzer()
            analyzer.generate_report()
        except Exception as e:
            logger.print_status(f"⚠️  Ошибка при генерации отчета: {e}")
    
    def _print_final_stats(self):
        if self.stats['start_time']:
            uptime = time.time() - self.stats['start_time']
            logger.print_status(f"📊 Статистика:")
            logger.print_status(f"  Время работы: {uptime:.1f} сек")
            logger.print_status(f"  Циклов: {self.stats['total_cycles']}")
            logger.print_status(f"  Импульсов: {self.stats['total_impulses']}")

def main():
    monitor = CryptoMonitor()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(monitor.run())
        except KeyboardInterrupt:
            print("\n")  
            loop.run_until_complete(monitor.shutdown("🛑 Программа остановлена"))
        finally:
            loop.close()
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()