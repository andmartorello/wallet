import json
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import requests

# ======================= DataManager Class =======================

class DataManager:
    def __init__(self):
        self.crypto_transactions_path = "data/crypto_transactions.json"
        self.fiat_transactions_path = "data/fiat_transactions.json"
        self.crypto_valute_path = "data/crypto_valute.json"
        self.etf_valute_path = "data/etf_valute.json"
        self.percentuali_target_path = "data/percentuali_target.json"

        self.manual_etf_prices = self.load_manual_etf_prices()
        self.percentuali_target = self.load_percentuali_target()
        self.crypto_mapping = self.load_crypto_valute_mapping()
        self.etf_mapping = self.load_etf_valute_mapping()

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
        with open(self.fiat_transactions_path, 'r') as f:
            fiat_data = json.load(f)
        return fiat_data

    def save_fiat_transactions(self, fiat_data):
        with open(self.fiat_transactions_path, 'w') as f:
            json.dump(fiat_data, f, indent=4)

    def update_etf_price(self, etf_name, price):
        self.manual_etf_prices[etf_name] = price
        with open(self.etf_valute_path, 'w') as f:
            json.dump(self.manual_etf_prices, f, indent=4)

# ======================= TransactionProcessor Class =======================

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
        total_units_for_avg = {}
        usdt_balance = 0.0

        for tx in transactions:
            pair = tx["Pair"]
            side = tx["Side"]
            price = float(tx["Price"].split()[0])
            order_amount = float(tx["Order Amount"].split()[0])
            filled_amount = float(tx["Filled Amount"].split()[0])
            executed_amount = float(tx["Executed Amount"].split()[0])
            trade_fee = tx["Trade Fee"]
            info = tx.get("Info", "Transazione")  
            
            fee_amount = float(trade_fee.split()[0])
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

                if side == "Buy":
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
                    total_units_for_avg[base_currency] = 0

                if side == "Buy":
                    if pair == "USDT/EUR":
                        balances[base_currency] += filled_amount
                        avg_prices[base_currency] += executed_amount
                        total_units_for_avg[base_currency] += filled_amount
                        eur_balance -= executed_amount
                        usdt_balance += filled_amount
                    else:
                        balances[base_currency] += filled_amount
                        if price != 0:
                            avg_prices[base_currency] += executed_amount
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
                        avg_prices[base_currency] -= executed_amount
                        total_units_for_avg[base_currency] -= filled_amount
                        usdt_balance += executed_amount - fee_amount

        for currency in balances:
            if total_units_for_avg[currency] != 0:
                avg_prices[currency] = avg_prices[currency] / abs(total_units_for_avg[currency])

        return balances, avg_prices, eur_balance, usdt_balance

# ======================= Portfolio Class =======================

class Portfolio:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def calculate_percentage_gain(self, price_current, price_avg):
        if price_avg == 0 or price_current == 'N/A':
            return 'N/A'  
        return ((price_current - price_avg) / price_avg) * 100

# ======================= ApplicationGUI Class =======================

class ApplicationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Transazioni e Saldi")
        self.root.geometry("1000x500")
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Initialize DataManager and other classes
        self.data_manager = DataManager()
        self.transaction_processor = TransactionProcessor(self.data_manager)
        self.portfolio = Portfolio(self.data_manager)

        # Initialize variables
        self.balances = {}
        self.avg_prices = {}
        self.eur_balance = 0.0
        self.usdt_balance = 0.0
        self.total_invested = 0.0

        # Build GUI
        self.create_widgets()
        self.load_and_display_data()

    def create_widgets(self):
        # Left Frame
        self.left_frame = ttk.Frame(self.root)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.progress_frame = ttk.Frame(self.left_frame)
        self.progress_frame.pack(side="bottom", fill="both", expand=True, padx=5, pady=5)

        # Main Frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Top Frame
        self.top_frame = ttk.Frame(self.main_frame)
        self.top_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Bottom Frame
        self.bottom_frame = ttk.Frame(self.main_frame)
        self.bottom_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # FIAT Transactions Frame
        self.fiat_frame = ttk.LabelFrame(self.top_frame, text="Transazioni FIAT", padding=(10, 10), style="TLabelframe")
        self.fiat_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # Crypto Transactions Frame
        self.crypto_frame = ttk.LabelFrame(self.top_frame, text="Transazioni Crypto", padding=(10, 10), style="TLabelframe")
        self.crypto_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # FIAT Transactions List
        fiat_columns = ("Timestamp", "Type", "Filled Amount")
        self.fiat_list = ttk.Treeview(self.fiat_frame, columns=fiat_columns, show="headings", height=10)
        for col in fiat_columns:
            self.fiat_list.heading(col, text=col)
            self.fiat_list.column(col, minwidth=0, width=150)
        fiat_vscrollbar = ttk.Scrollbar(self.fiat_frame, orient="vertical", command=self.fiat_list.yview)
        self.fiat_list.configure(yscroll=fiat_vscrollbar.set)
        fiat_vscrollbar.pack(side="right", fill="y")
        self.fiat_list.pack(fill="both", expand=True)

        # Crypto Transactions List
        crypto_columns = ("Timestamp", "Pair", "Side", "Price", "Order Amount", "Filled Amount", "Executed Amount", "Info")
        self.crypto_list = ttk.Treeview(self.crypto_frame, columns=crypto_columns, show="headings", height=10)
        for col in crypto_columns:
            self.crypto_list.heading(col, text=col)
            self.crypto_list.column(col, minwidth=0, width=150)
        crypto_vscrollbar = ttk.Scrollbar(self.crypto_frame, orient="vertical", command=self.crypto_list.yview)
        self.crypto_list.configure(yscroll=crypto_vscrollbar.set)
        crypto_vscrollbar.pack(side="right", fill="y")
        self.crypto_list.pack(fill="both", expand=True)

        # Balances Text
        self.balances_text = tk.Text(self.bottom_frame, height=10, wrap="word", font=("Arial", 10), padx=10, pady=5)
        self.balances_text.pack(side="left", fill="both", expand=True)

        # Buttons
        self.create_buttons()

    def create_buttons(self):
        style = ttk.Style()
        style.configure("Small.TButton", font=("Arial", 8))

        add_fiat_button = ttk.Button(self.left_frame, text="Aggiungi FIAT", command=self.add_fiat_transaction, style="Small.TButton")
        add_fiat_button.pack(fill="x", padx=10, pady=5)
        add_fiat_button.config(width=10)

        add_crypto_button = ttk.Button(self.left_frame, text="Aggiungi Crypto", command=self.add_crypto_transaction, style="Small.TButton")
        add_crypto_button.pack(fill="x", padx=10, pady=5)
        add_crypto_button.config(width=10)

        delete_transaction_button = ttk.Button(self.left_frame, text="Elimina Transazione", command=self.delete_transaction, style="Small.TButton")
        delete_transaction_button.pack(fill="x", padx=10, pady=5)
        delete_transaction_button.config(width=10)

        modify_etf_button = ttk.Button(self.left_frame, text="Modifica Prezzo ETF", command=self.update_etf_price, style="Small.TButton")
        modify_etf_button.pack(fill="x", padx=10, pady=5)
        modify_etf_button.config(width=10)

    # ======================= Data Loading and Display =======================

    def load_and_display_data(self):
        crypto_transactions = self.data_manager.load_crypto_transactions()
        crypto_transactions.sort(key=lambda tx: datetime.strptime(tx["Timestamp"], "%b %d, %Y %H:%M:%S"))

        self.eur_balance, self.total_invested, fiat_transactions = self.transaction_processor.load_fiat_balance()
        fiat_transactions.sort(key=lambda tx: datetime.strptime(tx["Timestamp"], "%b %d, %Y %H:%M:%S"))

        self.display_crypto_transactions(crypto_transactions)
        self.display_fiat_transactions(fiat_transactions)

        self.balances, self.avg_prices, self.eur_balance, self.usdt_balance = self.transaction_processor.process_crypto_transactions(crypto_transactions, self.eur_balance)

        self.display_balances()
        self.display_percentages()

    def display_crypto_transactions(self, transactions):
        self.crypto_list.delete(*self.crypto_list.get_children())
        for tx in transactions:
            self.crypto_list.insert("", "end", values=(tx["Timestamp"], tx["Pair"], tx["Side"], tx["Price"], tx["Order Amount"], tx["Filled Amount"], tx["Executed Amount"], tx.get("Info", "Transazione")))

    def display_fiat_transactions(self, transactions):
        self.fiat_list.delete(*self.fiat_list.get_children())
        for tx in transactions:
            self.fiat_list.insert("", "end", values=(tx["Timestamp"], tx["Type"], tx["Filled Amount"]))

    # ======================= Transaction Management =======================

    def add_fiat_transaction(self):
        def save_fiat_transaction():
            timestamp = datetime.now().strftime("%b %d, %Y %H:%M:%S")
            tx_type = type_dropdown.get()
            filled_amount = filled_amount_entry.get()

            fiat_data = self.data_manager.load_fiat_transactions()
            fiat_data['Transactions'].append({
                "Timestamp": timestamp,
                "Type": tx_type,
                "Filled Amount": f"{filled_amount} EUR"
            })
            self.data_manager.save_fiat_transactions(fiat_data)

            fiat_window.destroy()
            self.load_and_display_data()

        fiat_window = tk.Toplevel(self.root)
        fiat_window.title("Aggiungi Transazione FIAT")
        
        tk.Label(fiat_window, text="Tipo di Transazione:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=5)
        type_dropdown = ttk.Combobox(fiat_window, values=["Top Up FIAT", "Withdraw FIAT"], state="readonly")
        type_dropdown.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(fiat_window, text="Importo (EUR):", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=10, pady=5)
        filled_amount_entry = ttk.Entry(fiat_window)
        filled_amount_entry.grid(row=1, column=1, padx=10, pady=5)

        save_button = ttk.Button(fiat_window, text="Aggiungi Transazione", command=save_fiat_transaction)
        save_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    def add_crypto_transaction(self):
        def save_crypto_transaction():
            pair = pair_entry.get()
            if '/' not in pair:
                messagebox.showerror("Errore", "La coppia deve essere nel formato BASE/QUOTE, ad es. BTC/USDT.")
                return

            timestamp = datetime.now().strftime("%b %d, %Y %H:%M:%S")
            side = side_dropdown.get()
            price = price_entry.get()
            order_amount = order_amount_entry.get()
            filled_amount = filled_amount_entry.get()
            executed_amount = executed_amount_entry.get()
            trade_fee = trade_fee_entry.get()
            info = info_dropdown.get()

            transactions = self.data_manager.load_crypto_transactions()
            transactions.append({
                "Timestamp": timestamp,
                "Pair": pair,
                "Side": side,
                "Price": f"{price} {pair.split('/')[1]}",
                "Order Amount": f"{order_amount} {pair.split('/')[0]}",
                "Filled Amount": f"{filled_amount} {pair.split('/')[0]}",
                "Executed Amount": f"{executed_amount} {pair.split('/')[1]}",
                "Trade Fee": f"{trade_fee} {pair.split('/')[0]}",
                "Info": info
            })
            self.data_manager.save_crypto_transactions(transactions)

            crypto_window.destroy()
            self.load_and_display_data()

        crypto_window = tk.Toplevel(self.root)
        crypto_window.title("Aggiungi Transazione Crypto/ETF")

        tk.Label(crypto_window, text="Coppia (es. BTC/USDT o VFEA/EUR):", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        pair_entry = ttk.Entry(crypto_window)
        pair_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(crypto_window, text="Tipo di Transazione:", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        side_dropdown = ttk.Combobox(crypto_window, values=["Buy", "Sell"], state="readonly")
        side_dropdown.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(crypto_window, text="Prezzo (EUR o USDT):", font=("Arial", 10, "bold")).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        price_entry = ttk.Entry(crypto_window)
        price_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(crypto_window, text="Quantità Ordinata:", font=("Arial", 10, "bold")).grid(row=3, column=0, padx=10, pady=5, sticky="w")
        order_amount_entry = ttk.Entry(crypto_window)
        order_amount_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(crypto_window, text="Quantità Eseguita:", font=("Arial", 10, "bold")).grid(row=4, column=0, padx=10, pady=5, sticky="w")
        filled_amount_entry = ttk.Entry(crypto_window)
        filled_amount_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(crypto_window, text="Importo Eseguito (EUR o USDT):", font=("Arial", 10, "bold")).grid(row=5, column=0, padx=10, pady=5, sticky="w")
        executed_amount_entry = ttk.Entry(crypto_window)
        executed_amount_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(crypto_window, text="Commissione di Scambio:", font=("Arial", 10, "bold")).grid(row=6, column=0, padx=10, pady=5, sticky="w")
        trade_fee_entry = ttk.Entry(crypto_window)
        trade_fee_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(crypto_window, text="Tipo di Transazione (Info):", font=("Arial", 10, "bold")).grid(row=7, column=0, padx=10, pady=5, sticky="w")
        info_dropdown = ttk.Combobox(crypto_window, values=["Transazione", "Earn", "Etf"], state="readonly")
        info_dropdown.grid(row=7, column=1, padx=10, pady=5, sticky="ew")

        save_button = ttk.Button(crypto_window, text="Aggiungi Transazione", command=save_crypto_transaction)
        save_button.grid(row=8, column=0, columnspan=2, padx=10, pady=20)

        crypto_window.grid_columnconfigure(1, weight=1)

    def delete_transaction(self):
        selected_fiat = self.fiat_list.selection()
        selected_crypto = self.crypto_list.selection()

        if selected_fiat:
            selected_item = self.fiat_list.item(selected_fiat)
            timestamp = selected_item['values'][0]

            fiat_data = self.data_manager.load_fiat_transactions()
            transactions = fiat_data['Transactions']
            index_to_delete = next((i for i, tx in enumerate(transactions) if tx['Timestamp'] == timestamp), None)
                
            if index_to_delete is not None:
                del transactions[index_to_delete]
                self.data_manager.save_fiat_transactions(fiat_data)

        elif selected_crypto:
            selected_item = self.crypto_list.item(selected_crypto)
            timestamp = selected_item['values'][0]

            transactions = self.data_manager.load_crypto_transactions()
            index_to_delete = next((i for i, tx in enumerate(transactions) if tx['Timestamp'] == timestamp), None)
                
            if index_to_delete is not None:
                del transactions[index_to_delete]
                self.data_manager.save_crypto_transactions(transactions)

        else:
            messagebox.showwarning("Errore", "Seleziona una transazione da eliminare.")

        self.load_and_display_data()

    def update_etf_price(self):
        def save_etf_price():
            etf_name = etf_name_entry.get()
            try:
                current_price = float(current_price_entry.get())
            except ValueError:
                messagebox.showerror("Errore", "Inserisci un valore valido per il prezzo.")
                return

            if etf_name in self.data_manager.manual_etf_prices:
                self.data_manager.update_etf_price(etf_name, current_price)
                etf_window.destroy()
                self.load_and_display_data()
                print(f"Interfaccia aggiornata per ETF: {etf_name}, Nuovo Valore: {current_price:.2f} EUR")
            else:
                messagebox.showerror("Errore", f"L'ETF '{etf_name}' non è stato trovato.")
                return

        etf_window = tk.Toplevel(self.root)
        etf_window.title("Modifica Prezzo ETF")

        tk.Label(etf_window, text="Nome ETF:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, pady=5)
        etf_name_entry = ttk.Entry(etf_window)
        etf_name_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(etf_window, text="Valore Attuale (EUR):", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=10, pady=5)
        current_price_entry = ttk.Entry(etf_window)
        current_price_entry.grid(row=1, column=1, padx=10, pady=5)

        save_button = ttk.Button(etf_window, text="Salva", command=save_etf_price)
        save_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    # ======================= Display Balances and Percentages =======================

    def display_balances(self):
        self.balances_text.delete(1.0, tk.END)  

        # Configurazione dei tag per la formattazione del testo
        self.balances_text.tag_configure("green", foreground="green", font=("Arial", 10, "bold"))
        self.balances_text.tag_configure("red", foreground="red", font=("Arial", 10, "bold"))
        self.balances_text.tag_configure("header", font=("Arial", 12, "bold", "underline"))
        self.balances_text.tag_configure("bold", font=("Arial", 10, "bold"))
        self.balances_text.tag_configure("normal", font=("Arial", 10))
        
        current_crypto_prices = self.data_manager.get_current_crypto_prices()

        total_invested_excluding_eur = self.total_invested - self.eur_balance
        total_current_value_eur = 0  

        # Aggiungi un'intestazione per le criptovalute
        self.balances_text.insert(tk.END, "Bilanci Criptovalute\n", "header")

        # Elaboriamo le crypto e USDT
        for currency, balance in self.balances.items():
            if currency != 'USDT' and not currency.startswith('ETF_'):
                avg_price = self.avg_prices.get(currency, 'N/A')
                coin_id = self.data_manager.crypto_mapping.get(f"{currency}/USDT", None)
                current_price_usd = current_crypto_prices.get(coin_id, {}).get('usd', 'N/A')
                current_price_eur = current_crypto_prices.get(coin_id, {}).get('eur', 'N/A')

                if current_price_eur != 'N/A':
                    total_current_value_eur += balance * current_price_eur

                percentage_gain = self.portfolio.calculate_percentage_gain(current_price_usd, avg_price)

                color = "green" if percentage_gain != 'N/A' and isinstance(percentage_gain, (int, float)) and percentage_gain > 0 else "red"
                
                self.balances_text.insert(tk.END, f"{currency}: ", "bold")
                self.balances_text.insert(tk.END, f"Unità: {balance:.6f}, Prezzo Medio: {avg_price:.2f}, Valore USD: {current_price_usd}, Valore EUR: {current_price_eur}, Guadagno/Perdita: ", "normal")
                
                if isinstance(percentage_gain, (int, float)):
                    self.balances_text.insert(tk.END, f"{percentage_gain:.2f}%\n", color)
                else:
                    self.balances_text.insert(tk.END, f"{percentage_gain}\n", color)

        # Aggiungi USDT
        avg_price_usdt = self.avg_prices.get('USDT', 'N/A')
        current_price_usdt = current_crypto_prices.get('tether', {}).get('eur', 'N/A')
        usdt_gain_percent = self.portfolio.calculate_percentage_gain(current_price_usdt, avg_price_usdt)

        total_current_value_eur += self.usdt_balance * current_price_usdt

        self.balances_text.insert(tk.END, "USDT: ", "bold")
        self.balances_text.insert(tk.END, f"Unità: {self.usdt_balance:.6f}, Prezzo Medio: {avg_price_usdt}, Valore USD: 1.0, Valore EUR: {current_price_usdt}, Guadagno/Perdita: ", "normal")
        
        if isinstance(usdt_gain_percent, (int, float)):
            self.balances_text.insert(tk.END, f"{usdt_gain_percent:.2f}%\n", "green" if usdt_gain_percent >= 0 else "red")
        else:
            self.balances_text.insert(tk.END, f"{usdt_gain_percent}\n", "green" if usdt_gain_percent >= 0 else "red")

        # Intestazione per gli ETF
        self.balances_text.insert(tk.END, "\nBilanci ETF\n", "header")

        # Elaborazione dei dati ETF
        for currency, balance in self.balances.items():
            if currency.startswith('ETF_'):
                avg_price = self.avg_prices.get(currency, 'N/A')
                
                etf_name = currency[4:]
                etf_current_value = self.data_manager.manual_etf_prices.get(etf_name, self.data_manager.etf_mapping.get(etf_name, 'N/A'))

                if isinstance(etf_current_value, (int, float)):
                    etf_current_value_str = f"{etf_current_value:,.2f} EUR"
                    gain_loss = self.portfolio.calculate_percentage_gain(etf_current_value, avg_price)
                    
                    color = "green" if isinstance(gain_loss, (int, float)) and gain_loss > 0 else "red"
                    gain_loss_str = f"{gain_loss:.2f}%" if isinstance(gain_loss, (int, float)) else gain_loss
                else:
                    etf_current_value_str = 'N/A'
                    gain_loss_str = 'N/A'
                    color = "normal"

                self.balances_text.insert(tk.END, f"{etf_name}: ", "bold")
                self.balances_text.insert(tk.END, f"Unità: {balance:.6f}, Prezzo Medio: {avg_price:.2f}, Valore Attuale: {etf_current_value_str}, Guadagno/Perdita: ", "normal")
                
                self.balances_text.insert(tk.END, f"{gain_loss_str}\n", color)

                if etf_current_value != 'N/A':
                    total_current_value_eur += balance * etf_current_value

        # Riepilogo del saldo in EUR
        self.balances_text.insert(tk.END, "\nSaldo Finale\n", "header")
        self.balances_text.insert(tk.END, f"Saldo finale in EUR: {self.eur_balance:,.2f} EUR\n", "bold")
        self.balances_text.insert(tk.END, f"Saldo totale investito in EUR (esclusi EUR): {total_invested_excluding_eur:,.2f} EUR\n", "bold")
        self.balances_text.insert(tk.END, f"Valore totale attuale in EUR (esclusi EUR): {total_current_value_eur:,.2f} EUR\n", "bold")

    def display_percentages(self):
        for widget in self.progress_frame.winfo_children():
            widget.destroy()

        current_crypto_prices = self.data_manager.get_current_crypto_prices()
        percentuali_target = self.data_manager.percentuali_target

        # Inizializziamo variabili per ETF, BTC, ETH, SOL e Altcoin
        total_etf_value = 0
        total_btc_value = 0
        total_eth_value = 0
        total_solana_value = 0
        total_altcoins_value = 0
        total_liquidity = self.eur_balance + self.usdt_balance * current_crypto_prices.get('tether', {}).get('eur', 0)

        etf_values = {}

        # Calcolo del valore degli ETF basato sul valore attuale in EUR
        for currency, balance in self.balances.items():
            if currency.startswith('ETF_'):
                etf_name = currency[4:]
                etf_current_value = self.data_manager.manual_etf_prices.get(etf_name, 0)
                etf_value = balance * etf_current_value
                etf_values[etf_name] = etf_value
                total_etf_value += etf_value

        # Calcolo del valore delle criptovalute
        for currency, balance in self.balances.items():
            current_price_eur = current_crypto_prices.get(self.data_manager.crypto_mapping.get(f"{currency}/USDT", ''), {}).get('eur', 0)
            if currency == 'BTC':
                total_btc_value = balance * current_price_eur
            elif currency == 'ETH':
                total_eth_value = balance * current_price_eur
            elif currency == 'SOL':
                total_solana_value = balance * current_price_eur
            elif currency != 'USDT' and not currency.startswith('ETF_'):
                total_altcoins_value += balance * current_price_eur

        # Valore totale del portafoglio in EUR
        total_portfolio_value = total_liquidity + total_etf_value + total_btc_value + total_eth_value + total_solana_value + total_altcoins_value

        def create_progressbar(label_text, value, target_value):
            label = tk.Label(self.progress_frame, text=f"{label_text} ({value:.2f}% / {target_value:.2f}%)", font=("Arial", 8, "bold"))
            label.pack(pady=2, anchor="w")
            progress = ttk.Progressbar(self.progress_frame, orient='horizontal', length=250, mode='determinate')
            progress['value'] = value
            progress.pack(pady=2, anchor="w")

        if total_portfolio_value > 0:
            # Calcolo delle percentuali
            liquidity_percent = (total_liquidity / total_portfolio_value) * 100
            btc_percent = (total_btc_value / total_portfolio_value) * 100
            eth_percent = (total_eth_value / total_portfolio_value) * 100
            solana_percent = (total_solana_value / total_portfolio_value) * 100
            altcoins_percent = (total_altcoins_value / total_portfolio_value) * 100

            create_progressbar(f"Liquidita (EUR e USDT): {total_liquidity:,.2f} EUR", liquidity_percent, percentuali_target["liquidita"])

            # Aggiungi le barre per ogni ETF
            for etf_name, etf_value in etf_values.items():
                etf_single_percent = (etf_value / total_portfolio_value) * 100
                etf_target = percentuali_target["etf"].get(etf_name, 0)
                create_progressbar(f"{etf_name}: {etf_value:,.2f} EUR", etf_single_percent, etf_target)

            create_progressbar(f"Bitcoin (BTC): {total_btc_value:,.2f} EUR", btc_percent, percentuali_target["BTC"])
            create_progressbar(f"Ethereum (ETH): {total_eth_value:,.2f} EUR", eth_percent, percentuali_target["ETH"])
            create_progressbar(f"Solana (SOL): {total_solana_value:,.2f} EUR", solana_percent, percentuali_target["SOL"])
            create_progressbar(f"Altcoin (resto): {total_altcoins_value:,.2f} EUR", altcoins_percent, percentuali_target["altcoin"])
        else:
            tk.Label(self.progress_frame, text="Nessun dato disponibile per creare le barre di progresso.", font=("Arial", 10, "bold")).pack(pady=5)

# ======================= Main Application =======================

if __name__ == "__main__":
    root = tk.Tk()
    app = ApplicationGUI(root)
    root.mainloop()
