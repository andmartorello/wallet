import json
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import requests
import dateparser

def datetime_to_string(obj):
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    raise TypeError("Tipo non serializzabile")

    
# ======================= DataManager Class =======================

class DataManager:
    def __init__(self):
        self.crypto_transactions_path = "data/crypto_transactions.json"
        self.fiat_transactions_path = "data/fiat_transactions.json"
        self.crypto_valute_path = "data/crypto_valute.json"
        self.etf_valute_path = "data/etf_valute.json"
        self.percentuali_target_path = "data/percentuali_target.json"
        self.conto_deposito_path = "data/conto_deposito.json"
        self.immobili_data_path = "data/immobili.json"

        self.manual_etf_prices = self.load_manual_etf_prices()
        self.percentuali_target = self.load_percentuali_target()
        self.crypto_mapping = self.load_crypto_valute_mapping()
        self.etf_mapping = self.load_etf_valute_mapping()
        self.conto_deposito = self.load_conto_deposito()  
        self.immobili_data = self.load_immobili_data()
    
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

    import dateparser  # Assicurati di avere questa importazione in alto

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
        self.root.title("Gestione Portafoglio Investimenti")
        self.root.geometry("1200x700")

        self.data_manager = DataManager()
        self.transaction_processor = TransactionProcessor(self.data_manager)
        self.portfolio = Portfolio(self.data_manager)

        self.balances = {}
        self.avg_prices = {}
        self.avg_prices_usd = {}  
        self.eur_balance = 0.0
        self.usdt_balance = 0.0
        self.total_invested = 0.0
        self.total_immobili_value = 0.0
        self.total_invested_excluding_eur = 0.0  
        self.total_current_value_eur = 0.0  

        self.style = ttk.Style()
        self.style.theme_use("clam")  
        self.style.configure("custom.Horizontal.TProgressbar", thickness=20)

        self.create_widgets()
        self.load_and_display_data()
    
    def pay_mortgage(self):
        selected_item = self.immobili_tree.selection()
        if not selected_item:
            messagebox.showerror("Errore", "Per favore, seleziona un immobile per effettuare il pagamento.")
            return

        immobile_id = self.immobili_tree.item(selected_item)["values"][0]

        # Trova l'immobile con l'ID selezionato
        immobile = next((imm for imm in self.data_manager.immobili_data["Immobili"] if imm["ID"] == immobile_id), None)
        if not immobile:
            messagebox.showerror("Errore", "Immobile non trovato.")
            return

        if not immobile["Mutuo"]:
            messagebox.showinfo("Info", "Questo immobile non ha un mutuo.")
            return

        if immobile["Pagamenti Effettuati"] >= immobile["Numero Rate"]:
            messagebox.showinfo("Info", "Tutte le rate sono state già pagate per questo immobile.")
            return

        importo_rata = immobile["Importo Rata"]

        # Verifica se il saldo EUR è sufficiente
        if self.eur_balance < importo_rata:
            messagebox.showerror("Errore", "Saldo EUR insufficiente per effettuare il pagamento.")
            return

        # Aggiorna il saldo EUR
        self.eur_balance -= importo_rata

        # Aggiungi una transazione FIAT di tipo "Withdraw FIAT" per l'importo della rata
        timestamp = datetime.now().strftime("%b %d, %Y %H:%M:%S")
        fiat_data = self.data_manager.load_fiat_transactions()
        fiat_data['Transactions'].append({
            "Timestamp": timestamp,
            "Type": "Withdraw FIAT",
            "Filled Amount": f"{importo_rata:.2f} EUR",
            "Info": "Pagamento rata mutuo"
        })
        self.data_manager.save_fiat_transactions(fiat_data)

        # Incrementa il contatore dei pagamenti effettuati
        immobile["Pagamenti Effettuati"] += 1

        # Salva i dati degli immobili
        self.data_manager.save_immobili_data()

        messagebox.showinfo("Successo", f"Pagamento di {importo_rata:.2f} EUR effettuato con successo.")
        self.load_and_display_data()

    def add_immobile(self):
        def save_immobile():
            tipo_immobile = tipo_dropdown.get()
            valore = valore_entry.get()
            mutuo = mutuo_var.get()
            anticipo_percentuale = anticipo_entry.get()

            if not tipo_immobile or not valore:
                messagebox.showerror("Errore", "Per favore, compila tutti i campi obbligatori.")
                return

            try:
                valore = float(valore.replace(",", "."))
                if valore <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Errore", "Inserisci un valore valido per il valore dell'immobile.")
                return

            if mutuo:
                if not anticipo_percentuale:
                    messagebox.showerror("Errore", "Inserisci la percentuale di anticipo.")
                    return
                try:
                    anticipo_percentuale = float(anticipo_percentuale.replace(",", "."))
                    if not 0 <= anticipo_percentuale <= 100:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Errore", "Inserisci una percentuale valida tra 0 e 100.")
                    return
            else:
                # Se non c'è mutuo, l'anticipo è il 100%
                anticipo_percentuale = 100.0

            anticipo_importo = (anticipo_percentuale / 100) * valore
            valore_mutuo = valore - anticipo_importo

            # Verifica se il saldo EUR è sufficiente
            if self.eur_balance < anticipo_importo:
                messagebox.showerror("Errore", "Saldo EUR insufficiente per coprire l'anticipo.")
                return

            # Aggiorna il saldo EUR sottraendo l'anticipo
            self.eur_balance -= anticipo_importo

            # Aggiungi una transazione FIAT di tipo "Withdraw FIAT" per l'importo dell'anticipo
            timestamp = datetime.now().strftime("%b %d, %Y %H:%M:%S")
            fiat_data = self.data_manager.load_fiat_transactions()
            fiat_data['Transactions'].append({
                "Timestamp": timestamp,
                "Type": "Withdraw FIAT",
                "Filled Amount": f"{anticipo_importo:.2f} EUR",
                "Info": "Pagamento immobile"
            })
            self.data_manager.save_fiat_transactions(fiat_data)

            if mutuo:
                numero_rate = numero_rate_entry.get()
                importo_rata = importo_rata_entry.get()

                if not numero_rate or not importo_rata:
                    messagebox.showerror("Errore", "Per favore, inserisci il numero di rate e l'importo della rata.")
                    return
                try:
                    numero_rate = int(numero_rate)
                    if numero_rate <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Errore", "Inserisci un numero valido di rate.")
                    return
                try:
                    importo_rata = float(importo_rata.replace(",", "."))
                    if importo_rata <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Errore", "Inserisci un importo valido per la rata.")
                    return
            else:
                numero_rate = None
                importo_rata = None

            # Genera un ID univoco per l'immobile
            immobile_id = f"IMM-{len(self.data_manager.immobili_data['Immobili']) + 1}"

            nuovo_immobile = {
                "ID": immobile_id,
                "Tipo": tipo_immobile,
                "Valore": valore,
                "Mutuo": mutuo,
                "Anticipo": anticipo_importo,
                "Valore Mutuo": valore_mutuo,
                "Numero Rate": numero_rate,
                "Importo Rata": importo_rata,
                "Pagamenti Effettuati": 0  # Contatore per i pagamenti effettuati
            }

            self.data_manager.immobili_data["Immobili"].append(nuovo_immobile)
            self.data_manager.save_immobili_data()

            messagebox.showinfo("Successo", "Immobile aggiunto con successo.")
            immobile_window.destroy()
            self.load_and_display_data()


        def toggle_anticipo():
            if mutuo_var.get():
                # Abilita l'input dell'anticipo
                anticipo_entry.config(state='normal')
                anticipo_entry.delete(0, tk.END)

                # Mostra i campi per il numero di rate e l'importo della rata
                numero_rate_label.pack(pady=5)
                numero_rate_entry.pack(pady=5)
                importo_rata_label.pack(pady=5)
                importo_rata_entry.pack(pady=5)
            else:
                # Disabilita l'input dell'anticipo e imposta al 100%
                anticipo_entry.delete(0, tk.END)
                anticipo_entry.insert(0, "100")
                anticipo_entry.config(state='disabled')

                # Nasconde i campi per il numero di rate e l'importo della rata
                numero_rate_label.pack_forget()
                numero_rate_entry.pack_forget()
                importo_rata_label.pack_forget()
                importo_rata_entry.pack_forget()


        immobile_window = tk.Toplevel(self.root)
        immobile_window.title("Aggiungi Immobile")
        immobile_window.geometry("400x400")

        ttk.Label(immobile_window, text="Tipo di Immobile:", font=("Arial", 10, "bold")).pack(pady=5)
        tipo_dropdown = ttk.Combobox(immobile_window, values=["Residenziale", "Commerciale"], state="readonly")
        tipo_dropdown.pack(pady=5)

        ttk.Label(immobile_window, text="Valore dell'Immobile (EUR):", font=("Arial", 10, "bold")).pack(pady=5)
        valore_entry = ttk.Entry(immobile_window)
        valore_entry.pack(pady=5)
        
        # Campi per il numero di rate e l'importo della rata
        numero_rate_label = ttk.Label(immobile_window, text="Numero Totale di Rate:", font=("Arial", 10, "bold"))
        numero_rate_entry = ttk.Entry(immobile_window)

        importo_rata_label = ttk.Label(immobile_window, text="Importo della Rata (EUR):", font=("Arial", 10, "bold"))
        importo_rata_entry = ttk.Entry(immobile_window)

        mutuo_var = tk.BooleanVar()
        mutuo_var.set(False)
        mutuo_check = ttk.Checkbutton(
            immobile_window,
            text="Acquistato con Mutuo",
            variable=mutuo_var,
            onvalue=True,
            offvalue=False,
            command=toggle_anticipo
        )
        mutuo_check.pack(pady=5)

        ttk.Label(immobile_window, text="Percentuale di Anticipo (%):", font=("Arial", 10, "bold")).pack(pady=5)
        anticipo_entry = ttk.Entry(immobile_window)
        anticipo_entry.pack(pady=5)
        anticipo_entry.insert(0, "100")
        anticipo_entry.config(state='disabled')  # Disabilitato di default perché mutuo_var è False

        save_button = ttk.Button(immobile_window, text="Aggiungi Immobile", command=save_immobile)
        save_button.pack(pady=20)

    def check_deposit_expirations(self):
        expired_deposits = []
        today = datetime.now()
        deposits_to_remove = []

        for deposito in self.data_manager.conto_deposito["Conto deposito"]:
            scadenza = deposito["Scadenza"]
            if today >= scadenza:
                expired_deposits.append(deposito)
                deposits_to_remove.append(deposito)

        for deposito in deposits_to_remove:
            self.data_manager.conto_deposito["Conto deposito"].remove(deposito)

        with open(self.data_manager.conto_deposito_path, 'w') as f:
            json.dump(self.data_manager.conto_deposito, f, indent=4, default=datetime_to_string)

        for deposito in expired_deposits:
            self.handle_expired_deposit(deposito)


    def handle_expired_deposit(self, deposito):
        def save_interest():
            interest_amount = interest_entry.get()
            if not interest_amount:
                messagebox.showerror("Errore", "Per favore, inserisci l'importo degli interessi guadagnati.")
                return

            try:
                interest_amount = float(interest_amount.replace(",", "."))
            except ValueError:
                messagebox.showerror("Errore", "Per favore, inserisci un importo valido.")
                return

            timestamp = datetime.now().strftime("%b %d, %Y %H:%M:%S")
            fiat_data = self.data_manager.load_fiat_transactions()
            fiat_data['Transactions'].append({
                "Timestamp": timestamp,
                "Type": "Top Up FIAT",
                "Filled Amount": f"{interest_amount} EUR",
                "Info": "Interessi conto deposito"
            })
            self.data_manager.save_fiat_transactions(fiat_data)

            self.load_and_display_data()
            messagebox.showinfo("Successo", "Gli interessi sono stati aggiunti al saldo disponibile.")
            interest_window.destroy()

        interest_window = tk.Toplevel(self.root)
        interest_window.title("Interessi Guadagnati")
        interest_window.geometry("400x200")

        ttk.Label(interest_window, text=f"Il conto deposito di {deposito['Filled Amount']} è scaduto.", font=("Arial", 10, "bold")).pack(pady=10)
        ttk.Label(interest_window, text="Inserisci l'importo degli interessi guadagnati (EUR):", font=("Arial", 10)).pack(pady=5)
        interest_entry = ttk.Entry(interest_window)
        interest_entry.pack(pady=5)
        save_button = ttk.Button(interest_window, text="Conferma", command=save_interest)
        save_button.pack(pady=10)

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.transactions_tab = ttk.Frame(self.notebook)
        self.balances_tab = ttk.Frame(self.notebook)
        self.summary_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.transactions_tab, text='Transazioni')
        self.notebook.add(self.balances_tab, text='Bilanci')
        self.notebook.add(self.summary_tab, text='Sommario Portafoglio')

        self.create_transactions_tab()
        self.create_balances_tab()
        self.create_summary_tab()

    def create_transactions_tab(self):
        self.transactions_button_frame = ttk.Frame(self.transactions_tab)
        self.transactions_button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.create_buttons(self.transactions_button_frame)

        self.paned_transactions = ttk.Panedwindow(self.transactions_tab, orient=tk.HORIZONTAL)
        self.paned_transactions.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.fiat_frame = ttk.Labelframe(self.paned_transactions, text="Transazioni FIAT", padding=(10, 10))
        self.paned_transactions.add(self.fiat_frame, weight=1)

        self.crypto_frame = ttk.Labelframe(self.paned_transactions, text="Transazioni Crypto", padding=(10, 10))
        self.paned_transactions.add(self.crypto_frame, weight=1)

        fiat_columns = ("Timestamp", "Type", "Filled Amount", "Info")
        self.fiat_list = ttk.Treeview(self.fiat_frame, columns=fiat_columns, show="headings", height=15)
        for col in fiat_columns:
            self.fiat_list.heading(col, text=col)
            self.fiat_list.column(col, minwidth=0, width=150)
        fiat_vscrollbar = ttk.Scrollbar(self.fiat_frame, orient="vertical", command=self.fiat_list.yview)
        self.fiat_list.configure(yscroll=fiat_vscrollbar.set)
        fiat_vscrollbar.pack(side="right", fill="y")
        self.fiat_list.pack(fill=tk.BOTH, expand=True)

        crypto_columns = ("Timestamp", "Pair", "Side", "Price", "Order Amount", "Filled Amount", "Executed Amount", "Info")
        self.crypto_list = ttk.Treeview(self.crypto_frame, columns=crypto_columns, show="headings", height=15)
        for col in crypto_columns:
            self.crypto_list.heading(col, text=col)
            self.crypto_list.column(col, minwidth=0, width=150)
        crypto_vscrollbar = ttk.Scrollbar(self.crypto_frame, orient="vertical", command=self.crypto_list.yview)
        self.crypto_list.configure(yscroll=crypto_vscrollbar.set)
        crypto_vscrollbar.pack(side="right", fill="y")
        self.crypto_list.pack(fill=tk.BOTH, expand=True)

    def create_balances_tab(self):
        self.paned_balances = ttk.Panedwindow(self.balances_tab, orient=tk.VERTICAL)
        self.paned_balances.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.balances_frame = ttk.Labelframe(self.paned_balances, text="Bilanci", padding=(10, 10))
        self.paned_balances.add(self.balances_frame, weight=2)

        self.balances_notebook = ttk.Notebook(self.balances_frame)
        self.balances_notebook.pack(fill=tk.BOTH, expand=True)

        self.deposito_tab = ttk.Frame(self.balances_notebook)
        self.crypto_tab = ttk.Frame(self.balances_notebook)
        self.etf_tab = ttk.Frame(self.balances_notebook)
        self.immobili_tab = ttk.Frame(self.balances_notebook)

        self.balances_notebook.add(self.deposito_tab, text='Conti Deposito')
        self.balances_notebook.add(self.crypto_tab, text='Criptovalute')
        self.balances_notebook.add(self.etf_tab, text='ETF')
        self.balances_notebook.add(self.immobili_tab, text='Immobili')

        deposito_columns = ("Timestamp", "Tipo", "Importo", "Scadenza")
        self.deposito_tree = ttk.Treeview(self.deposito_tab, columns=deposito_columns, show="headings")
        for col in deposito_columns:
            self.deposito_tree.heading(col, text=col)
            self.deposito_tree.column(col, minwidth=0, width=150)
        self.deposito_tree.pack(fill=tk.BOTH, expand=True)

        buttons_frame_depositi = ttk.Frame(self.deposito_tab)
        buttons_frame_depositi.pack(fill=tk.X, pady=5)

        add_conto_deposito_button = ttk.Button(buttons_frame_depositi, text="Aggiungi Conto Deposito", command=self.add_conto_deposito)
        add_conto_deposito_button.pack(side=tk.LEFT, padx=10, pady=5)

        crypto_columns = ("Valuta", "Unità", "Prezzo Medio USD", "Prezzo Medio EUR", "Prezzo Attuale USD", "Prezzo Attuale EUR", "Valore Totale EUR", "Guadagno/Perdita %")
        self.crypto_tree = ttk.Treeview(self.crypto_tab, columns=crypto_columns, show="headings")
        for col in crypto_columns:
            self.crypto_tree.heading(col, text=col)
            self.crypto_tree.column(col, minwidth=0, width=120)
        self.crypto_tree.pack(fill=tk.BOTH, expand=True)

        etf_columns = ("ETF", "Unità", "Prezzo Medio EUR", "Prezzo Attuale EUR", "Valore Totale EUR", "Guadagno/Perdita %")
        self.etf_tree = ttk.Treeview(self.etf_tab, columns=etf_columns, show="headings")
        for col in etf_columns:
            self.etf_tree.heading(col, text=col)
            self.etf_tree.column(col, minwidth=0, width=120)
        self.etf_tree.pack(fill=tk.BOTH, expand=True)

        buttons_frame_etf = ttk.Frame(self.etf_tab)
        buttons_frame_etf.pack(fill=tk.X, pady=5)

        modify_etf_button = ttk.Button(buttons_frame_etf, text="Modifica Prezzo ETF", command=self.update_etf_price)
        modify_etf_button.pack(side=tk.LEFT, padx=10, pady=5)

        immobili_columns = ("ID", "Tipo", "Valore", "Mutuo", "Anticipo", "Valore Mutuo", "Numero Rate", "Importo Rata", "Rate Pagate", "Investimento Totale")
        self.immobili_tree = ttk.Treeview(self.immobili_tab, columns=immobili_columns, show="headings")
        for col in immobili_columns:
            self.immobili_tree.heading(col, text=col)
            self.immobili_tree.column(col, minwidth=0, width=120)
        self.immobili_tree.pack(fill=tk.BOTH, expand=True)

        # Frame per i pulsanti
        buttons_frame_immobili = ttk.Frame(self.immobili_tab)
        buttons_frame_immobili.pack(fill=tk.X, pady=5)

        add_immobile_button = ttk.Button(buttons_frame_immobili, text="Aggiungi Immobile", command=self.add_immobile)
        add_immobile_button.pack(side=tk.LEFT, padx=10, pady=5)

        self.pay_mortgage_button = ttk.Button(buttons_frame_immobili, text="Effettua Pagamento Rata", command=self.pay_mortgage)
        self.pay_mortgage_button.pack(side=tk.LEFT, padx=10, pady=5)

        
    def create_summary_tab(self):
        self.summary_frame = ttk.Frame(self.summary_tab, padding=(10, 10))
        self.summary_frame.pack(fill=tk.BOTH, expand=True)

        self.recap_frame = ttk.Labelframe(self.summary_frame, text="Riepilogo Portafoglio", padding=(10, 10))
        self.recap_frame.pack(fill=tk.X, padx=10, pady=10)

        self.percentuali_frame = ttk.Labelframe(self.summary_frame, text="Percentuali Portafoglio", padding=(10, 10))
        self.percentuali_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.recap_labels = {}
        recap_items = [
            ("Totale nei conti deposito:", "totale_depositi"),
            ("Saldo EUR:", "saldo_finale"), 
            ("Saldo investito:", "saldo_investito"),
            ("Valore attuale investimento:", "valore_attuale")
        ]

        for idx, (text, key) in enumerate(recap_items):
            label_text = ttk.Label(self.recap_frame, text=text, font=("Arial", 10, "bold"))
            label_value = ttk.Label(self.recap_frame, text="", font=("Arial", 10))
            label_text.grid(row=idx, column=0, sticky=tk.W, padx=5, pady=2)
            label_value.grid(row=idx, column=1, sticky=tk.W, padx=5, pady=2)
            self.recap_labels[key] = label_value

        self.percentuali_canvas = tk.Canvas(self.percentuali_frame)
        self.percentuali_scrollbar = ttk.Scrollbar(self.percentuali_frame, orient="vertical", command=self.percentuali_canvas.yview)
        self.percentuali_content = ttk.Frame(self.percentuali_canvas)

        self.percentuali_content.bind(
            "<Configure>",
            lambda e: self.percentuali_canvas.configure(
                scrollregion=self.percentuali_canvas.bbox("all")
            )
        )

        self.percentuali_canvas.create_window((0, 0), window=self.percentuali_content, anchor="nw")
        self.percentuali_canvas.configure(yscrollcommand=self.percentuali_scrollbar.set)

        self.percentuali_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.percentuali_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_buttons(self, frame):
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))

        add_fiat_button = ttk.Button(frame, text="Aggiungi FIAT", command=self.add_fiat_transaction, style="Accent.TButton")
        add_fiat_button.pack(side=tk.LEFT, padx=5, pady=5)

        add_crypto_button = ttk.Button(frame, text="Aggiungi Crypto", command=self.add_crypto_transaction, style="Accent.TButton")
        add_crypto_button.pack(side=tk.LEFT, padx=5, pady=5)

        delete_transaction_button = ttk.Button(frame, text="Elimina Transazione", command=self.delete_transaction, style="Accent.TButton")
        delete_transaction_button.pack(side=tk.LEFT, padx=5, pady=5)

    # ======================= Data Loading and Display =======================

    def load_and_display_data(self):
        crypto_transactions = self.data_manager.load_crypto_transactions()
        crypto_transactions.sort(key=lambda tx: dateparser.parse(tx["Timestamp"], languages=['it', 'en']))
        self.eur_balance, self.total_invested, fiat_transactions = self.transaction_processor.load_fiat_balance()
        fiat_transactions.sort(key=lambda tx: dateparser.parse(tx["Timestamp"], languages=['it', 'en']))
        
        deposito_totale = sum([float(deposito["Filled Amount"].replace(" EUR", "")) for deposito in self.data_manager.conto_deposito["Conto deposito"]])
        self.eur_balance -= deposito_totale  

        self.display_crypto_transactions(crypto_transactions)
        self.display_fiat_transactions(fiat_transactions)

        self.balances, self.avg_prices, self.avg_prices_usd, self.eur_balance, self.usdt_balance = self.transaction_processor.process_crypto_transactions(crypto_transactions, self.eur_balance)
        self.check_deposit_expirations()
        self.display_balances()
        self.display_summary()  

    def display_crypto_transactions(self, transactions):
        self.crypto_list.delete(*self.crypto_list.get_children())
        for tx in transactions:
            self.crypto_list.insert("", "end", values=(tx["Timestamp"], tx["Pair"], tx["Side"], tx["Price"], tx["Order Amount"], tx["Filled Amount"], tx["Executed Amount"], tx.get("Info", "Transazione")))

    def display_fiat_transactions(self, transactions):
        self.fiat_list.delete(*self.fiat_list.get_children())
        for tx in transactions:
            self.fiat_list.insert("", "end", values=(tx["Timestamp"], tx["Type"], tx["Filled Amount"], tx.get("Info", "N/D")))

    # ======================= Transaction Management =======================

    def add_fiat_transaction(self):
        def save_fiat_transaction():
            timestamp = datetime.now().strftime("%b %d, %Y %H:%M:%S")
            tx_type = type_dropdown.get()
            filled_amount = filled_amount_entry.get()
            info = info_dropdown.get()  # Raccoglie l'informazione dall'input dell'utente

            if not filled_amount:
                messagebox.showerror("Errore", "Inserisci un importo valido.")
                return

            fiat_data = self.data_manager.load_fiat_transactions()
            fiat_data['Transactions'].append({
                "Timestamp": timestamp,
                "Type": tx_type,
                "Filled Amount": f"{filled_amount} EUR",
                "Info": info 
            })
            self.data_manager.save_fiat_transactions(fiat_data)

            fiat_window.destroy()
            self.load_and_display_data()
            messagebox.showinfo("Successo", "Transazione FIAT aggiunta con successo.")

        fiat_window = tk.Toplevel(self.root)
        fiat_window.title("Aggiungi Transazione FIAT")
        fiat_window.geometry("400x300")
        
        ttk.Label(fiat_window, text="Tipo di Transazione:", font=("Arial", 10, "bold")).pack(pady=5)
        type_dropdown = ttk.Combobox(fiat_window, values=["Top Up FIAT", "Withdraw FIAT"], state="readonly")
        type_dropdown.pack(pady=5)

        ttk.Label(fiat_window, text="Importo (EUR):", font=("Arial", 10, "bold")).pack(pady=5)
        filled_amount_entry = ttk.Entry(fiat_window)
        filled_amount_entry.pack(pady=5)

        ttk.Label(fiat_window, text="Informazioni aggiuntive:", font=("Arial", 10, "bold")).pack(pady=5)
        info_dropdown = ttk.Combobox(fiat_window, values=["Normale", "Correzione"], state="readonly")
        info_dropdown.pack(pady=5)

        save_button = ttk.Button(fiat_window, text="Aggiungi Transazione", command=save_fiat_transaction)
        save_button.pack(pady=10)

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

            required_fields = [pair, side, price, order_amount, filled_amount, executed_amount, trade_fee]
            if not all(required_fields):
                messagebox.showerror("Errore", "Per favore, compila tutti i campi richiesti.")
                return

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
            messagebox.showinfo("Successo", "Transazione Crypto/ETF aggiunta con successo.")

        crypto_window = tk.Toplevel(self.root)
        crypto_window.title("Aggiungi Transazione Crypto/ETF")
        crypto_window.geometry("500x600")

        fields = [
            ("Coppia (es. BTC/USDT o VFEA/EUR):", ttk.Entry),
            ("Tipo di Transazione:", ttk.Combobox, {"values": ["Buy", "Sell"], "state": "readonly"}),
            ("Prezzo (EUR o USDT):", ttk.Entry),
            ("Quantità Ordinata:", ttk.Entry),
            ("Quantità Eseguita:", ttk.Entry),
            ("Importo Eseguito (EUR o USDT):", ttk.Entry),
            ("Commissione di Scambio:", ttk.Entry),
            ("Tipo di Transazione (Info):", ttk.Combobox, {"values": ["Crypto", "Earn", "Etf"], "state": "readonly"}),
        ]

        entries = []

        for idx, (label_text, widget_class, *widget_args) in enumerate(fields):
            ttk.Label(crypto_window, text=label_text, font=("Arial", 10, "bold")).pack(pady=5)
            widget = widget_class(crypto_window, **(widget_args[0] if widget_args else {}))
            widget.pack(pady=5)
            entries.append(widget)

        pair_entry, side_dropdown, price_entry, order_amount_entry, filled_amount_entry, executed_amount_entry, trade_fee_entry, info_dropdown = entries

        save_button = ttk.Button(crypto_window, text="Aggiungi Transazione", command=save_crypto_transaction)
        save_button.pack(pady=20)

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
                messagebox.showinfo("Successo", "Transazione FIAT eliminata con successo.")

        elif selected_crypto:
            selected_item = self.crypto_list.item(selected_crypto)
            timestamp = selected_item['values'][0]

            transactions = self.data_manager.load_crypto_transactions()
            index_to_delete = next((i for i, tx in enumerate(transactions) if tx['Timestamp'] == timestamp), None)
                
            if index_to_delete is not None:
                del transactions[index_to_delete]
                self.data_manager.save_crypto_transactions(transactions)
                messagebox.showinfo("Successo", "Transazione Crypto/ETF eliminata con successo.")

        else:
            messagebox.showwarning("Errore", "Seleziona una transazione da eliminare.")

        self.load_and_display_data()

    def add_conto_deposito(self):
        deposito_window = tk.Toplevel(self.root)
        deposito_window.title("Aggiungi Conto Deposito")
        deposito_window.geometry("400x250")

        ttk.Label(deposito_window, text="Tipo di Conto:", font=("Arial", 10, "bold")).pack(pady=5)
        type_dropdown = ttk.Combobox(deposito_window, values=["Vincolato", "Non vincolato"], state="readonly")
        type_dropdown.pack(pady=5)

        ttk.Label(deposito_window, text="Importo (EUR):", font=("Arial", 10, "bold")).pack(pady=5)
        filled_amount_entry = ttk.Entry(deposito_window)
        filled_amount_entry.pack(pady=5)

        ttk.Label(deposito_window, text="Scadenza (es. Nov 19, 2028 13:49:03):", font=("Arial", 10, "bold")).pack(pady=5)
        scadenza_entry = ttk.Entry(deposito_window)
        scadenza_entry.pack(pady=5)

        save_button = ttk.Button(deposito_window, text="Aggiungi Conto Deposito", command=lambda: self.save_conto_deposito(type_dropdown.get(), filled_amount_entry.get(), scadenza_entry.get()))
        save_button.pack(pady=10)

    def save_conto_deposito(self, deposito_type, filled_amount, scadenza):
        timestamp = datetime.now().strftime("%b %d, %Y %H:%M:%S")
        
        try:
            filled_amount_value = float(filled_amount.replace(",", "."))
            if filled_amount_value <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Errore", "Per favore, inserisci un importo valido e positivo.")
            return
        
        scadenza_parsed = dateparser.parse(scadenza, languages=['it', 'en'])
        if scadenza_parsed is None:
            messagebox.showerror("Errore", "Formato data di scadenza non valido. Per favore, inserisci una data valida.")
            return
        if scadenza_parsed <= datetime.now():
            messagebox.showerror("Errore", "La data di scadenza deve essere futura.")
            return

        new_deposito = {
            "Timestamp": timestamp,
            "Type": deposito_type,
            "Filled Amount": f"{filled_amount} EUR",
            "Scadenza": scadenza_parsed
        }

        self.data_manager.conto_deposito["Conto deposito"].append(new_deposito)

        with open(self.data_manager.conto_deposito_path, 'w') as f:
            json.dump(self.data_manager.conto_deposito, f, indent=4, default=datetime_to_string)

        self.load_and_display_data()
        messagebox.showinfo("Successo", "Conto Deposito aggiunto con successo.")

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
                messagebox.showinfo("Successo", f"Prezzo ETF '{etf_name}' aggiornato a {current_price:.2f} EUR")
            else:
                messagebox.showerror("Errore", f"L'ETF '{etf_name}' non è stato trovato.")
                return

        etf_window = tk.Toplevel(self.root)
        etf_window.title("Modifica Prezzo ETF")
        etf_window.geometry("400x200")

        ttk.Label(etf_window, text="Nome ETF:", font=("Arial", 10, "bold")).pack(pady=5)
        etf_name_entry = ttk.Entry(etf_window)
        etf_name_entry.pack(pady=5)

        ttk.Label(etf_window, text="Valore Attuale (EUR):", font=("Arial", 10, "bold")).pack(pady=5)
        current_price_entry = ttk.Entry(etf_window)
        current_price_entry.pack(pady=5)

        save_button = ttk.Button(etf_window, text="Salva", command=save_etf_price)
        save_button.pack(pady=10)

    # ======================= Display Balances and Summary =======================

    def display_balances(self):
        self.total_invested_excluding_eur = 0.0
        self.total_current_value_eur = 0.0
        self.total_immobili_value = 0.0

        for tree in [self.deposito_tree, self.crypto_tree, self.etf_tree, self.immobili_tree]:
            tree.delete(*tree.get_children())

        current_crypto_prices = self.data_manager.get_current_crypto_prices()

        deposito_totale = 0
        for deposito in self.data_manager.conto_deposito["Conto deposito"]:
            timestamp = deposito["Timestamp"]
            deposito_type = deposito["Type"]
            amount_str = deposito["Filled Amount"].replace(" EUR", "")
            amount = float(amount_str)
            scadenza = deposito["Scadenza"]
            deposito_totale += amount

            self.deposito_tree.insert("", "end", values=(timestamp, deposito_type, f"{amount:.2f} EUR", scadenza))

        for currency, balance in self.balances.items():
            avg_price_eur = self.avg_prices.get(currency, 'N/A')
            avg_price_usd = self.avg_prices_usd.get(currency, 'N/A')

            if currency != 'USDT' and not currency.startswith('ETF_'):
                coin_id = self.data_manager.crypto_mapping.get(f"{currency}/USDT", None)
                current_price_usd = current_crypto_prices.get(coin_id, {}).get('usd', 'N/A')
                current_price_eur = current_crypto_prices.get(coin_id, {}).get('eur', 'N/A')

                # Convert current_price_eur to float if it's a valid number
                current_price_eur = float(current_price_eur) if isinstance(current_price_eur, (int, float, str)) and current_price_eur != 'N/A' else 'N/A'

                if current_price_eur != 'N/A':
                    total_value_eur = balance * current_price_eur
                    self.total_current_value_eur += total_value_eur
                else:
                    total_value_eur = 'N/A'

                if avg_price_eur != 'N/A':
                    invested_eur = balance * avg_price_eur
                    self.total_invested_excluding_eur += invested_eur
                else:
                    invested_eur = 'N/A'

                percentage_gain = self.portfolio.calculate_percentage_gain(current_price_usd, avg_price_usd)
                gain_loss_text = (
                    f"▲ {percentage_gain:.2f}%" if isinstance(percentage_gain, (int, float)) and percentage_gain >= 0
                    else f"▼ {abs(percentage_gain):.2f}%" if isinstance(percentage_gain, (int, float)) and percentage_gain < 0
                    else 'N/A'
                )

                self.crypto_tree.insert("", "end", values=(
                    currency,
                    f"{balance:.6f}",
                    f"{avg_price_usd:.4f}" if avg_price_usd != 'N/A' else 'N/A',
                    f"{avg_price_eur:.4f}" if avg_price_eur != 'N/A' else 'N/A',
                    f"{current_price_usd:.4f}" if current_price_usd != 'N/A' else 'N/A',
                    f"{current_price_eur:.4f}" if current_price_eur != 'N/A' else 'N/A',
                    f"{total_value_eur:.2f}" if total_value_eur != 'N/A' else 'N/A',
                    gain_loss_text
                ))

            elif currency == 'USDT':
                avg_price_usd = 1.0  
                avg_price_eur = self.avg_prices.get('USDT', 'N/A')
                current_price_usd = 1.0  
                current_price_eur = current_crypto_prices.get('tether', {}).get('eur', 'N/A')

                # Convert to float if current_price_eur is a valid number
                current_price_eur = float(current_price_eur) if isinstance(current_price_eur, (int, float, str)) and current_price_eur != 'N/A' else 'N/A'
                self.usdt_balance = float(self.usdt_balance) if isinstance(self.usdt_balance, str) else self.usdt_balance

                if current_price_eur != 'N/A':
                    total_value_eur = self.usdt_balance * current_price_eur
                else:
                    total_value_eur = 'N/A'

                usdt_gain_percent = self.portfolio.calculate_percentage_gain(current_price_eur, avg_price_eur)
                gain_loss_text = (
                    f"▲ {usdt_gain_percent:.2f}%" if isinstance(usdt_gain_percent, (int, float)) and usdt_gain_percent >= 0
                    else f"▼ {abs(usdt_gain_percent):.2f}%" if isinstance(usdt_gain_percent, (int, float)) and usdt_gain_percent < 0
                    else 'N/A'
                )

                self.crypto_tree.insert("", "end", values=(
                    "USDT",
                    f"{self.usdt_balance:.6f}",
                    f"{avg_price_usd:.2f}",
                    f"{avg_price_eur:.4f}" if avg_price_eur != 'N/A' else 'N/A',
                    f"{current_price_usd:.2f}",
                    f"{current_price_eur:.4f}" if current_price_eur != 'N/A' else 'N/A',
                    f"{total_value_eur:.2f}" if current_price_eur != 'N/A' else 'N/A',
                    gain_loss_text
                ))

            elif currency == 'USDT':
                avg_price_usd = 1.0  
                avg_price_eur = self.avg_prices.get('USDT', 'N/A')
                current_price_usd = 1.0  
                current_price_eur = current_crypto_prices.get('tether', {}).get('eur', 'N/A')
                total_value_eur = self.usdt_balance * current_price_eur

                usdt_gain_percent = self.portfolio.calculate_percentage_gain(current_price_eur, avg_price_eur)

                if isinstance(usdt_gain_percent, (int, float)):
                    if usdt_gain_percent >= 0:
                        gain_loss_text = f"▲ {usdt_gain_percent:.2f}%"
                    else:
                        gain_loss_text = f"▼ {abs(usdt_gain_percent):.2f}%"
                else:
                    gain_loss_text = 'N/A'

                self.crypto_tree.insert("", "end", values=(
                    "USDT",
                    f"{self.usdt_balance:.6f}",
                    f"{avg_price_usd:.2f}",
                    f"{avg_price_eur:.4f}" if avg_price_eur != 'N/A' else 'N/A',
                    f"{current_price_usd:.2f}",
                    f"{current_price_eur:.4f}" if current_price_eur != 'N/A' else 'N/A',
                    f"{total_value_eur:.2f}" if current_price_eur != 'N/A' else 'N/A',
                    gain_loss_text
                ))

        for immobile in self.data_manager.immobili_data["Immobili"]:
            immobile_id = immobile["ID"]
            tipo = immobile["Tipo"]
            valore = immobile["Valore"]
            mutuo = "Sì" if immobile["Mutuo"] else "No"
            anticipo = immobile["Anticipo"]
            valore_mutuo = immobile["Valore Mutuo"]

            if immobile["Mutuo"]:
                numero_rate = immobile["Numero Rate"]
                importo_rata = immobile["Importo Rata"]
                rate_pagate = immobile["Pagamenti Effettuati"]
                investimento_totale = anticipo + (importo_rata * rate_pagate)
            else:
                numero_rate = "-"
                importo_rata = "-"
                rate_pagate = "-"
                investimento_totale = anticipo

            self.total_immobili_value += investimento_totale

            self.immobili_tree.insert("", "end", values=(
                immobile_id,
                tipo,
                f"{valore:,.2f} EUR",
                mutuo,
                f"{anticipo:,.2f} EUR",
                f"{valore_mutuo:,.2f} EUR",
                numero_rate,
                f"{importo_rata:,.2f} EUR" if importo_rata != "-" else "-",
                rate_pagate,
                f"{investimento_totale:,.2f} EUR"
            ))
            
        for currency, balance in self.balances.items():
            if currency.startswith('ETF_'):
                avg_price = self.avg_prices.get(currency, 'N/A')
                etf_name = currency[4:]
                etf_current_value = self.data_manager.manual_etf_prices.get(etf_name, self.data_manager.etf_mapping.get(etf_name, 'N/A'))

                if isinstance(etf_current_value, (int, float)):
                    total_value_eur = balance * etf_current_value
                    self.total_current_value_eur += total_value_eur

                    if avg_price != 'N/A':
                        invested_eur = balance * avg_price
                        self.total_invested_excluding_eur += invested_eur
                    else:
                        invested_eur = 'N/A'

                    gain_loss = self.portfolio.calculate_percentage_gain(etf_current_value, avg_price)
                    if isinstance(gain_loss, (int, float)):
                        if gain_loss >= 0:
                            gain_loss_text = f"▲ {gain_loss:.2f}%"
                        else:
                            gain_loss_text = f"▼ {abs(gain_loss):.2f}%"
                    else:
                        gain_loss_text = 'N/A'
                else:
                    total_value_eur = 'N/A'
                    invested_eur = 'N/A'
                    gain_loss_text = 'N/A'

                self.etf_tree.insert("", "end", values=(
                    etf_name,
                    f"{balance:.6f}",
                    f"{avg_price:.2f}" if avg_price != 'N/A' else 'N/A',
                    f"{etf_current_value:.2f}" if isinstance(etf_current_value, (int, float)) else 'N/A',
                    f"{total_value_eur:.2f}" if isinstance(total_value_eur, (int, float)) else 'N/A',
                    gain_loss_text
                ))

    def display_summary(self):
        for widget in self.percentuali_content.winfo_children():
            widget.destroy()

        current_crypto_prices = self.data_manager.get_current_crypto_prices()
        percentuali_target = self.data_manager.percentuali_target

        total_deposito_value = sum([float(deposito["Filled Amount"].replace(" EUR", "")) for deposito in self.data_manager.conto_deposito["Conto deposito"]])
        total_liquidity = self.eur_balance + self.usdt_balance * current_crypto_prices.get('tether', {}).get('eur', 0)
        total_portfolio_value = self.total_current_value_eur + total_liquidity + total_deposito_value + self.total_immobili_value

        self.recap_labels["saldo_finale"].config(text=f"{self.eur_balance:,.2f} EUR")
        self.recap_labels["totale_depositi"].config(text=f"{total_deposito_value:,.2f} EUR")
        self.recap_labels["saldo_investito"].config(text=f"{self.total_invested_excluding_eur:,.2f} EUR")
        self.recap_labels["valore_attuale"].config(text=f"{self.total_current_value_eur:,.2f} EUR")

        def create_progressbar(label_text, value, target_value):
            frame = ttk.Frame(self.percentuali_content)
            frame.pack(fill=tk.X, pady=5)

            label = ttk.Label(frame, text=label_text, font=("Arial", 10, "bold"))
            label.pack(side=tk.LEFT, padx=5)

            progress_style = "custom.Horizontal.TProgressbar"

            progress = ttk.Progressbar(frame, style=progress_style, orient='horizontal', length=300, mode='determinate')
            progress['value'] = value
            progress['maximum'] = 100
            progress.pack(side=tk.LEFT, padx=5)

            percent_label = ttk.Label(frame, text=f"{value:.2f}% / {target_value:.2f}%", font=("Arial", 10))
            percent_label.pack(side=tk.LEFT, padx=5)

        if total_portfolio_value > 0:
            # Calcola le percentuali per le varie categorie
            liquidity_percent = (total_liquidity / total_portfolio_value) * 100
            deposito_percent = (total_deposito_value / total_portfolio_value) * 100
            immobili_percent = (self.total_immobili_value / total_portfolio_value) * 100

            # Crea le barre di progresso per Liquidity, Conto Deposito e Immobili
            create_progressbar(f"Liquidità: {total_liquidity:,.2f} EUR", liquidity_percent, percentuali_target.get("liquidita", 0))
            create_progressbar(f"Conto Deposito: {total_deposito_value:,.2f} EUR", deposito_percent, percentuali_target.get("Conto deposito", 0))
            create_progressbar(f"Immobili: {self.total_immobili_value:,.2f} EUR", immobili_percent, percentuali_target.get("Immobili", 0))

            # Calcolo dei valori degli ETF
            etf_values = {}
            for currency, balance in self.balances.items():
                if currency.startswith('ETF_'):
                    etf_name = currency[4:]
                    etf_current_value = self.data_manager.manual_etf_prices.get(etf_name, 0)
                    etf_value = balance * etf_current_value
                    etf_values[etf_name] = etf_value

            # Calcolo dei valori delle criptovalute
            total_btc_value = 0
            total_eth_value = 0
            total_solana_value = 0
            total_altcoins_value = 0

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

            # Crea le barre di progresso per gli ETF
            for etf_name, etf_value in etf_values.items():
                etf_single_percent = (etf_value / total_portfolio_value) * 100
                etf_target = percentuali_target["etf"].get(etf_name, 0)
                create_progressbar(f"{etf_name}: {etf_value:,.2f} EUR", etf_single_percent, etf_target)

            # Calcola le percentuali per le criptovalute
            btc_percent = (total_btc_value / total_portfolio_value) * 100
            eth_percent = (total_eth_value / total_portfolio_value) * 100
            solana_percent = (total_solana_value / total_portfolio_value) * 100
            altcoins_percent = (total_altcoins_value / total_portfolio_value) * 100

            # Crea le barre di progresso per le criptovalute
            create_progressbar(f"Bitcoin (BTC): {total_btc_value:,.2f} EUR", btc_percent, percentuali_target.get("BTC", 0))
            create_progressbar(f"Ethereum (ETH): {total_eth_value:,.2f} EUR", eth_percent, percentuali_target.get("ETH", 0))
            create_progressbar(f"Solana (SOL): {total_solana_value:,.2f} EUR", solana_percent, percentuali_target.get("SOL", 0))
            create_progressbar(f"Altcoin (resto): {total_altcoins_value:,.2f} EUR", altcoins_percent, percentuali_target.get("altcoin", 0))
        else:
            ttk.Label(self.percentuali_content, text="Nessun dato disponibile per creare le barre di progresso.", font=("Arial", 10, "bold")).pack(pady=5)

# ======================= Main Application =======================

if __name__ == "__main__":
    root = tk.Tk()
    app = ApplicationGUI(root)
    root.mainloop()
