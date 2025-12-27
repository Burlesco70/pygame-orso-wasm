# Gioco dell’Orso 🐻

Implementazione in **Python + Pygame** del *Gioco dell’Orso* (Bear and Hunters Game), un antico gioco da tavolo tradizionale della **Valle del Cervo (Alpi Biellesi)**.

Il progetto nasce come evoluzione di un corso su Pygame ed è stato successivamente esteso con:
- architettura orientata agli oggetti
- utilizzo di sprite e gruppi
- intelligenza artificiale per Orso e Cacciatori
- doppia manche secondo le regole storiche

📖 Maggiori informazioni sul gioco:
https://vallecervobiella.wordpress.com/il-gioco-dellorso/ (in italiano)

---

## 📖 Storia e Logica

Il gioco simula la caccia all'orso:

  - **L'Orso** deve resistere il più a lungo possibile, muovendosi per evitare di essere circondato.
  - **I Cacciatori** devono collaborare per bloccare ogni movimento dell'orso nel minor numero di mosse possibile.
  - **Struttura a due manches**: Per determinare il vincitore, i giocatori si scambiano i ruoli. Vince chi, nei panni dell'orso, riesce a compiere più mosse prima di essere catturato.

## 🚀 Funzionalità

  - 🎮 **Modalità di gioco**: Umano vs Computer o Umano vs Umano (Locale).
  - 🧠 **AI Avanzata**: Orso e Cacciatori utilizzano policy pre-addestrate (`.policy`) per mosse ottimizzate.
  - 🎨 **Interfaccia Grafica**: Gestione completa tramite Sprite, gruppi di collisione e HUD dinamica.
  - 🌐 **Web Ready**: Codice predisposto per la conversione in WebAssembly tramite **Pygbag**.

---

## 🎮 Caratteristiche principali

- Scacchiera da 21 posizioni
- Modalità:
  - Giocatore vs Giocatore
  - Giocatore vs Computer
- Due manches (ruoli invertiti)
- IA dell’Orso (reinforcement learning)
- IA dei Cacciatori (policy deterministica)
- Interfaccia grafica completa con HUD
- Compatibile con **Pygame desktop**
- Eseguibile anche come **WebApp tramite pygbag**

---

## 🧠 Intelligenza Artificiale

- **Orso**: policy di reinforcement learning caricata da file (`bear.policy`)
- **Cacciatori**: policy basata su valutazione degli stati (`hunter.policy`)
- Le policy sono caricate da file pickle esterni

---

## 🌐 Stato pygbag / WebAssembly

⚠️ **Nota importante**

Questa versione:
- ✅ è **funzionante** anche se compilata con **pygbag**
- ❌ **non è ancora ottimizzata per il web**

Limitazioni attuali:
- risoluzione grafica fissa (1280×720)
- asset grafici di grandi dimensioni
- layout non responsive
- HUD e coordinate assolute

👉 Una futura versione ridurrà le dimensioni degli asset e introdurrà adattamento dinamico al canvas browser.

---

## ▶️ Esecuzione in locale

Requisiti:
- Python ≥ 3.11
- pygame ≥ 2.x

Avvio:
```bash
python main.py
```
## 🌐 Compilazione per il Web (Pygbag)

Il codice include il supporto asincrono (`asyncio`) necessario per girare nei moderni browser.

1.  **Installare Pygbag**:
    ```bash
    pip install pygbag
    ```
2.  **Testare il gioco nel browser**:
    Esegui il comando dalla cartella principale del progetto:
    ```bash
    pygbag .
    ```
3.  **Nota sulle prestazioni**: Attualmente la grafica utilizza asset ad alta risoluzione. In ambiente web, il caricamento iniziale potrebbe richiedere alcuni secondi a causa delle dimensioni dei file immagine.

## 📂 Struttura del Progetto

  - `main.py`: Il punto di ingresso principale del gioco.
  - `bear.policy` / `hunter.policy`: File contenenti i dati per l'intelligenza artificiale.
  - `img/`: Contiene gli asset grafici (scacchiera, pedine, pulsanti).
  - `sfx/`: Effetti sonori e musica di sottofondo.
  - `*.otf`: Font utilizzati per l'interfaccia.

## 📝 Note Tecniche

  - **AI**: Implementata tramite una funzione di valore stato-azione caricata via `pickle`.
  - **Asyncio**: Utilizzato per non bloccare il thread principale del browser durante l'esecuzione WebAssembly.

-----