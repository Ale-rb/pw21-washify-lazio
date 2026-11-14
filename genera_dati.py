"""
genera_dati.py
Genera i dati inventati

Uso:  python genera_dati.py
Output: cartella data/raw/ con clienti.csv, fornitori.csv, operatori.csv,
        prodotti.csv, richieste.csv
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# PARAMETRI
SEED = 42
N_CLIENTI = 500
N_FORNITORI = 300
N_OPERATORI = 300
N_RICHIESTE = 600
DIFETTI = True          # True = inserisce qualche difetto voluto da pulire con l'ETL
QUOTA_DIFETTI = 0.03    # circa il 3% delle righe di richieste
CARTELLA = Path("data/raw")

INIZIO_RICHIESTE = datetime(2025, 1, 1)
FINE_RICHIESTE = datetime(2025, 12, 31)

random.seed(SEED)

# DATI DI BASE
PROVINCE = ["Roma", "Latina", "Frosinone", "Viterbo", "Rieti"]
PESO_PROVINCE = [55, 15, 12, 10, 8]           # Roma pesa molto di più

CANALI = ["app", "sito", "passaparola"]

# categoria -> prezzo base per un'unità di prodotto per auto (euro)
N_PRODOTTI=6
CATEGORIE = {"Shampoo": 9,"Cera": 18,"Detergente interni": 8,"Lucidante": 15,"Panni e spugne": 6,"Kit completo": 35,}
VARIANTI = ["Base", "Pro", "Eco"]
MOLTIPLICATORE_CAMION = 4   # le confezioni per camion costano di più

PAROLE_NOME = ["Lucida", "Idro", "Nova", "Eco", "Turbo", "Brill", "Clean","Auto", "Splendor", "Aqua", "Pulito", "Max", "Roma", "Lazio"]
SUFFISSI = ["S.r.l.", "S.n.c.", "& C.", "Group"]

MEZZI = ["moto", "auto", "furgone"]

# stagionalità: si lava di più l'auto in primavera/estate
PESO_MESE = {1: 6, 2: 6, 3: 9, 4: 11, 5: 12, 6: 12,7: 10, 8: 8, 9: 10, 10: 9, 11: 7, 12: 7}
# lunedì=0 ... domenica=6: più ordini nel weekend
PESO_GIORNO = {0: 8, 1: 8, 2: 8, 3: 9, 4: 10, 5: 14, 6: 11}
# ore di punta: mattina (9-12) e fine pomeriggio (17-19)
PESO_ORA = {8: 4, 9: 9, 10: 10, 11: 9, 12: 5, 13: 3, 14: 4,15: 6, 16: 7, 17: 10, 18: 9, 19: 5}


# GENERAZIONE DELLE ANAGRAFICHE
def genera_clienti():
    righe = []
    inizio = datetime(2024, 1, 1)
    giorni = (datetime(2025, 10, 31) - inizio).days
    for i in range(1, N_CLIENTI + 1):
        tipo = random.choices(["privato", "ente"], weights=[85, 15])[0]
        righe.append({
            "id_cliente":f"C{i:04d}",
            "tipo": tipo,
            "provincia": random.choices(PROVINCE, weights=PESO_PROVINCE)[0],
            "data_iscrizione": (inizio + timedelta(days=random.randint(0, giorni))).date(),
            "canale_iscrizione": random.choice(CANALI),
        })
    return pd.DataFrame(righe)


def genera_fornitori():
    righe = []
    for i in range(1, N_FORNITORI + 1):
        nome = f"{random.choice(PAROLE_NOME)} {random.choice(PAROLE_NOME)} {random.choice(SUFFISSI)}"
        righe.append({
            "id_fornitore":f"F{i:04d}",
            "nome": nome,
            "provincia": random.choices(PROVINCE, weights=PESO_PROVINCE)[0],
        })
    return pd.DataFrame(righe)


def genera_operatori():
    righe = []
    for i in range(1, N_OPERATORI + 1):
        righe.append({
            "id_operatore":f"0{i:04d}",
            "provincia": random.choices(PROVINCE, weights=PESO_PROVINCE)[0],
            "mezzo": random.choice(MEZZI),
            "anni_esperienza": random.randint(0, 20),
        })
    return pd.DataFrame(righe)


def genera_prodotti():
    righe = []
    i = 1
    for categoria, prezzo in CATEGORIE.items():
        for tipo_veicolo in ["auto", "camion"]:
            for variante in VARIANTI:
                prezzo_base = prezzo * (MOLTIPLICATORE_CAMION if tipo_veicolo == "camion" else 1)
                # la variante Pro costa di più, la Eco un po' meno
                fattore = {"Base": 1.0, "Pro": 1.3, "Eco": 0.9}[variante]
                righe.append({
                    "id_prodotto": f"P{i:04d}",
                    "nome": f"{categoria} {variante} ({tipo_veicolo})",
                    "categoria": categoria,
                    "tipo_veicolo": tipo_veicolo,
                    "prezzo_listino": round(prezzo_base * fattore, 2),
                })
                i += 1
    return pd.DataFrame(righe)


# GENERAZIONE DELLE RICHIESTE
def prepara_giorni():
    giorni, pesi = [], []
    giorno = INIZIO_RICHIESTE
    while giorno <= FINE_RICHIESTE:
        giorni.append(giorno)
        pesi.append(PESO_MESE[giorno.month] * PESO_GIORNO[giorno.weekday()])
        giorno += timedelta(days=1)
    return giorni, pesi


def genera_richieste(clienti, fornitori, operatori, prodotti):
    giorni, pesi_giorni = prepara_giorni()
    ore = list(PESO_ORA.keys())
    pesi_ore = list(PESO_ORA.values())

    # alcuni clienti ordinano molto più spesso di altri (serve per i clienti ricorrenti);
    # gli enti ordinano più spesso dei privati
    pesi_clienti = []
    for _, c in clienti.iterrows():
        peso = random.choice([1, 1, 1, 2, 4, 8])
        if c["tipo"] == "ente":
            peso *= 3
        pesi_clienti.append(peso)

    prodotti_auto = prodotti[prodotti["tipo_veicolo"] == "auto"]
    prodotti_camion = prodotti[prodotti["tipo_veicolo"] == "camion"]
    operatori_per_provincia = {p: g["id_operatore"].tolist()for p, g in operatori.groupby("provincia")}
    tutti_operatori = operatori["id_operatore"].tolist()
    tutti_fornitori = fornitori["id_fornitore"].tolist()

    righe = []
    for i in range(1, N_RICHIESTE + 1):
        # cliente e data: la data non può precedere l'iscrizione del cliente
        while True:
            idx = random.choices(range(len(clienti)), weights=pesi_clienti)[0]
            cliente = clienti.iloc[idx]
            giorno = random.choices(giorni, weights=pesi_giorni)[0]
            if giorno.date() >= cliente["data_iscrizione"]:
                break
        ora = random.choices(ore, weights=pesi_ore)[0]
        data_ora = giorno.replace(hour=ora, minute=random.randint(0, 59))

        # prodotto: i privati comprano quasi solo per auto, gli enti molto per camion
        if cliente["tipo"] == "ente":
            per_camion = random.random() < 0.60
        else:
            per_camion = random.random() < 0.03
        scelti = prodotti_camion if per_camion else prodotti_auto
        prodotto = scelti.iloc[random.randrange(len(scelti))]

        # quantità e importo (sconto per ordini grandi)
        if cliente["tipo"] == "ente":
            quantita = random.randint(5, 30)
        else:
            quantita = random.randint(1, 4)
        sconto = 0.90 if quantita >= 10 else 1.0
        importo = round(prodotto["prezzo_listino"] * quantita * sconto, 2)

        # operatore della stessa provincia del cliente (se esiste)
        candidati = operatori_per_provincia.get(cliente["provincia"], tutti_operatori)
        id_operatore = random.choice(candidati)

        # stato e tempo di consegna (in minuti)
        stato = random.choices(["completata", "in_ritardo", "annullata"],
                               weights=[80, 12, 8])[0]
        base = random.randint(60, 180)
        if cliente["provincia"] == "Roma":
            base += 25                        # traffico
        if stato == "in_ritardo":
            tempo = base + random.randint(60, 180)
        else:
            tempo = base
        if stato == "annullata":              # nessun incasso e nessuna consegna
            importo, tempo = None, None

        righe.append({"id_richiesta": i,"id_cliente": (cliente["id_cliente"]),"id_fornitore": random.choice(tutti_fornitori),"id_operatore": id_operatore,
            "id_prodotto": (prodotto["id_prodotto"]), "data_ora": data_ora.strftime("%Y-%m-%d %H:%M"),"quantita": quantita,"importo": importo,
            "tempo_consegna_min": tempo,
            "stato": stato,
        })
    return pd.DataFrame(righe)

# DIFETTI VOLUTI

def introduci_difetti(richieste, clienti):
    richieste = richieste.copy()
    n = max(1, int(len(richieste) * QUOTA_DIFETTI))

    # 1. importi scritti con la virgola decimale (diventano testo)
    richieste["importo"] = richieste["importo"].astype("object")
    for idx in random.sample(list(richieste.index), n):
        valore = richieste.at[idx, "importo"]
        if pd.notna(valore):
            richieste.at[idx, "importo"] = str(valore).replace(".", ",")

    # 2. date in un altro formato (gg/mm/aaaa hh:mm)
    for idx in random.sample(list(richieste.index), n):
        d = datetime.strptime(richieste.at[idx, "data_ora"], "%Y-%m-%d %H:%M")
        richieste.at[idx, "data_ora"] = d.strftime("%d/%m/%Y %H:%M")

    # 3. stati scritti in modo incoerente
    for idx in random.sample(list(richieste.index), n):
        richieste.at[idx, "stato"] = random.choice(
            [richieste.at[idx, "stato"].upper(), " " + richieste.at[idx, "stato"]])

    # 4. righe duplicate
    duplicate = richieste.sample(n, random_state=SEED)
    richieste = pd.concat([richieste, duplicate], ignore_index=True)

    # 5. provincia dei clienti con maiuscole/spazi incoerenti
    clienti = clienti.copy()
    for idx in random.sample(list(clienti.index), n):
        p = clienti.at[idx, "provincia"]
        clienti.at[idx, "provincia"] = random.choice([p.upper(), p.lower(), " " + p + " "])

    return richieste, clienti

# MAIN
def main():
    CARTELLA.mkdir(parents=True, exist_ok=True)

    clienti = genera_clienti()
    fornitori = genera_fornitori()
    operatori = genera_operatori()
    prodotti = genera_prodotti()
    richieste = genera_richieste(clienti, fornitori, operatori, prodotti)

    if DIFETTI:
        richieste, clienti = introduci_difetti(richieste, clienti)

    clienti.to_csv(CARTELLA / "clienti.csv", index=False, sep=";")
    fornitori.to_csv(CARTELLA / "fornitori.csv", index=False, sep=";")
    operatori.to_csv(CARTELLA / "operatori.csv", index=False, sep=";")
    prodotti.to_csv(CARTELLA / "prodotti.csv", index=False, sep=";")
    richieste.to_csv(CARTELLA / "richieste.csv", index=False, sep=";")

    print(f"Creati i file in {CARTELLA}")
    print(f"  clienti:   {len(clienti)}")
    print(f"  fornitori: {len(fornitori)}")
    print(f"  operatori: {len(operatori)}")
    print(f"  prodotti:  {len(prodotti)}")
    print(f"  richieste: {len(richieste)}")


if __name__ == "__main__":
    main()
