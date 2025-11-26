from datetime import datetime
from collections import deque

class ImpulseDetector:
    def __init__(self, threshold=0.15): 
        self.threshold = threshold
        self.price_history = {}
        self.base_prices = {}  
    
    def update_price(self, token, new_price):
        now = datetime.now()
        
        if token not in self.price_history:
            self.price_history[token] = deque(maxlen=10)
        
        history = self.price_history[token]
        history.append({
            'timestamp': now,
            'price': new_price
        })
        
        if len(history) >= 2:
            oldest_price = history[0]['price']
            if oldest_price > 0:
                price_change = (new_price - oldest_price) / oldest_price
                
                if abs(price_change) >= self.threshold:
                    self.base_prices[token] = oldest_price
                    return price_change, oldest_price, new_price
        
        return None, None, None
    
    def get_base_price(self, token):
        return self.base_prices.get(token)
    
    def get_recent_prices(self, token):
        if token in self.price_history:
            return list(self.price_history[token])
        return []