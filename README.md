# Gestione Portafoglio Crypto e ETF

Questo progetto è un'applicazione GUI in Python che consente di gestire transazioni e saldi per criptovalute, ETF e valuta FIAT (EUR). L'applicazione permette di:

- Aggiungere, visualizzare ed eliminare transazioni per FIAT, Crypto ed ETF.
- Aggiornare manualmente i prezzi degli ETF.
- Calcolare e visualizzare i saldi attuali, i guadagni o le perdite percentuali.
- Visualizzare la composizione del portafoglio rispetto alle percentuali target predefinite.

## Requisiti

### Python 3.x

### Moduli Python:

- `tkinter` (incluso di default con Python)
- `requests`

## Installazione

1. **Clona il repository o scarica i file**

```bash
git clone https://github.com/tuo-username/tuo-repository.git
```

2. **Installa le dipendenze**

   Assicurati di avere installato il modulo `requests`:

```
pip install requests
```

3. **Configura i dati**

   Crea una cartella `data` nella directory del progetto e assicurati che contenga i seguenti file JSON:

   - `crypto_transactions.json`
   - `fiat_transactions.json`
   - `crypto_valute.json`
   - `etf_valute.json`
   - `percentuali_target.json`

   Se questi file non esistono, creali con il contenuto appropriato (vedi sezione Configurazione dei Dati).

## Configurazione dei Dati

### `crypto_transactions.json`

Contiene un elenco di transazioni di criptovalute. Se stai iniziando da zero, puoi inizializzarlo come segue:

```css
[]
```

### `fiat_transactions.json`

Contiene il saldo FIAT iniziale e le transazioni FIAT:

```json
{
  "EUR_Balance": 0,
  "Transactions": []
}
```

### `crypto_valute.json`

Mappa le coppie di criptovalute ai loro identificatori su CoinGecko:

```json
{
  "BTC/USDT": "bitcoin",
  "ETH/USDT": "ethereum",
  "SOL/USDT": "solana",
  "USDT/EUR": "tether"
}
```

Aggiungi o modifica le mappature in base alle criptovalute che intendi gestire.

### `etf_valute.json`

Contiene i prezzi manuali degli ETF:

```json
{
  "VFEA": 60.00,
  "IS3N": 7.00
}
```

Puoi aggiornare i prezzi degli ETF direttamente dall'applicazione.

### `percentuali_target.json`

Definisce le percentuali target per la composizione del portafoglio:

```json
{
  "liquidita": 20,
  "BTC": 30,
  "ETH": 20,
  "SOL": 10,
  "altcoin": 10,
  "etf": {
    "VFEA": 5,
    "IS3N": 5
  }
}
```

Modifica queste percentuali in base alle tue preferenze di investimento.

## Esecuzione dell'Applicazione

Esegui lo script principale nella directory del progetto:

```
python nome_del_tuo_script.py
```

Sostituisci `nome_del_tuo_script.py` con il nome effettivo del file Python contenente il codice dell'applicazione.

## Utilizzo dell'Interfaccia Grafica

### Panoramica

L'interfaccia grafica è suddivisa in diverse sezioni:

- **Pannello Sinistro**: Contiene i pulsanti per interagire con le transazioni e visualizza le barre di progresso che rappresentano la composizione del portafoglio.
- **Sezione Superiore Destra**: Mostra due tabelle con le transazioni FIAT e Crypto/ETF.
- **Sezione Inferiore Destra**: Visualizza i saldi attuali, i guadagni o le perdite percentuali e altre informazioni sul portafoglio.

### Funzionalità Principali

1. **Aggiungere una Transazione FIAT**
   - Clicca su "Aggiungi FIAT" nel pannello sinistro.
   - Nella finestra che si apre, seleziona il tipo di transazione ("Top Up FIAT" per depositi, "Withdraw FIAT" per prelievi).
   - Inserisci l'importo in EUR.
   - Clicca su "Aggiungi Transazione" per salvare.

2. **Aggiungere una Transazione Crypto o ETF**
   - Clicca su "Aggiungi Crypto" nel pannello sinistro.
   - Nella finestra che si apre, inserisci le seguenti informazioni:
     - **Coppia**: Ad esempio, "BTC/USDT" per Bitcoin o "VFEA/EUR" per un ETF.
     - **Tipo di Transazione**: "Buy" o "Sell".
     - **Prezzo**: Il prezzo al quale hai acquistato o venduto.
     - **Quantità Ordinata**: L'importo totale che hai ordinato.
     - **Quantità Eseguita**: L'importo effettivamente eseguito.
     - **Importo Eseguito**: L'importo totale in EUR o USDT pagato o ricevuto.
     - **Commissione di Scambio**: Le commissioni pagate per la transazione.
     - **Tipo di Transazione (Info)**: Seleziona "Transazione" per operazioni normali, "Earn" per interessi ricevuti, "Etf" se si tratta di un ETF.
   - Clicca su "Aggiungi Transazione" per salvare.

3. **Eliminare una Transazione**
   - Seleziona la transazione che desideri eliminare nella tabella corrispondente (FIAT o Crypto).
   - Clicca su "Elimina Transazione" nel pannello sinistro.
   - La transazione verrà rimossa e l'interfaccia si aggiornerà automaticamente.

4. **Aggiornare il Prezzo di un ETF**
   - Clicca su "Modifica Prezzo ETF" nel pannello sinistro.
   - Nella finestra che si apre, inserisci il nome dell'ETF e il nuovo prezzo corrente in EUR.
   - Clicca su "Salva" per aggiornare il prezzo.

### Visualizzazione dei Saldi

La sezione inferiore destra mostra:

- **Unità possedute per ogni asset.**
- **Prezzo medio di acquisto.**
- **Valore corrente in USD e EUR.**
- **Guadagno o perdita percentuale.**

Le informazioni sono suddivise tra:

- **Bilanci Criptovalute**: Dettagli sulle criptovalute possedute.
- **Bilanci ETF**: Dettagli sugli ETF posseduti.
- **Saldo Finale**: Riassunto del saldo in EUR e del valore totale del portafoglio.

### Composizione del Portafoglio

Le barre di progresso nel pannello sinistro rappresentano la percentuale di ogni asset class rispetto al portafoglio totale, confrontata con le percentuali target definite in `percentuali_target.json`.

## Come Funziona l'Applicazione

- **Gestione dei Dati**: I dati delle transazioni e delle configurazioni sono salvati in file JSON nella cartella `data/`.
  
- **Aggiornamento dei Prezzi**:
  - **Criptovalute**: Utilizza l'API di CoinGecko per ottenere i prezzi correnti.
  - **ETF**: I prezzi devono essere aggiornati manualmente dall'utente.
  
- **Calcolo dei Saldi**:
  - Elabora le transazioni per calcolare i saldi attuali.
  - Calcola i prezzi medi di acquisto.
  - Determina guadagni o perdite percentuali.
  
- **Interfaccia Utente**:
  - Fornisce un modo intuitivo per gestire le transazioni.
  - Visualizza informazioni dettagliate sul portafoglio.
  - Permette di monitorare la composizione del portafoglio rispetto agli obiettivi prefissati.

## Note Importanti

- **Backup dei Dati**: È consigliabile effettuare backup regolari dei file JSON per evitare la perdita di dati.
  
- **Precisione dei Dati**: Assicurati di inserire correttamente tutte le informazioni durante l'aggiunta di transazioni per garantire l'accuratezza dei calcoli.
  
- **Limitazioni**:
  - L'applicazione non gestisce eventi straordinari come split di azioni, airdrop di criptovalute, ecc.
  - I prezzi degli ETF devono essere inseriti manualmente.

## Troubleshooting

- **L'applicazione non si avvia**:
  - Verifica di avere installato tutte le dipendenze richieste.
  - Assicurati che i file JSON nella cartella `data/` siano presenti e correttamente formattati.

- **Errore durante l'ottenimento dei prezzi delle criptovalute**:
  - Controlla la connessione internet.
  - Verifica che l'API di CoinGecko sia raggiungibile.

## Contribuire

Se desideri contribuire al progetto:

1. Fai un fork del repository.

2. Crea un branch per le tue modifiche:

```bash
git checkout -b feature/nuova-funzionalita
```

3. Committa le tue modifiche:

```sql
git commit -m "Aggiunta nuova funzionalità"
```

4. Pusha il branch:

```bash
git push origin feature/nuova-funzionalita
```

5. Apri una Pull Request sul repository originale.
