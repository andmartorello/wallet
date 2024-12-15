class TransactionProcessor:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def load_fiat_balance(self):
        fiat_data = self.data_manager.load_fiat_transactions()
        eur_balance = fiat_data.get("EUR_Balance", 0)
        fiat_transactions = fiat_data.get("Transactions", [])
        eur_balance, total_invested = self.process_fiat_transactions(fiat_transactions, eur_balance)
        return eur_balance, total_invested, fiat_transactions

    def process_fiat_transactions(self, fiat_transactions, initial_eur_balance):
        eur_balance = initial_eur_balance
        total_invested = 0  
        for tx in fiat_transactions:
            amount = float(tx["Filled Amount"].replace(',', '.').split()[0])
            if tx["Type"] == "Top Up FIAT":
                eur_balance += amount  
                total_invested += amount  
            elif tx["Type"] == "Withdraw FIAT":
                eur_balance -= amount  
                total_invested -= amount  
        return eur_balance, total_invested

    def process_crypto_transactions(self, transactions, eur_balance):
        balances = {}
        avg_prices = {}
        avg_prices_usd = {}
        total_units_for_avg = {}
        usdt_balance = 0.0

        for tx in transactions:
            pair = tx["Pair"]
            side = tx["Side"]
            price = float(tx["Price"].split()[0]) if tx["Price"].split()[0].replace(".", "", 1).isdigit() else 0.0
            order_amount = float(tx["Order Amount"].split()[0])
            filled_amount = float(tx["Filled Amount"].split()[0])
            executed_amount = float(tx["Executed Amount"].split()[0])
            trade_fee = tx["Trade Fee"]
            info = tx.get("Info", "Transazione")  

            # Verifica se la transazione è di tipo "Earn" per escluderla solo dal saldo investito
            is_earn = tx.get("Info") == "Earn"

            fee_amount = float(trade_fee.split()[0]) if trade_fee.split()[0].replace(".", "", 1).isdigit() else 0.0
            fee_currency = trade_fee.split()[1]
            
            if fee_currency == pair.split("/")[0]:
                filled_amount -= fee_amount
            
            base_currency = pair.split("/")[0]
            quote_currency = pair.split("/")[1]

            if info == "Etf":
                etf_currency = f"ETF_{base_currency}"  
                if etf_currency not in balances:
                    balances[etf_currency] = 0
                    avg_prices[etf_currency] = 0
                    total_units_for_avg[etf_currency] = 0

                if side == "Buy" and not is_earn:  # Esclude "Earn" dal totale investito
                    balances[etf_currency] += filled_amount
                    avg_prices[etf_currency] += executed_amount
                    total_units_for_avg[etf_currency] += filled_amount
                    eur_balance -= executed_amount  
                elif side == "Sell":
                    balances[etf_currency] -= filled_amount
                    avg_prices[etf_currency] -= executed_amount
                    total_units_for_avg[etf_currency] -= filled_amount
                    eur_balance += executed_amount - fee_amount  

            else:
                if base_currency not in balances:
                    balances[base_currency] = 0
                    avg_prices[base_currency] = 0
                    avg_prices_usd[base_currency] = 0
                    total_units_for_avg[base_currency] = 0

                if side == "Buy" and not is_earn:
                    if pair == "USDT/EUR":
                        balances[base_currency] += filled_amount
                        avg_prices[base_currency] += executed_amount
                        total_units_for_avg[base_currency] += filled_amount
                        eur_balance -= executed_amount
                        usdt_balance += filled_amount
                    else:
                        balances[base_currency] += filled_amount
                        if price > 0:
                            avg_prices_usd[base_currency] += executed_amount
                            total_units_for_avg[base_currency] += filled_amount
                            usdt_balance -= executed_amount

                elif side == "Sell":
                    if pair == "USDT/EUR":
                        balances[base_currency] -= order_amount
                        avg_prices[base_currency] -= executed_amount
                        total_units_for_avg[base_currency] -= order_amount
                        eur_balance += executed_amount - fee_amount
                        usdt_balance -= filled_amount
                    else:
                        balances[base_currency] -= filled_amount
                        avg_prices_usd[base_currency] -= executed_amount
                        total_units_for_avg[base_currency] -= filled_amount
                        usdt_balance += executed_amount - fee_amount

        # Calcolo dei prezzi medi
        for currency in balances:
            if total_units_for_avg[currency] > 0:
                if currency == 'USDT':
                    avg_prices[currency] = avg_prices[currency] / abs(total_units_for_avg[currency])
                elif currency.startswith('ETF_'):
                    avg_prices[currency] = avg_prices[currency] / abs(total_units_for_avg[currency])
                else:
                    avg_prices_usd[currency] = avg_prices_usd[currency] / abs(total_units_for_avg[currency])

        usdt_avg_price_eur = avg_prices.get('USDT', 1)
        for currency in avg_prices_usd:
            if currency != 'USDT' and usdt_avg_price_eur > 0:
                avg_prices[currency] = avg_prices_usd[currency] * usdt_avg_price_eur

        return balances, avg_prices, avg_prices_usd, eur_balance, usdt_balance
