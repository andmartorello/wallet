class Portfolio:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def calculate_percentage_gain(self, price_current, price_avg):
        if price_avg == 0 or price_current == 'N/A':
            return 'N/A'  
        return ((price_current - price_avg) / price_avg) * 100
