'''
Versione del gioco "finale" dopo il corso su PyGame
1 - https://youtu.be/rdT_Z23YRAY
2 - https://youtu.be/xG4IKcAzMCw
3 - https://youtu.be/V3VuqFeJ1hc
ovvero con utilizzo di Sprites e gruppi di collisioni
e maggiore orientamento OOP
----------------------------------------------------------------
10-2022 - Aggiunta AI Orso
02-2023 - Aggiunta AI Cacciatori
04-2023 - Impostazione a due manches dopo chiarimenti con i ricercatori del DocBi
12-2025 - Scalato a 1280x720 per supporto WebASM e dispositivi con schermi diversi
'''

from __future__ import annotations
from typing import List, Tuple
import asyncio
import os
import pygame
import sys
import functools
import random
import pickle

# Rileva se l'esecuzione avviene in ambiente WebASM (browser)
IS_WEB = sys.platform == "emscripten"

INFINITY = float('inf')

# ========== CONFIGURAZIONE COLORI ==========
BLACK = (0, 0, 0)
RED = (255, 0, 0)

# ========== SIMBOLI PER LA SCACCHIERA ==========
# Simboli usati nella rappresentazione logica della board
BOARD_HUNTER_1 = '1'  # Primo cacciatore
BOARD_HUNTER_2 = '8'  # Secondo cacciatore
BOARD_HUNTER_3 = '9'  # Terzo cacciatore
BOARD_BEAR = '2'      # Orso
BOARD_EMPTY = '_'     # Casella vuota

# Simbolo normalizzato per le policy AI (tutti i cacciatori sono uguali per l'AI)
BOARD_HUNTER_POLICY = '1'

# Flag per abilitare/disabilitare la musica
MUSIC = True

class GamePlayer:
    '''
    Rappresenta un giocatore nelle due manches del gioco.
    Tiene traccia del nome, tipo (umano/computer), ruolo (cacciatore/orso)
    e numero di mosse fatte come orso.
    '''
    def __init__(self, name, is_human, is_hunter) -> None:
        self.name = name              # Nome visualizzato (es. "Tu", "Computer")
        self.is_human = is_human      # True se giocatore umano, False se AI
        self.bear_moves = 0           # Mosse completate quando gioca come orso
        self.is_hunter = is_hunter    # True se in questo turno è cacciatore


class BearGameManche:
    '''
    Gestisce la logica di una singola manche del gioco.
    Questa classe è indipendente da PyGame e contiene solo la logica del gioco.
    
    La scacchiera ha 21 posizioni numerate da 0 a 20:
    - '_' indica una casella vuota
    - '1', '8', '9' indicano i tre cacciatori
    - '2' indica l'orso
    '''
    
    # ========== CONFIGURAZIONE GIOCO ==========
    BOARD_POSITIONS = 21           # Numero totale di posizioni sulla scacchiera
    MAX_BEAR_MOVES = 40            # Mosse massime per la vittoria dell'orso
    HUNTER_STARTS = False          # Se True, iniziano i cacciatori
    
    # Definisce quali posizioni sono adiacenti a ciascuna casella
    # L'indice della lista corrisponde alla posizione sulla board
    ADJACENT_POSITIONS = [
        [1,2,3],        # Posizione 0: collegata a 1,2,3
        [0,3,4],        # Posizione 1: collegata a 0,3,4
        [0,3,6],        # Posizione 2: collegata a 0,3,6
        [0,1,2,5],      # Posizione 3: nodo centrale, 4 collegamenti
        [1,7,8],        # Posizione 4
        [3,9,10,11],    # Posizione 5: nodo importante con 4 collegamenti
        [2,12,13],      # Posizione 6
        [4,8,14],       # Posizione 7
        [7,4,14,9],     # Posizione 8: 4 collegamenti
        [8,10,5,15],    # Posizione 9: 4 collegamenti
        [5,9,11,15],    # Posizione 10: 4 collegamenti
        [5,10,15,12],   # Posizione 11: 4 collegamenti
        [11,6,16,13],   # Posizione 12: 4 collegamenti
        [6,12,16],      # Posizione 13
        [7,8,18],       # Posizione 14
        [9,10,11,17],   # Posizione 15: nodo importante con 4 collegamenti
        [12,13,19],     # Posizione 16
        [15,18,19,20],  # Posizione 17: nodo importante con 4 collegamenti
        [14,17,20],     # Posizione 18
        [16,17,20],     # Posizione 19
        [18,17,19]      # Posizione 20: posizione iniziale classica dell'orso
    ]

    def __init__(self, 
                 first_manche_as_bear: bool,
                 against_computer: bool, 
                 classic_initial_position: bool):
        '''
        Inizializza una manche e carica le policy per l'AI.
        
        Args:
            first_manche_as_bear: True se il giocatore umano inizia come orso
            against_computer: True se si gioca contro l'AI
            classic_initial_position: True per posizione iniziale classica (cacciatori in alto, orso in basso)
        '''
        base_path = "."
        
        # Imposta la configurazione iniziale della board
        self.reset(against_computer, classic_initial_position)
        self.first_manche_as_bear = first_manche_as_bear
        
        # ========== CARICAMENTO AI ORSO ==========
        # Carica la policy appresa tramite Reinforcement Learning
        self._bear_player = Player("orso")
        self._bear_player.load_policy(
            os.path.join(base_path, "bear.policy")
        )

        # ========== CARICAMENTO AI CACCIATORE ==========
        # Carica la policy deterministica basata sulla distanza
        self._hunter_player = Player("cacciatore")
        self._hunter_player.load_policy(
            os.path.join(base_path, "hunter.policy")
        )
        
    def reset(self, against_computer: bool, classic_initial_position: bool) -> None:
        '''
        Reimposta la board e le variabili di gioco per iniziare una nuova manche.
        
        Ci sono due configurazioni iniziali possibili:
        1. Classica: cacciatori in posizioni 0,1,2 - orso in posizione 20
        2. Centrale (Iacazio): configurazione più bilanciata per partite veloci
        '''
        if classic_initial_position:
            # Configurazione classica: cacciatori raggruppati in alto
            self._board = [
                BOARD_HUNTER_1, BOARD_HUNTER_2, BOARD_HUNTER_3,  # Pos 0,1,2: cacciatori
                BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY,
                BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, 
                BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY,
                BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, 
                BOARD_EMPTY, BOARD_EMPTY, 
                BOARD_BEAR  # Pos 20: orso
            ]
            self._bear_position = 20            
        else:
            # Configurazione centrale "Iacazio" per partite più veloci
            self._board = [
                BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, 
                BOARD_HUNTER_1,  # Pos 5
                BOARD_EMPTY,
                BOARD_EMPTY, BOARD_EMPTY, 
                BOARD_HUNTER_2,  # Pos 9
                BOARD_BEAR,      # Pos 10: orso al centro
                BOARD_HUNTER_3,  # Pos 11
                BOARD_EMPTY, BOARD_EMPTY,
                BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, 
                BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY
            ]
            self._bear_position = 10            
        
        # Inizializza le variabili di stato
        self._bear_moves = 0                    # Contatore mosse orso
        self._hunter_starting_pos = -1          # Posizione cacciatore selezionato (-1 = nessuno)
        self._hunter_ai_final = -1              # Destinazione AI cacciatore
        self._is_hunter_turn = self.HUNTER_STARTS  # Di chi è il turno
        self.against_computer = against_computer
        self._winner = None                     # Messaggio del vincitore
        self._last_move = None                  # Ultima mossa effettuata (per undo)

    # ========== METODI GETTER ==========
    
    def get_bear_moves(self) -> int:
        '''Restituisce il numero di mosse completate dall'orso.'''
        return self._bear_moves

    def get_max_bear_moves(self) -> int:
        '''Restituisce il numero massimo di mosse per la vittoria dell'orso.'''
        return self.MAX_BEAR_MOVES

    def get_board_position(self, position: int) -> str:
        '''
        Restituisce il simbolo ('1','8','9','2','_') presente nella posizione specificata.
        
        Args:
            position: Indice della posizione (0-20)
        Returns:
            Stringa con il simbolo della pedina o '_' per vuoto
        '''
        return self._board[position]

    def get_hunter_starting_pos(self) -> int:
        '''
        Restituisce la posizione del cacciatore attualmente selezionato.
        Returns -1 se nessun cacciatore è selezionato.
        '''
        return self._hunter_starting_pos
    
    # ========== METODI DI CONTROLLO VITTORIA ==========
    
    def is_bear_winner(self) -> bool:
        '''
        Verifica se l'orso ha vinto.
        L'orso vince se raggiunge MAX_BEAR_MOVES mosse.
        '''
        # L'orso perde se non ha mosse disponibili
        if not(self.get_possible_moves(self._bear_position)):
            return False
        # L'orso vince se raggiunge il numero massimo di mosse
        if (self._bear_moves >= self.MAX_BEAR_MOVES):
            return True

    def game_over(self) -> bool:
        '''
        Verifica se la manche è terminata e imposta il messaggio del vincitore.
        
        Returns:
            True se la partita è finita, False altrimenti
        '''
        # Cacciatori vincono se l'orso non ha mosse disponibili
        if not(self.get_possible_moves(self._bear_position)):
            self._winner = f"I cacciatori vincono; l'orso ha fatto {self.get_bear_moves()} mosse"
            return True
        # Orso vince se raggiunge il numero massimo di mosse
        elif (self._bear_moves >= self.MAX_BEAR_MOVES):
            self._winner = f"L'orso è scappato; ha fatto {self.get_bear_moves()} mosse"
            return True
        else:
            return False

    # ========== METODI DI UTILITÀ ==========
    
    def is_hunter(self, selection: str) -> bool:
        '''Verifica se il simbolo rappresenta un cacciatore.'''
        return selection in [BOARD_HUNTER_1, BOARD_HUNTER_2, BOARD_HUNTER_3]

    def is_hunter_turn(self) -> bool:
        '''Verifica se è il turno dei cacciatori.'''
        return self._is_hunter_turn

    # ========== GESTIONE MOSSE CACCIATORE (UMANO) ==========
    
    def manage_hunter_selection(self, sel: int) -> str:
        '''
        Gestisce la selezione e il movimento dei cacciatori da parte del giocatore umano.
        Il processo è in due fasi: prima si seleziona un cacciatore, poi la destinazione.
        
        Args:
            sel: Posizione selezionata dal giocatore
        Returns:
            Messaggio da visualizzare all'utente
        '''
        # FASE 1: Selezione del cacciatore
        if self._hunter_starting_pos == -1:
            if not(self.is_hunter(self._board[sel])):
                return "Seleziona un cacciatore!"
            else:
                # Cacciatore selezionato, aspetta la destinazione
                self._hunter_starting_pos = sel
                return "Cacciatore, fa' la tua mossa!"
        
        # FASE 2: Selezione della destinazione
        else:
            if sel in self.get_possible_moves(self._hunter_starting_pos):
                # Mossa valida: sposta il cacciatore
                selected_hunter = self._board[self._hunter_starting_pos]
                self._board[self._hunter_starting_pos] = BOARD_EMPTY
                self._board[sel] = selected_hunter
                self._hunter_starting_pos = -1  # Reset selezione
                self._is_hunter_turn = not(self._is_hunter_turn)  # Cambia turno
                return "Orso, scegli la tua mossa!"
            else:
                # Mossa non valida: torna alla fase di selezione
                self._hunter_starting_pos = -1
                return "Posizione non valida!"
    
    # ========== GESTIONE MOSSE CACCIATORE (AI) ==========
    
    async def manage_ai_hunter_selection(self) -> str:
        '''
        Gestisce la mossa dell'AI cacciatore usando la policy precalcolata.
        Simula il comportamento umano in due fasi: selezione e movimento.
        '''
        # FASE 1: Selezione del cacciatore da muovere
        if (self._hunter_starting_pos == -1):
            # Trova tutte le posizioni dei cacciatori
            hunter_positions = []
            for x in range(self.BOARD_POSITIONS):
                if self._board[x] in [BOARD_HUNTER_1, BOARD_HUNTER_2, BOARD_HUNTER_3]:
                    hunter_positions.append(x)

            # Genera tutte le possibili azioni (cacciatore, destinazione)
            hunter_actions = []
            for x in hunter_positions:
                moves = self.get_possible_moves(x)
                for move in moves:
                    hunter_actions.append((x, move))                    

            # Usa la policy AI per scegliere la migliore azione
            action = self._hunter_player.get_action(hunter_actions, self)
            self._hunter_starting_pos = action[0]  # Cacciatore scelto
            self._hunter_ai_final = action[1]      # Destinazione scelta
            return "Cacciatore selezionato"
        
        # FASE 2: Esecuzione della mossa
        else:
            self._board[self._hunter_ai_final] = self._board[self._hunter_starting_pos]            
            self._board[self._hunter_starting_pos] = BOARD_EMPTY
            self._hunter_starting_pos = -1
            self._hunter_ai_final = -1
            self._is_hunter_turn = not self._is_hunter_turn
            # Pausa per simulare il "pensiero" dell'AI
            await asyncio.sleep(1)
            return "Orso, scegli la tua mossa!"

    # ========== GESTIONE MOSSE ORSO ==========
    
    def get_bear_actions(self) -> List[Tuple[int, int]]:
        '''
        Restituisce tutte le azioni possibili per l'orso.
        
        Returns:
            Lista di tuple (posizione_corrente, destinazione_possibile)
        '''
        actions = []
        for adj in BearGameManche.ADJACENT_POSITIONS[self._bear_position]:
            if self._board[adj] == BOARD_EMPTY:
                actions.append((self._bear_position, adj))
        return actions

    def move_bear(self, new_position: int) -> None:
        '''
        Muove l'orso in una nuova posizione.
        Questo metodo è usato sia dall'AI che dal metodo move_player.
        
        Args:
            new_position: Posizione di destinazione
        Raises:
            ValueError: Se la mossa non è valida
        '''
        self._last_move = (self._bear_position, new_position)
        
        if new_position in self.get_possible_moves(self._bear_position):
            self._board[self._bear_position] = BOARD_EMPTY
            self._board[new_position] = BOARD_BEAR
            self._bear_position = new_position
            self._bear_moves += 1  # Incrementa il contatore
            self._is_hunter_turn = not self._is_hunter_turn
        else:
            print(self._last_move)
            raise ValueError("Orso non può muoversi qui!")

    def move_hunter(self, start_position: int, end_position: int) -> None:
        '''
        Muove un cacciatore da una posizione a un'altra.
        Usato dal metodo move_player per l'AI.
        '''
        self._last_move = (start_position, end_position)
        start_symbol = self._board[start_position]
        self._board[start_position] = BOARD_EMPTY
        self._board[end_position] = start_symbol
        self._is_hunter_turn = not self._is_hunter_turn

    def move_player(self, start_pos, end_pos) -> None:
        '''
        Interfaccia generica per muovere un giocatore.
        Chiama move_hunter o move_bear in base al turno.
        Usato dall'AI per simulare mosse durante la ricerca.
        '''
        if self._is_hunter_turn:
            return self.move_hunter(start_pos, end_pos)
        else:
            return self.move_bear(end_pos)

    async def manage_ai_smart_bear_selection(self) -> str:
        '''
        Gestisce la mossa dell'AI orso usando la policy di Reinforcement Learning.
        '''
        # Pausa per simulare il "pensiero"
        await asyncio.sleep(1)
        
        # Ottiene tutte le azioni possibili
        bear_actions = self.get_bear_actions()
        
        # Usa la policy AI per scegliere la migliore
        action = self._bear_player.get_action(bear_actions, self)
        
        # Esegue la mossa
        self.move_bear(action[1])
        
        return "L'orso intelligente ha mosso!"
    
    def manage_bear_selection(self, sel: int) -> str:
        '''
        Gestisce la mossa dell'orso controllato da un giocatore umano.
        
        Args:
            sel: Posizione selezionata dal giocatore
        Returns:
            Messaggio da visualizzare
        '''
        if sel in self.get_possible_moves(self._bear_position):
            # Mossa valida: sposta l'orso
            self._board[self._bear_position] = BOARD_EMPTY
            self._board[sel] = BOARD_BEAR
            self._bear_moves += 1
            self._bear_position = sel
            self._is_hunter_turn = not(self._is_hunter_turn)
            return "Seleziona uno dei cacciatori!"
        else:
            return "Posizione non valida..."
    
    # ========== METODI PER LA VISUALIZZAZIONE ==========
    
    def is_footprint_and_type(self, sel: int) -> tuple[bool, str]:
        '''
        Verifica se una posizione è una destinazione valida (orma).
        Le orme vengono visualizzate per indicare dove può muoversi il giocatore.
        
        Args:
            sel: Posizione da controllare
        Returns:
            Tupla (è_orma, tipo_orma) dove tipo_orma è "HUNTER" o "BEAR" o None
        '''
        if self._is_hunter_turn:
            # Se è il turno dei cacciatori e uno è selezionato
            if self._hunter_starting_pos == -1:
                return (False, None)
            else:
                if sel in self.get_possible_moves(self._hunter_starting_pos):
                    return (True, "HUNTER")
                else:
                    return (False, None)
        else:
            # Se è il turno dell'orso
            if sel in self.get_possible_moves(self._bear_position):
                return (True, "BEAR")
            else:
                return (False, None)

    def get_possible_moves(self, position: int) -> list[int]:
        '''
        Restituisce tutte le posizioni libere adiacenti a una posizione data.
        
        Args:
            position: Posizione di partenza
        Returns:
            Lista di posizioni libere raggiungibili
        '''
        moves = []
        # Controlla tutte le posizioni adiacenti
        for x in BearGameManche.ADJACENT_POSITIONS[position]:
            if self._board[x] == BOARD_EMPTY:
                moves.append(x)
        return moves

    # ========== METODI PER L'AI ==========
    
    def get_hash(self) -> str:
        '''
        Genera un hash univoco dello stato della board per l'AI.
        Normalizza i cacciatori (1,8,9 -> tutti '1') perché per l'AI
        sono indistinguibili.
        
        Returns:
            Stringa che rappresenta lo stato della board
        '''
        board = self._board.copy()
        
        # Normalizza gli ID dei cacciatori per il modello di RL
        for i in range(len(board)):
            if board[i] in [BOARD_HUNTER_3, BOARD_HUNTER_2, BOARD_HUNTER_1]:
                board[i] = BOARD_HUNTER_POLICY
        
        return ''.join(board)

    def undo_move(self) -> None:
        '''
        Annulla l'ultima mossa effettuata.
        Usato dall'AI per esplorare diverse possibilità durante la ricerca.
        '''
        self._is_hunter_turn = not self._is_hunter_turn
        target_position, starting_position = self._last_move  # Invertiti!
        start_symbol = self._board[starting_position]
        self._board[starting_position] = BOARD_EMPTY
        
        if self._is_hunter_turn:
            # Era una mossa dell'orso, ripristina il cacciatore
            self._board[target_position] = start_symbol
        else:
            # Era una mossa dei cacciatori, ripristina l'orso
            self._bear_moves -= 1
            self._bear_position = target_position
            self._board[target_position] = start_symbol
        
        self._last_move = None


# ========== FUNZIONI DI UTILITÀ PER ASSET ==========

@functools.lru_cache()
def get_img(path):
    '''
    Carica un'immagine con cache LRU per ottimizzare le prestazioni.
    Il decorator lru_cache salva le immagini in memoria per recuperi rapidi.
    '''
    return pygame.image.load(path)

@functools.lru_cache()
def get_img_alpha(path):
    '''
    Carica un'immagine con trasparenza (canale alpha) usando la cache.
    '''
    return pygame.image.load(path).convert_alpha()

def scale_img(img, scale_factor=0.833333):
    '''
    Ridimensiona un'immagine secondo un fattore di scala.
    Il fattore 0.833333 = 1280/1536 converte dalla risoluzione originale a 1280x720.
    
    Args:
        img: Immagine PyGame da scalare
        scale_factor: Fattore di scala (default 0.833333)
    Returns:
        Immagine scalata
    '''
    new_width = int(img.get_width() * scale_factor)
    new_height = int(img.get_height() * scale_factor)
    return pygame.transform.scale(img, (new_width, new_height))


# ========== CLASSE PRINCIPALE PYGAME ==========

class OrsoPyGame:
    '''
    Classe principale che gestisce l'interfaccia grafica con PyGame.
    Coordina menu, manches, HUD e input dell'utente.
    '''    
    # Create the window - sempre 1280x720
    FINESTRA_X = 1280
    FINESTRA_Y = 720
    DIM_CASELLA = 80

    def __init__(self):
        '''
        Game init
        '''
        # Logical game
        self.winner = None
        # Initialize pygame
        pygame.init()
        if IS_WEB:
            # Non può essere SCALED per webasm
            self.screen = pygame.display.set_mode((OrsoPyGame.FINESTRA_X, OrsoPyGame.FINESTRA_Y))
        else:
            # flags to manage full screen and rescaling, working for Pygame > 2.0
            display_flags = pygame.SCALED | pygame.FULLSCREEN
            self.screen = pygame.display.set_mode((OrsoPyGame.FINESTRA_X, OrsoPyGame.FINESTRA_Y), display_flags)
      
        pygame.display.set_caption("Gioco dell'orso")
        # set game clock
        self.clock = pygame.time.Clock()
        self._load_assets_menu()
        self._load_assets_game()
        # Gestione caselle: posizione e gruppo sprite - SCALATE
        self._caselle = [(608,0), (471,4), (750,4), #0,1,2
                    (608,112), (292,188), (608,188), #3,4,5
                    (929,188), (262,321), (387,321), #6,7,8
                    (471,321), (608,321), (750,321), #9,10,11
                    (829,321), (962,321), (292,471), #12,13,14
                    (608,471), (929,471), (608,546), #15,16,17
                    (471,646), (750,646), (608,667)] #18.19.20
        # Creazione gruppo caselle
        self._lista_caselle = pygame.sprite.Group()
        for i,p in enumerate(self._caselle):
            #print(i,p)
            pos = CasellaGiocoOrso(i, self)
            # Definisco rect ma non image
            pos.rect = pygame.Rect(p[0],p[1], OrsoPyGame.DIM_CASELLA, OrsoPyGame.DIM_CASELLA)
            self._lista_caselle.add(pos)

    def _load_assets_game(self) -> None:
        '''Loading game assets'''
        self.USCITA_IMG = scale_img(get_img('img/back.png'))
        self.USCITA_RECT = self.USCITA_IMG.get_rect()
        self.LABEL = scale_img(get_img('img/buttonLong.png'))
        self.USCITA_RECT.center = (1129,562)
        # Scacchiera
        self.BOARD_IMG = scale_img(get_img('img/board.png'))

    def _load_assets_menu(self) -> None:
        '''Loading menu assets'''
        # grafica titolo creata con https://textcraft.net/
        self.ORSO_IDLE_IMG = scale_img(get_img('img/little-bear-idle.png'))
        self.TRE_CACCIATORI_IMG = scale_img(get_img('img/TreCacciatoriTurno.png'))
        self.TITOLO = scale_img(get_img_alpha("img/Gioco-dellorso.png"))
        self.L_ORSO = scale_img(get_img_alpha("img/Lorso.png"))
        self.I_CACCIATORI = scale_img(get_img_alpha("img/I-cacciatori.png"))
        # Utilizzo casuale delle immagini di sfondo
        self.MENU_BACKGROUND = scale_img(get_img(f"img/3d_board.png"))
        self.PBG_LOGO = scale_img(get_img("img/pbg-small-empty.png"))

    async def menu(self) -> None:
        '''
        Display main menu with PyGame
        '''
        if MUSIC:
            pygame.mixer.music.load('sfx/intro.ogg')
            pygame.mixer.music.play(-1)

        # Elementi di sfondo - SCALATI
        self.screen.blit(self.MENU_BACKGROUND, (0, 0))
        self.screen.blit(self.PBG_LOGO, (0, 0))
        self.screen.blit(self.TITOLO, (417,17))
        self.screen.blit(self.L_ORSO, (192, 292))
        self.screen.blit(self.ORSO_IDLE_IMG, (208, 350))
        self.screen.blit(self.I_CACCIATORI, (967, 292))
        self.screen.blit(self.TRE_CACCIATORI_IMG, (1000, 350))
        
        # Creo gruppo sprite per menu
        self._menu_items = pygame.sprite.Group()
        self._m_inizio = OpzioneMenuInizioGioco(self)
        self._menu_items.add(self._m_inizio)
        self._m_uscita = OpzioneMenuUscita(self)
        self._menu_items.add(self._m_uscita)
        
        # Voci menu centrale
        # Opzione menu Player Vs AI
        self.OPZIONI_PLAYER_MODE = {
            True:"Gioca contro il computer              ",
            False:'Gioca contro un amico                 '
        }
        self._m_pl_mode = OpzioneMenuAgainstComputer(self.OPZIONI_PLAYER_MODE, True, self, (483,292))
        self._menu_items.add(self._m_pl_mode)
        
        # Opzione menu Mosse
        self.OPZIONI_PRIMA_MANCHE = {
            True:'Prima manche come orso                  ',
            False:'Prima manche come cacciatore           '
        }
        self._m_first_manche = OpzioneMenuFirstMancheAsBear(self.OPZIONI_PRIMA_MANCHE, False, self, (483,367))
        self._menu_items.add(self._m_first_manche)
        
        # Opzione disposizione iniziale
        self.OPZIONI_INIZIO = {
            True: 'Posizione iniziale classica        ',
            False:"Posizione iniziale centrale        "
            }
        self._m_pos_iniziali = OpzioneMenuInizio(self.OPZIONI_INIZIO, True, self, (483,442)) 
        self._menu_items.add(self._m_pos_iniziali)

        self._pos_call = (0, 0)
        self._running = True
        # Menu loop
        while self._running:
            self._pos_call = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    await self.quit()
                elif event.type == pygame.MOUSEBUTTONDOWN:                
                    self._pos_call = pygame.mouse.get_pos()
                    for m_item in self._menu_items:
                        if m_item.rect.collidepoint(self._pos_call):
                            await m_item.action()
            # Aggiorna gli items di menu
            self._menu_items.update()
            self._menu_items.draw(self.screen)
            # Aggiorna lo screen
            pygame.display.update()
            await asyncio.sleep(0)

    async def quit(self):
        '''Exit from game'''
        await asyncio.sleep(0.5)
        if MUSIC:
            pygame.mixer.music.fadeout(500)
            pygame.mixer.music.stop()
        pygame.quit()
        sys.exit(0)

    async def _menu_call(self):
        '''Menu call'''
        await asyncio.sleep(0.5)
        if MUSIC:
            pygame.mixer.music.fadeout(500)
        await self.menu()

    async def manche(self,
                   first_manche_as_bear: bool,
                   against_computer: bool, 
                   posizioni_iniziali_classiche: bool):
        '''Manche loop logic with PyGame'''
        if MUSIC:
            pygame.mixer.music.load('sfx/orso_music.ogg')
            pygame.mixer.music.play(-1)
        # Inizializza la scacchiera e il gioco
        self.una_manche = BearGameManche(first_manche_as_bear, against_computer, posizioni_iniziali_classiche)
        # Ruolo computer
        self._computer = None
        if against_computer:
            if first_manche_as_bear:
                self._computer = "HUNTER"
            else:
                self._computer = "BEAR"
        self._msg = "L'orso scappa facendo "+str(self.una_manche.get_max_bear_moves())+" mosse"
        # Creazione gruppo elementi di HUD
        self._hud = pygame.sprite.Group()
        self._h_turno = HudTurno(self)
        self._h_mosse = HudMosseOrso(self)
        self._h_msg = HudMessaggi(self)    
        self._hud.add(self._h_turno)
        self._hud.add(self._h_mosse)
        self._hud.add(self._h_msg)       
        # Inizializzazioni
        self._running = True
        self._pos_call = (0, 0)
        self._selezione = None
        pygame.display.update()
        await asyncio.sleep(0)        
        # Manche loop
        while self._running:
            self.clock.tick(60)
            # Disegna la scacchiera
            self.screen.blit(self.BOARD_IMG, (0, 0))
            # Pannello uscita
            self.screen.blit(self.USCITA_IMG, (1042, 483))
            # Aggiorna le caselle
            self._lista_caselle.update()
            self._lista_caselle.draw(self.screen)
            # Aggiorna HUD
            self._hud.update()
            self._hud.draw(self.screen)
            # Se è turno AI deve procedere senza verificare click utente
            if ((self.una_manche.against_computer) and 
                (not self.una_manche.is_hunter_turn()) and 
                (self._computer == "BEAR")):
                self._msg = await self.una_manche.manage_ai_smart_bear_selection()
            if ((self.una_manche.against_computer) and 
                (self.una_manche.is_hunter_turn()) and 
                (self._computer == "HUNTER"))                :
                self._msg = await self.una_manche.manage_ai_hunter_selection()                          
            pygame.display.update()
            await asyncio.sleep(0)
            # Check eventi
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    await self._menu_call()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._pos_call = pygame.mouse.get_pos()
                    # Verifica se click su freccia per uscita
                    if self.USCITA_RECT.collidepoint(self._pos_call):
                        self._running = False
                        await self._menu_call()
                    # Controlla click nelle caselle
                    for casella_cliccata in self._lista_caselle:
                        if casella_cliccata.rect.collidepoint(self._pos_call):
                            self._selezione = casella_cliccata.position
                            # Controlla e aggiorna gli spostamenti nella scacchiera
                            # Se click in posizione non corretta, ritorna solo un messaggio
                            if not self.una_manche.against_computer:
                                if (self.una_manche.is_hunter_turn()):
                                    self._msg = self.una_manche.manage_hunter_selection(self._selezione)
                                else:
                                    self._msg = self.una_manche.manage_bear_selection(self._selezione)
                            elif ((self.una_manche.against_computer) and 
                                  (self.una_manche.is_hunter_turn()) and 
                                  (self._computer == "BEAR")
                                  ):
                                    self._msg = self.una_manche.manage_hunter_selection(self._selezione)
                            elif ((not self.una_manche.is_hunter_turn()) and 
                                  (self.una_manche.against_computer) and 
                                  (self._computer == "HUNTER")):                                    
                                    self._msg = self.una_manche.manage_bear_selection(self._selezione)            
                            pygame.display.update()
                            await asyncio.sleep(0)
            # Aggiornamento screen
            # Aggiorna le caselle
            self._lista_caselle.update()
            self._lista_caselle.draw(self.screen)
            # Aggiorna HUD
            self._hud.update()
            self._hud.draw(self.screen)
            # Check fine della manche
            if self.una_manche.game_over():
                if MUSIC:
                    pygame.mixer.music.pause()
                self._msg = "Fine manche"
                self.screen.blit(self.LABEL, (483, 317))
                self.LOBSTER_25 = pygame.font.Font('LobsterTwo-Regular.otf',21)
                text = ""
                if self.una_manche.is_bear_winner():
                    try:
                        #Non funziona con webasm
                        if MUSIC:
                            pygame.mixer.Channel(1).play(pygame.mixer.Sound('sfx/orso_ride.ogg'))
                    except:
                        pass
                    text = self.LOBSTER_25.render(f"   L'orso raggiunge {self.una_manche.get_max_bear_moves()} mosse e scappa!", 1, BLACK)
                else:
                    try:
                        #Non funziona con webasm
                        if MUSIC:
                            pygame.mixer.Channel(1).play(pygame.mixer.Sound('sfx/success.ogg')) 
                    except:
                        pass
                    text = self.LOBSTER_25.render(f"  I cacciatori lasciano all'orso {self.una_manche.get_bear_moves()} mosse", 1, BLACK)
                self.screen.blit(text, (492,333))
                pygame.display.update()
                await asyncio.sleep(5)                    
                return self.una_manche.get_bear_moves()
            pygame.display.update()
            await asyncio.sleep(0)
                

    async def game(self,
                   first_manche_as_bear: bool,
                   against_computer: bool, 
                   posizioni_iniziali_classiche: bool):
        '''Game logic with double manche'''
        self.player_A = GamePlayer("      Tu       ", True, not first_manche_as_bear)
        self.player_B = GamePlayer("    Amico    ", against_computer, first_manche_as_bear)
        if against_computer:
            self.player_B.name = " Computer "
        if first_manche_as_bear:
            self.player_B.is_hunter = True
            self.player_A.is_hunter = False
        else:            
            self.player_B.is_hunter = False
            self.player_A.is_hunter = True
        # Inizializzazioni
        self._running = True
        self._pos_call = (0, 0)
        # Game loop
        # Disegna la scacchiera
        self.screen.blit(self.BOARD_IMG, (0, 0))
        self.screen.blit(self.PBG_LOGO, (0, 0))
        # HUD situazione turni e punteggi
        self._hud = pygame.sprite.Group()
        self._h_msg = HudGioco(self.screen, "      Prima manche      ")
        self._h_m_pA = HudTurnoMancheGiocatore(417,250,self.screen, self.player_A)
        self._h_t_pA = HudMosseOrsoMancheGiocatore(417,417,self.screen, self.player_A)
        self._h_m_pB = HudTurnoMancheGiocatore(708,250,self.screen, self.player_B)        
        self._h_t_pB = HudMosseOrsoMancheGiocatore(708,417,self.screen, self.player_B)       
        self._hud.add(self._h_msg)
        self._hud.add(self._h_t_pA)
        self._hud.add(self._h_t_pB)
        self._hud.add(self._h_m_pA)
        self._hud.add(self._h_m_pB)
        self.clock.tick(60)
        # Aggiorna pannello messaggi
        self._hud.update()
        self._hud.draw(self.screen)
        pygame.display.update()
        await asyncio.sleep(5)            
        # Logica due manches
        bear_moves = await self.manche(
                first_manche_as_bear,
                against_computer, 
                posizioni_iniziali_classiche)
        if first_manche_as_bear:
            self.player_A.bear_moves = bear_moves
        else:
            self.player_B.bear_moves = bear_moves
        self.player_B.is_hunter = not self.player_B.is_hunter
        self.player_A.is_hunter = not self.player_A.is_hunter
        # Disegna la scacchiera
        self.screen.blit(self.BOARD_IMG, (0, 0))
        self.screen.blit(self.PBG_LOGO, (0, 0))
        # HUD situazione turni e punteggi
        self._hud = pygame.sprite.Group()
        self._h_msg = HudGioco(self.screen, "    Seconda manche    ")
        self._h_m_pA = HudTurnoMancheGiocatore(417,250,self.screen, self.player_A)
        self._h_t_pA = HudMosseOrsoMancheGiocatore(417,417,self.screen, self.player_A)
        self._h_m_pB = HudTurnoMancheGiocatore(708,250,self.screen, self.player_B)        
        self._h_t_pB = HudMosseOrsoMancheGiocatore(708,417,self.screen, self.player_B)       
        self._hud.add(self._h_msg)
        self._hud.add(self._h_t_pA)
        self._hud.add(self._h_t_pB)
        self._hud.add(self._h_m_pA)
        self._hud.add(self._h_m_pB)
        # Aggiorna pannello messaggi
        self._hud.update()
        self._hud.draw(self.screen)
        pygame.display.update()
        await asyncio.sleep(5)
        bear_moves = await self.manche(
                not first_manche_as_bear,
                against_computer, 
                posizioni_iniziali_classiche)            
        if not first_manche_as_bear:
            self.player_A.bear_moves = bear_moves
        else:
            self.player_B.bear_moves = bear_moves
        if self.player_A.bear_moves > self.player_B.bear_moves:
            self.winner = "  Bravo! Hai vinto!  "
        elif self.player_B.bear_moves > self.player_A.bear_moves:
            self.winner = " Hai perso... Riprova "
        else:
            self.winner = "E' un pareggio! Bravi!"
        self.screen.blit(self.BOARD_IMG, (0, 0))
        self.screen.blit(self.PBG_LOGO, (0, 0))
        self._hud = pygame.sprite.Group()
        self._h_msg = HudGioco(self.screen, "Fine seconda manche")
        self._h_m_pA = HudTurnoMancheGiocatore(417,250,self.screen, self.player_A)
        self._h_t_pA = HudMosseOrsoMancheGiocatore(417,417,self.screen, self.player_A)
        self._h_m_pB = HudTurnoMancheGiocatore(708,250,self.screen, self.player_B)        
        self._h_t_pB = HudMosseOrsoMancheGiocatore(708,417,self.screen, self.player_B)       
        self._hud.add(self._h_msg)
        self._hud.add(self._h_t_pA)
        self._hud.add(self._h_t_pB)
        self._hud.add(self._h_m_pA)
        self._hud.add(self._h_m_pB)
        self._h_msg.msg = self.winner
        # Aggiorna pannello messaggi
        self._hud.update()
        self._hud.draw(self.screen)         
        pygame.display.update()
        await asyncio.sleep(8)
        await self.menu()


# Classi opzioni di menu
class OpzioneMenu(pygame.sprite.Sprite):
    '''
    Generic class for menu options; it requires
    - opzioni come dizionario valore:voce da visualizzare
    - valore iniziale di default
    - gioco orso
    - posizione del pannello di sfondo
    '''
    PANNELLO_UNO_IMG = scale_img(get_img('img/buttonLong.png')) #panel
    def __init__(self, opzioni: dict, default_value: object, game: OrsoPyGame, position: tuple):
        super().__init__()
        self.game = game
        self.LOBSTER_30 = pygame.font.Font('LobsterTwo-Regular.otf',25)
        # Iniziano i cacciatori è il default
        self.value = default_value
        self.opzioni = opzioni
        self.position = position
        self._text = self.LOBSTER_30.render(
            self.opzioni[self.value], 
            1, 
            BLACK)
        self.rect = self._text.get_rect()
        self.rect.x = self.position[0]+20
        self.rect.y = self.position[1]+25
        self.image = self._text

    def update(self):
        self.game.screen.blit(OpzioneMenu.PANNELLO_UNO_IMG, self.position)
        self._text = self.LOBSTER_30.render(
            self.opzioni[self.value], 
            1, 
            BLACK)
        self.rect = self._text.get_rect()
        self.rect.x = self.position[0]+20
        self.rect.y = self.position[1]+25        
        self.image = self._text

    def action(self):
        raise NotImplementedError("Action must be implemented by child class")


class OpzioneMenuInizio(OpzioneMenu):
    async def action(self):
        self.value = not(self.value)


class OpzioneMenuAgainstComputer(OpzioneMenu):
    async def action(self):
        self.value = not(self.value)


class OpzioneMenuFirstMancheAsBear(OpzioneMenu):
    async def action(self):
        self.value = not(self.value)        

class OpzioneMenuPlayerType(OpzioneMenu):
    async def action(self):
        self.value += 10
        if self.value == 40:
            self.value = 10


class OpzioneMenuNumeroMosse(OpzioneMenu):
    async def action(self):
        self.value += 10
        if self.value == 50:
            self.value = 20


class OpzioneMenuUscita(pygame.sprite.Sprite):
    '''Menu: uscita'''
    def __init__(self, game: OrsoPyGame):
        super().__init__()
        self.game = game
        self.ESCI_GIOCO = scale_img(get_img('img/buttonLong.png'))
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',37)
        self._esci_str = self.LOBSTER_45.render("Esci dal gioco", 1, BLACK)
        self.rect = self._esci_str.get_rect()
        self.rect.x = 142
        self.rect.y = 575

    def update(self):
        self.game.screen.blit(self.ESCI_GIOCO, (83, 567))
        self.image = self._esci_str

    async def action(self):
        self.game._running = False
        await self.game.quit()
    

class OpzioneMenuInizioGioco(pygame.sprite.Sprite):
    '''Menu: inizio'''
    def __init__(self, game: OrsoPyGame):
        super().__init__()
        self.game = game
        self.INIZIA = scale_img(get_img('img/buttonLong.png'))
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',37)
        self._inizia_str = self.LOBSTER_45.render("  Inizia a giocare", 1, BLACK)
        self.rect = self._inizia_str.get_rect()
        self.rect.x = 950
        self.rect.y = 575


    def update(self):
        self.game.screen.blit(self.INIZIA, (917, 567))
        self.image = self._inizia_str

    async def action(self):
        self.game._running = False
        await asyncio.sleep(0.8)
        # fade out menu music
        if MUSIC:
            pygame.mixer.music.fadeout(800)
        # Richiamo del gioco con i parametri scelti
        await self.game.game(
            self.game._m_first_manche.value, #Human orso nella prima manche
            self.game._m_pl_mode.value, #Contro computer
            self.game._m_pos_iniziali.value #Disposizione iniziale classica
        )
  

# Classi HUD di gioco
class HudTurno(pygame.sprite.Sprite):
    '''HUD: pannello per il turno'''
    ORSO_IDLE_IMG = scale_img(get_img('img/little-bear-idle.png'))
    TRE_CACCIATORI_IMG = scale_img(get_img('img/TreCacciatoriTurno.png'))
    
    PANNELLO_DUE_IMG = scale_img(get_img('img/panel.png')) #panel_due
 
    def __init__(self, game: OrsoPyGame):
        super().__init__()
        self.game = game
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',37)
        self._turno_str = self.LOBSTER_45.render("Turno", 1, BLACK)

    def update(self): 
        # Inizializzazione Pannello turno, parte fissa
        self.game.screen.blit(HudTurno.PANNELLO_DUE_IMG, (1042, 67))        
        self.game.screen.blit(self._turno_str, (1083, 75))          
        if self.game.una_manche._is_hunter_turn:
            self.rect = HudTurno.TRE_CACCIATORI_IMG.get_rect()
            self.rect.x = 1054
            self.rect.y = 133
            self.image = HudTurno.TRE_CACCIATORI_IMG
        else:
            self.rect = HudTurno.ORSO_IDLE_IMG.get_rect()
            self.rect.x = 1100
            self.rect.y = 133
            self.image = HudTurno.ORSO_IDLE_IMG



class HudMosseOrso(pygame.sprite.Sprite):
    '''HUD: pannello per il contatore mosse orso'''
    PANNELLO_DUE_IMG = scale_img(get_img('img/panel.png')) #panel_due

    def __init__(self, game: OrsoPyGame):
        super().__init__()
        self.game = game
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',37)
        self.LOBSTER_90 = pygame.font.Font('LobsterTwo-Regular.otf',75)
        # Pannello mosse orso
        self._mosse_str = self.LOBSTER_45.render("Mosse orso", 1, BLACK)     
            
    def update(self):
        self._mosse = self.LOBSTER_90.render(str(self.game.una_manche.get_bear_moves()), 1, BLACK)       
        self.game.screen.blit(HudMosseOrso.PANNELLO_DUE_IMG, (67, 67))  
        self.game.screen.blit(self._mosse_str, (75, 75))  
        self.rect = self._mosse.get_rect()
        self.rect.x = 121
        self.rect.y = 117
        self.image = self._mosse



#########################################
class HudTurnoMancheGiocatore(pygame.sprite.Sprite):
    '''HUD: pannello per il turno del giocatore'''
    ORSO_IMG = scale_img(get_img('img/little-bear-sel.png'))
    TRE_CACCIATORI_IMG = scale_img(get_img('img/TreCacciatoriTurno.png'))
    
    PANNELLO_DUE_IMG = scale_img(get_img('img/panel.png')) #panel_due
 
    def __init__(self, x, y, screen, giocatore: GamePlayer):
        super().__init__()
        self.x = x
        self.y = y
        self.screen = screen
        self.giocatore = giocatore
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',37)

        self._turno_str = self.LOBSTER_45.render(f"{self.giocatore.name}", 1, BLACK)

    def update(self): 
        # Inizializzazione Pannello turno, parte fissa
        self.screen.blit(HudTurnoMancheGiocatore.PANNELLO_DUE_IMG, (self.x, self.y))        
        self.screen.blit(self._turno_str, (self.x + 10, self.y + 10))          
        if self.giocatore.is_hunter:
            self.rect = HudTurnoMancheGiocatore.TRE_CACCIATORI_IMG.get_rect()
            self.rect.x = self.x + 15
            self.rect.y = self.y + 80
            self.image = HudTurnoMancheGiocatore.TRE_CACCIATORI_IMG
        else:
            self.rect = HudTurnoMancheGiocatore.ORSO_IMG.get_rect()
            self.rect.x = self.x + 70
            self.rect.y = self.y + 80
            self.image = HudTurnoMancheGiocatore.ORSO_IMG

class HudMosseOrsoMancheGiocatore(pygame.sprite.Sprite):
    '''HUD: pannello per il numero mosse orso del giocatore'''
    PANNELLO_DUE_IMG = scale_img(get_img('img/panel.png')) #panel_due

    def __init__(self, x, y, screen, giocatore: GamePlayer):
        super().__init__()
        self.x = x
        self.y = y
        self.screen = screen
        self.giocatore = giocatore        
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',37)
        self.LOBSTER_90 = pygame.font.Font('LobsterTwo-Regular.otf',75)
        # Pannello mosse orso
        self._mosse_str = self.LOBSTER_45.render("Mosse orso", 1, BLACK)     
            
    def update(self):
        # Se non ha ancora giocato come orso
        mosse = " - "
        colore = BLACK
        if self.giocatore.bear_moves > 0:
            mosse = str(self.giocatore.bear_moves)
            colore = RED
        self._mosse = self.LOBSTER_90.render(mosse, 1, colore)
        self.screen.blit(HudMosseOrsoMancheGiocatore.PANNELLO_DUE_IMG, (self.x, self.y))  
        self.screen.blit(self._mosse_str, (self.x + 10, self.y + 10))  
        self.rect = self._mosse.get_rect()
        self.rect.x = self.x + 65
        self.rect.y = self.y + 60
        self.image = self._mosse
 

class HudGioco(pygame.sprite.Sprite):
    '''HUD: pannello per i messaggi'''    
    PANNELLO_UNO_IMG = scale_img(get_img('img/buttonLong.png')) #panel

    def __init__(self, screen, msg):
        super().__init__()
        self.screen = screen
        self.msg = msg
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',37)

    def update(self):
        self._text = self.LOBSTER_45.render(self.msg, 1, BLACK)
        self.screen.blit(HudGioco.PANNELLO_UNO_IMG, (483,125))
        self.rect = self._text.get_rect()
        self.rect.x = 492
        self.rect.y = 133
        self.image = self._text

#########################################
class HudMessaggi(pygame.sprite.Sprite):
    '''HUD: pannello per i messaggi'''    
    PANNELLO_UNO_IMG = scale_img(get_img('img/buttonLong.png')) #panel

    def __init__(self, game: OrsoPyGame):
        super().__init__()
        self.game = game
        self.LOBSTER_30 = pygame.font.Font('LobsterTwo-Regular.otf',25)

    def update(self):
        self._text = self.LOBSTER_30.render(self.game._msg, 1, BLACK)
        self.game.screen.blit(self.PANNELLO_UNO_IMG, (33, 567))
        self.rect = self._text.get_rect()
        self.rect.x = 42
        self.rect.y = 587
        self.image = self._text


class CasellaGiocoOrso(pygame.sprite.Sprite):
    '''
    Oggetto casella del gioco
    Gestisce la visualizzazione di personaggi e orme
    '''
    # Static resources
    TRASPARENTE = pygame.Surface((80,80), pygame.SRCALPHA)

    ORSO_IMG = scale_img(get_img('img/little-bear.png'))
    ORSO_IDLE_IMG = scale_img(get_img('img/little-bear-idle.png'))
    ORSO_SEL_IMG = scale_img(get_img('img/little-bear-sel.png'))

    CACCIATORE_UNO_IMG = scale_img(get_img('img/little-hunter1.png'))
    CACCIATORE_UNO_IDLE_IMG = scale_img(get_img('img/little-hunter1-idle.png'))
    CACCIATORE_UNO_SEL_IMG = scale_img(get_img('img/little-hunter1-sel.png'))

    CACCIATORE_DUE_IMG = scale_img(get_img('img/little-hunter2.png'))
    CACCIATORE_DUE_IDLE_IMG = scale_img(get_img('img/little-hunter2-idle.png'))
    CACCIATORE_DUE_SEL_IMG = scale_img(get_img('img/little-hunter2-sel.png'))

    CACCIATORE_TRE_IMG = scale_img(get_img('img/little-hunter3.png'))
    CACCIATORE_TRE_IDLE_IMG = scale_img(get_img('img/little-hunter3-idle.png'))
    CACCIATORE_TRE_SEL_IMG = scale_img(get_img('img/little-hunter3-sel.png'))
        
    # Orme
    ORMA_ORSO_IMG = scale_img(get_img('img/impronta_orso.png'))
    ORMA_CACCIATORE_IMG = scale_img(get_img('img/impronta_cacciatore.png'))

    def __init__(self, position: int, game: OrsoPyGame):
        super().__init__()
        self.position = position
        self.game = game

    def update(self):
        '''Valorizza l'attributo image dello sprite'''
        # Disegna la pedine ottenendo la board dall'oggetto gioco
        bb = self.game.una_manche
        if bb.get_board_position(self.position) == BOARD_EMPTY:
            # Controllo se è orma
            is_orma, tipo_orma  = bb.is_footprint_and_type(self.position)            
            if is_orma:
                if tipo_orma == 'HUNTER':
                    self.image = CasellaGiocoOrso.ORMA_CACCIATORE_IMG
                else:
                    self.image = CasellaGiocoOrso.ORMA_ORSO_IMG                    
            else:
                self.image = CasellaGiocoOrso.TRASPARENTE
        # Verifica se è orso
        elif bb.get_board_position(self.position) == BOARD_BEAR:            
            if not bb.is_hunter_turn():
                self.image = CasellaGiocoOrso.ORSO_SEL_IMG
            else:
                self.image = CasellaGiocoOrso.ORSO_IMG
        # Verifica se è uno dei cacciatori
        elif bb.get_board_position(self.position) == BOARD_HUNTER_1:
            if (bb.get_hunter_starting_pos() == self.position):
                self.image = CasellaGiocoOrso.CACCIATORE_UNO_SEL_IMG
            else:
                if bb.is_hunter_turn():
                    self.image = CasellaGiocoOrso.CACCIATORE_UNO_IMG
                else:
                    self.image = CasellaGiocoOrso.CACCIATORE_UNO_IDLE_IMG
        elif bb.get_board_position(self.position) == BOARD_HUNTER_2:
            if (bb.get_hunter_starting_pos() == self.position):
                self.image = CasellaGiocoOrso.CACCIATORE_DUE_SEL_IMG
            else:
                if bb.is_hunter_turn():
                    self.image = CasellaGiocoOrso.CACCIATORE_DUE_IMG
                else:
                    self.image = CasellaGiocoOrso.CACCIATORE_DUE_IDLE_IMG
        elif bb.get_board_position(self.position) == BOARD_HUNTER_3:
            if (bb.get_hunter_starting_pos() == self.position):
                self.image = CasellaGiocoOrso.CACCIATORE_TRE_SEL_IMG
            else:
                if bb.is_hunter_turn():
                    self.image = CasellaGiocoOrso.CACCIATORE_TRE_IMG
                else:
                    self.image = CasellaGiocoOrso.CACCIATORE_TRE_IDLE_IMG


class Player:
    def __init__(self, name):
        self.name = name
        self.states_value = {}  # state -> value

    def get_action(self, actions, current_board: BearGameManche) -> tuple[int, int]:
        '''Return the action to take as tuple (startpos, endpos)
        Now the ai player can choose randomically from all best moves
        '''
        value_max = -INFINITY
        best_actions = []
        for act in actions:
            current_board.move_player(act[0], act[1])
            state_value = self.states_value.get(current_board.get_hash())
            if (state_value is None):
                value = 0
            else:
                value = state_value

            if value > value_max:
                value_max = value
                best_actions = [act]
            elif value == value_max:
                best_actions.append(act)                

            current_board.undo_move()
        return random.choice(best_actions)

    def print_value(self, board) -> None:
        print(
            f"{self.name}: {board.get_hash()} -> "
            f"{self.states_value.get(board.get_hash())}"
        )

    def load_policy(self, file) -> None:
        '''Load file with policy for reinforcement learning'''
        with open(file, 'rb') as file_read:
            data = pickle.load(file_read)
        # Policies are in states_value key
        self.states_value = (
            data if 'states_value' not in data else  # data legacy support
            data['states_value']
        )


async def main():
    '''
    La trasformazione in async è stata necessaria per la pubblicazione come WebApp
    Il gioco è richiamato da menu
    '''
    opg = OrsoPyGame()
    await opg.menu()
    await opg.quit()

asyncio.run(main())