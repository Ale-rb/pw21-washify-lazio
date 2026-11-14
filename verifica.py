import sqlite3
from pathlib import Path
import pandas as pd

conn = sqlite3.connect(Path("data/warehouse")/"Washify_Lazio.db")

print("Connessione al database stabilita.")
query = """
    SELECT 'dim_cliente'     AS 'Nome tabella', COUNT(*) AS 'Numero righe' FROM dim_cliente
    UNION ALL
    SELECT 'dim_fornitore',  COUNT(*) FROM dim_fornitore
    UNION ALL
    SELECT 'dim_operatore',  COUNT(*) FROM dim_operatore
    UNION ALL
    SELECT 'dim_prodotto',   COUNT(*) FROM dim_prodotto
    UNION ALL
    SELECT 'dim_tempo',      COUNT(*) FROM dim_tempo
    UNION ALL
    SELECT 'fact_richieste', COUNT(*) FROM fact_richieste
"""
print(pd.read_sql(query, conn).to_string(index=False))

errori = conn.execute("PRAGMA foreign_key_check;").fetchall()

if len(errori)==0:
    print("Zero errori trovati")
else:
    print("Errori trovati")
    
ordini="""
    SELECT 
        stato AS Stato , COUNT (*) AS Richieste
    FROM fact_richieste
    GROUP BY stato
"""
print(pd.read_sql(ordini,conn).to_string(index=False))

Metriche="""
    SELECT 
        SUM(importo) AS 'Totale incassi in €',
        AVG(tempo_consegna_min) AS 'Tempo medio consegna'
    FROM fact_richieste
    WHERE stato IN ('completata', 'in_ritardo')
"""
print(pd.read_sql(Metriche,conn).to_string(index=False))

Test_X_Prov="""
    SELECT
        dim_cliente.provincia AS Provincia,
        COUNT(*) AS Richieste,
        SUM(fact_richieste.quantita) AS Quantità,
        ROUND(SUM(fact_richieste.importo), 2) AS Incassi,
        ROUND(AVG(fact_richieste.tempo_consegna_min), 1) AS 'Tempo medio'
    FROM fact_richieste
    INNER JOIN dim_cliente ON dim_cliente.sk_cliente=fact_richieste.sk_cliente
    WHERE fact_richieste.stato IN ('completata', 'in_ritardo')
    GROUP BY dim_cliente.provincia
    ORDER BY Richieste DESC
    
"""
print(pd.read_sql(Test_X_Prov,conn).to_string(index=False))

Test_X_Ente="""
    SELECT 
        COUNT(fact_richieste.id_richiesta) AS 'Richieste',
        dim_cliente.tipo AS 'Tipo cliente',
        dim_prodotto.tipo_veicolo AS 'Tipo veicolo'
    FROM fact_richieste
    INNER JOIN dim_cliente ON
        dim_cliente.sk_cliente=fact_richieste.sk_cliente
    INNER JOIN dim_prodotto ON  
        dim_prodotto.sk_prodotto=fact_richieste.sk_prodotto 
    GROUP BY dim_cliente.tipo, dim_prodotto.tipo_veicolo
    ORDER BY dim_cliente.tipo
"""
print(pd.read_sql(Test_X_Ente,conn).to_string(index=False))

Test_X_Ora="""
    SELECT
        fact_richieste.ora AS 'Ora',
        COUNT(*) AS 'Totale richieste'
    FROM fact_richieste
    GROUP BY fact_richieste.ora
    ORDER By fact_richieste.ora
"""
print(pd.read_sql(Test_X_Ora,conn).to_string(index=False))

Test_X_Giorno = """
    SELECT
        dim_tempo.nome_giorno AS 'Giorno',
        COUNT(*) AS 'Richieste'
    FROM fact_richieste
    INNER JOIN dim_tempo ON
        dim_tempo.sk_tempo = fact_richieste.sk_tempo
    GROUP BY dim_tempo.giorno_settimana, dim_tempo.nome_giorno
    ORDER BY dim_tempo.giorno_settimana
"""
print(pd.read_sql(Test_X_Giorno, conn).to_string(index=False))


Test_Clienti_ricor="""
WITH richieste_per_cliente AS (
        SELECT 
            fact_richieste.sk_cliente,
            COUNT(*) AS num_richieste
        FROM fact_richieste
        WHERE stato IN ('completata', 'in_ritardo')
        GROUP BY fact_richieste.sk_cliente
    )
    SELECT 
        COUNT(*) AS clienti_attivi,
        SUM(CASE WHEN num_richieste >= 2 THEN 1 ELSE 0 END) AS clienti_ricorrenti,
        ROUND(SUM(CASE WHEN num_richieste >= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 'ricorrenti_su_attivi_%'
    FROM richieste_per_cliente
"""
print(pd.read_sql(Test_Clienti_ricor, conn).to_string(index=False))

conn.close()