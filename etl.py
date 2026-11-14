"""ETL del data warehouse Washify Lazio: legge i CSV in data/raw, li pulisce
e carica le dimensioni e la tabella dei fatti in data/warehouse/Washify_Lazio.db.
Uso: python etl.py"""


import sqlite3
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
CARTELLA_DB = Path("data/warehouse")

INIZIO_CALENDARIO = '2025-01-01'
FINE_CALENDARIO = '2025-12-31'

GIORNI = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']

def carica_dim_cliente(conn, clienti):
    # Pulizia
    clienti = clienti.drop_duplicates(subset='id_cliente')
    clienti['provincia']=clienti['provincia'].str.strip().str.title()
    clienti['tipo']=clienti['tipo'].str.strip().str.title()
    clienti['canale_iscrizione']=clienti['canale_iscrizione'].str.strip().str.title()
    clienti.insert(0, 'sk_cliente', range(1, len(clienti) + 1))

    # Creazione della tabella con la chiave primaria
    conn.execute("DROP TABLE IF EXISTS dim_cliente")
    conn.execute("""
        CREATE TABLE dim_cliente (
            sk_cliente        INTEGER PRIMARY KEY,
            id_cliente        INTEGER NOT NULL UNIQUE,
            tipo              TEXT,
            provincia         TEXT,
            data_iscrizione   TEXT,
            canale_iscrizione TEXT
        )
    """)

    # Caricamento
    clienti.to_sql('dim_cliente', conn, if_exists='append', index=False)
    conn.commit()

def carica_dim_fornitore(conn,fornitori):
    # Pulizia
    fornitori=fornitori.drop_duplicates(subset='id_fornitore')
    fornitori['provincia']=fornitori['provincia'].str.strip().str.title()
    fornitori['nome']=fornitori['nome'].str.strip()
    fornitori.insert(0, 'sk_fornitore', range(1, len(fornitori) + 1))
    
    # Creazione della tabella con la chiave primaria
    conn.execute("DROP TABLE IF EXISTS dim_fornitore")
    conn.execute("""
        CREATE TABLE dim_fornitore (
            sk_fornitore      INTEGER PRIMARY KEY,
            id_fornitore      INTEGER NOT NULL UNIQUE,
            nome              TEXT,
            provincia         TEXT
        )
    """)
    
    fornitori.to_sql('dim_fornitore', conn, if_exists='append', index=False)
    conn.commit()

def carica_dim_operatore(conn,operatori):
    #Pulizia
    operatori=operatori.drop_duplicates(subset='id_operatore')
    operatori['provincia']=operatori['provincia'].str.strip().str.title()
    operatori['mezzo']=operatori['mezzo'].str.strip().str.title()
    operatori.insert(0,'sk_operatore',range(1,len(operatori)+1))
    
    # Creazione della tabella con la chiave primaria
    conn.execute("DROP TABLE IF EXISTS dim_operatore")
    conn.execute("""
            CREATE TABLE dim_operatore(
                sk_operatore       INTEGER PRIMARY KEY,
                id_operatore       INTEGER NOT NULL UNIQUE,
                provincia          TEXT,
                mezzo              TEXT,
                anni_esperienza    INTEGER
            )
                 
    """)
    
    operatori.to_sql('dim_operatore',conn,if_exists='append',index=False)
    conn.commit()

def carica_dim_prodotto(conn,prodotto):
    prodotto=prodotto.drop_duplicates(subset='id_prodotto')
    prodotto['categoria']=prodotto['categoria'].str.strip()
    prodotto['nome']=prodotto['nome'].str.strip()
    prodotto['tipo_veicolo']=prodotto['tipo_veicolo'].str.strip().str.title()
    prodotto.insert(0, 'sk_prodotto', range(1, len(prodotto) + 1))
    
    conn.execute("DROP TABLE IF EXISTS dim_prodotto")
    conn.execute("""
            CREATE TABLE dim_prodotto(
                sk_prodotto     INTEGER PRIMARY KEY,
                id_prodotto     INTEGER NOT NULL UNIQUE,
                nome            TEXT,
                categoria       TEXT,
                tipo_veicolo    TEXT,
                prezzo_listino  REAL
            )
    """)
    
    prodotto.to_sql('dim_prodotto',conn,if_exists='append',index=False)
    conn.commit()
    

def converti_date(serie):
    d = pd.to_datetime(serie, format='%Y-%m-%d %H:%M', errors='coerce')
    d2 = pd.to_datetime(serie, format='%d/%m/%Y %H:%M', errors='coerce')
    return d.fillna(d2)

def carica_dim_tempo(conn):
    righe=[]
    for i in pd.date_range(start=INIZIO_CALENDARIO, end=FINE_CALENDARIO):
        righe.append({
            'sk_tempo': int(i.strftime('%Y%m%d')),
            'data': i.strftime('%Y-%m-%d'),
            'anno':i.year,
            'mese':i.month,
            'giorno':i.day,
            'trimestre':(i.month-1)//3+1,
            'giorno_settimana':i.weekday()+1,
            'nome_giorno':GIORNI[i.weekday()],
        })
    dim_tempo_df=pd.DataFrame(righe)
    conn.execute("DROP TABLE IF EXISTS dim_tempo")
    conn.execute("""
        CREATE TABLE dim_tempo (
            sk_tempo          INTEGER PRIMARY KEY,
            data              TEXT NOT NULL UNIQUE,
            anno              INTEGER,
            mese              INTEGER,
            giorno            INTEGER,
            trimestre         INTEGER,
            giorno_settimana  INTEGER,
            nome_giorno       TEXT
        )
    """)
    dim_tempo_df.to_sql('dim_tempo', conn, if_exists='append', index=False)
    conn.commit()
    
def carica_fact_richieste(conn,richieste):
    #Pulizia dati divisi per colonne
    # Duplicati
    richieste = richieste.drop_duplicates(subset='id_richiesta')
    
    # Stato
    richieste['stato']=richieste['stato'].str.strip().str.lower()
    
    # Importo
    richieste['importo']=richieste['importo'].astype(str).str.replace(',', '.')
    richieste['importo']=pd.to_numeric(richieste['importo'], errors='coerce')
    
    #Estrazione dati da colonna tempo
    richieste['sk_tempo']=richieste['data_ora'].dt.strftime('%Y%m%d').astype(int)
    richieste['ora']=richieste['data_ora'].dt.hour
    
    #INIZIO MERGE TABELLE
    #Chiavi surrogate
    dim_cliente=pd.read_sql("SELECT sk_cliente,id_cliente FROM dim_cliente",conn)
    richieste=pd.merge(richieste,dim_cliente,on='id_cliente',how='left')

    dim_fornitore=pd.read_sql("SELECT sk_fornitore,id_fornitore FROM dim_fornitore",conn)
    richieste=pd.merge(richieste,dim_fornitore,on='id_fornitore',how='left')
    
    dim_operatore=pd.read_sql("SELECT sk_operatore,id_operatore FROM dim_operatore",conn)
    richieste=pd.merge(richieste,dim_operatore,on='id_operatore',how='left')
    
    dim_prodotto=pd.read_sql("SELECT sk_prodotto,id_prodotto FROM dim_prodotto",conn)
    richieste=pd.merge(richieste,dim_prodotto,on='id_prodotto',how='left')
    
    #Selezione colonne finali per tabella
    richieste=richieste[['id_richiesta','sk_cliente','sk_fornitore','sk_operatore','sk_prodotto','sk_tempo','ora','quantita','importo','tempo_consegna_min','stato']]
    
    #Creazione tabella fact_richieste
    conn.execute("DROP TABLE IF EXISTS fact_richieste")
    conn.execute("""
        CREATE TABLE fact_richieste (
            id_richiesta          INTEGER PRIMARY KEY,
            sk_cliente            INTEGER NOT NULL,
            sk_fornitore          INTEGER NOT NULL,
            sk_operatore          INTEGER NOT NULL,
            sk_prodotto           INTEGER NOT NULL,
            sk_tempo              INTEGER NOT NULL,
            ora                   INTEGER,
            quantita              INTEGER,
            importo               REAL,
            tempo_consegna_min    REAL,
            stato                 TEXT,
            FOREIGN KEY (sk_cliente) REFERENCES dim_cliente(sk_cliente),
            FOREIGN KEY (sk_fornitore) REFERENCES dim_fornitore(sk_fornitore),
            FOREIGN KEY (sk_operatore) REFERENCES dim_operatore(sk_operatore),
            FOREIGN KEY (sk_prodotto) REFERENCES dim_prodotto(sk_prodotto),
            FOREIGN KEY (sk_tempo) REFERENCES dim_tempo(sk_tempo)
        )
    """)
    richieste.to_sql('fact_richieste', conn, if_exists='append', index=False)
    conn.commit()

def esporta_csv(conn):
    cartella = Path("data/export")
    cartella.mkdir(parents=True, exist_ok=True)
    for tabella in ['dim_cliente', 'dim_fornitore', 'dim_operatore',
                    'dim_prodotto', 'dim_tempo', 'fact_richieste']:
        dati = pd.read_sql(f'SELECT * FROM {tabella}', conn)
        dati.to_csv(cartella / f'{tabella}.csv', index=False, sep=';')
    
def main():
    CARTELLA_DB.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CARTELLA_DB / 'Washify_Lazio.db')
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DROP TABLE IF EXISTS fact_richieste")
    
    clienti=pd.read_csv(RAW / 'clienti.csv', sep=';')
    carica_dim_cliente(conn, clienti)

    fornitori=pd.read_csv(RAW / 'fornitori.csv', sep=';')
    carica_dim_fornitore(conn, fornitori)
    
    operatori=pd.read_csv(RAW/'operatori.csv',sep=';')
    carica_dim_operatore(conn,operatori)
    
    prodotto=pd.read_csv(RAW/'prodotti.csv',sep=';')
    carica_dim_prodotto(conn,prodotto)
    
    carica_dim_tempo(conn)
    
    richieste=pd.read_csv(RAW / 'richieste.csv', sep=';')
    richieste['data_ora'] = converti_date(richieste['data_ora'])

    carica_fact_richieste(conn, richieste)

    esporta_csv(conn)
    
    conn.close()
    
if __name__ == "__main__":
    main()