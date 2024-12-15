import json
import requests
import dateparser

class DataManager:
    def __init__(self):
        self.crypto_transactions_path = "data/crypto_transactions.json"
        self.fiat_transactions_path = "data/fiat_transactions.json"
        self.crypto_valute_path = "data/crypto_valute.json"
        self.etf_valute_path = "data/etf_valute.json"
        self.percentuali_target_path = "data/percentuali_target.json"
        self.conto_deposito_path = "data/conto_deposito.json"
        self.immobili_data_path = "data/immobili.json"
        self.selling_prices_path = "data/selling_prices.json"

        self.manual_etf_prices = self.load_manual_etf_prices()
        self.percentuali_target = self.load_percentuali_target()
        self.crypto_mapping = self.load_crypto_valute_mapping()
        self.etf_mapping = self.load_etf_valute_mapping()
        self.conto_deposito = self.load_conto_deposito()  
        self.immobili_data = self.load_immobili_data()
        self.selling_prices = self.load_selling_prices()

    def load_immobili_data(self):
        try:
            with open(self.immobili_data_path, 'r') as f:
                immobili_data = json.load(f)
        except FileNotFoundError:
            immobili_data = {"Immobili": []}
            with open(self.immobili_data_path, 'w') as f:
                json.dump(immobili_data, f, indent=4)
        return immobili_data

    def save_immobili_data(self):
        with open(self.immobili_data_path, 'w') as f:
            json.dump(self.immobili_data, f, indent=4)

    def load_conto_deposito(self):
        try:
            with open(self.conto_deposito_path, 'r') as f:
                conto_deposito_data = json.load(f)
                for deposito in conto_deposito_data["Conto deposito"]:
                    # Usa dateparser.parse per convertire la data in un oggetto datetime
                    deposito["Scadenza"] = dateparser.parse(deposito["Scadenza"], languages=['it', 'en'])
                return conto_deposito_data
        except FileNotFoundError:
            return {"Conto deposito": []}


    
    def load_manual_etf_prices(self):
        with open(self.etf_valute_path, 'r') as f:
            etf_data = json.load(f)
        return etf_data

    def load_percentuali_target(self):
        with open(self.percentuali_target_path, 'r') as f:
            percentuali_target = json.load(f)
        return percentuali_target

    def load_crypto_valute_mapping(self):
        with open(self.crypto_valute_path, 'r') as f:
            crypto_mapping = json.load(f)
        return crypto_mapping

    def load_etf_valute_mapping(self):
        with open(self.etf_valute_path, 'r') as f:
            etf_mapping = json.load(f)
        return etf_mapping

    def load_selling_prices(self):
        try:
            with open(self.selling_prices_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_selling_prices(self, selling_prices):
        with open(self.selling_prices_path, 'w') as f:
            json.dump(selling_prices, f, indent=4)

    def get_current_crypto_prices(self):
        ids = ','.join(set(v for v in self.crypto_mapping.values() if isinstance(v, str)))
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd,eur"

        try:
            response = requests.get(url)
            response.raise_for_status()
            prices = response.json()
            return prices
        except requests.RequestException as e:
            print(f"Errore durante la richiesta API: {e}")
            return {}
    
    def load_crypto_transactions(self):
        with open(self.crypto_transactions_path, 'r') as f:
            crypto_transactions = json.load(f)
        return crypto_transactions

    def save_crypto_transactions(self, transactions):
        with open(self.crypto_transactions_path, 'w') as f:
            json.dump(transactions, f, indent=4)

    def load_fiat_transactions(self):
        try:
            with open(self.fiat_transactions_path, 'r') as f:
                fiat_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            fiat_data = {"Transactions": [], "EUR_Balance": 0}
            with open(self.fiat_transactions_path, 'w') as f:
                json.dump(fiat_data, f, indent=4)
        return fiat_data


    def save_fiat_transactions(self, fiat_data):
        with open(self.fiat_transactions_path, 'w') as f:
            json.dump(fiat_data, f, indent=4)

    def update_etf_price(self, etf_name, price):
        self.manual_etf_prices[etf_name] = price
        with open(self.etf_valute_path, 'w') as f:
            json.dump(self.manual_etf_prices, f, indent=4)
