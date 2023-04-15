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
'''

from __future__ import annotations
import asyncio
from json.encoder import INFINITY
import os
import pygame
import time
import sys
import functools
import random
import pickle

# Palette - RGB colors
BLACK = (0, 0, 0)
RED = (255, 0, 0)

# Symbols for the board of game
BOARD_HUNTER_1 = '1'
BOARD_HUNTER_2 = '8'
BOARD_HUNTER_3 = '9'
BOARD_BEAR = '2'
BOARD_EMPTY = '_'
# Symbols for the board of policy
# Unlink dependency logic between board game and board policy
BOARD_HUNTER_POLICY = '1'
MUSIC = True

class GamePlayer:
    '''
    Giocatore delle due manches
    '''
    def __init__(self, name, is_human, is_hunter) -> None:
        self.name = name
        self.is_human = is_human
        self.bear_moves = 0
        self.is_hunter = is_hunter

class BearGameManche:
    '''
    PyGame-independent manche-game class
    Class for logical board and game model
    21 positions:
    _ means empty;
    1-8-9 means hunters; 
    2 means bear;
    '''
    # Settings
    BOARD_POSITIONS = 21
    # Eventually change for testing
    MAX_BEAR_MOVES = 40
    HUNTER_STARTS = False
    # Adjacent positions in the board, list index is the board  position
    ADJACENT_POSITIONS = [[1,2,3], #0
                          [0,3,4],
                          [0,3,6], #2
                          [0,1,2,5],
                          [1,7,8], #4
                          [3,9,10,11],
                          [2,12,13], #6
                          [4,8,14],
                          [7,4,14,9], #8
                          [8, 10,5,15],
                          [5,9,11,15],#10
                          [5,10,15,12],
                          [11,6,16,13],#12
                          [6,12,16],
                          [7,8,18],#14
                          [9,10,11,17],
                          [12,13,19], #16
                          [15,18,19,20],
                          [14,17,20], #18
                          [16, 17, 20],
                          [18, 17, 19]]

    def __init__(self, 
                 first_manche_as_bear:bool,
                 against_computer: bool, 
                 classic_initial_position: bool):
        '''
        Load policies for AI
        '''
        # Temporary folder for PyInstaller
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        # Start settings
        self.reset(against_computer, classic_initial_position)
        self.first_manche_as_bear = first_manche_as_bear
        # Reinforcement learning loading for Bear AI
        self._bear_player = Player("orso")
        self._bear_player.load_policy(
            os.path.join(base_path, "bear.policy")
        )

        # Deterministic distance based state-value function for Hunter AI
        self._hunter_player = Player("cacciatore")
        self._hunter_player.load_policy(
            os.path.join(base_path, "hunter.policy")
        )
        
    def reset(self, against_computer: bool, classic_initial_position: bool) -> None:
        '''
        Initial positions and settings
        '''
        # Start and reset settings
        if classic_initial_position:
            self._board = [BOARD_HUNTER_1, BOARD_HUNTER_2, BOARD_HUNTER_3, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY,
                        BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY,
                        BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_BEAR]
            self._bear_position = 20            
        else:
            # Quick start - Iacazio's start
            self._board = [BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_HUNTER_1, BOARD_EMPTY,
                        BOARD_EMPTY, BOARD_EMPTY, BOARD_HUNTER_2, BOARD_BEAR, BOARD_HUNTER_3, BOARD_EMPTY, BOARD_EMPTY,
                        BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY, BOARD_EMPTY]
            self._bear_position = 10            
        
        self._bear_moves = 0
        self._hunter_starting_pos = -1
        # _hunter_ai_final usato solo per hunter AI
        self._hunter_ai_final = -1
        # From external configuration
        self._is_hunter_turn = self.HUNTER_STARTS
        self.against_computer = against_computer
        self._winner = None
        self._last_move = None


    def get_bear_moves(self) -> int:
        '''
        Counter of bear moves
        '''
        return self._bear_moves


    def get_max_bear_moves(self) -> int:
        '''
        Max bear moves
        '''
        return self.MAX_BEAR_MOVES

    def get_board_position(self, position:int) -> str:
        '''
        Return the pown of the input position
        '''
        return self._board[position]

    def get_hunter_starting_pos(self) -> int:
        '''
        Return the hunter starting position
        '''
        return self._hunter_starting_pos
    
    def is_bear_winner(self) -> bool:
        '''Returns the winner in a string type for display purposes'''
        if not(self.get_possible_moves(self._bear_position)):
            return False
        if (self._bear_moves >= self.MAX_BEAR_MOVES):
            return True

    def game_over(self) -> bool:
        '''Check for game over'''
        if not(self.get_possible_moves(self._bear_position)):
            self._winner = f"I cacciatori vincono; l'orso ha fatto {self.get_bear_moves()} mosse"
            return True
        elif (self._bear_moves >= self.MAX_BEAR_MOVES):
            self._winner = f"L'orso è scappato; ha fatto {self.get_bear_moves()} mosse"
            return True
        else:
            return False

    def is_hunter(self, selection:str) -> bool:
        '''Check if selection is an hunter'''
        return selection in [BOARD_HUNTER_1, BOARD_HUNTER_2, BOARD_HUNTER_3]

    def is_hunter_turn(self) -> bool:
        '''Check if is it the hunter turn'''
        return self._is_hunter_turn

    def manage_hunter_selection(self, sel:int) -> str:
        '''Input selection from user; return user message to display'''
        selected_hunter = ''
        # Pick up pawn (starting pos -1)
        if self._hunter_starting_pos == -1:
            if (not(self.is_hunter(self._board[sel]))):
                return "Seleziona un cacciatore!"
            else:
                self._hunter_starting_pos = sel
                return "Cacciatore, fa' la tua mossa!"
        else: # Finding final position for hunter
            if sel in self.get_possible_moves(self._hunter_starting_pos):
                selected_hunter = self._board[self._hunter_starting_pos]
                self._board[self._hunter_starting_pos] = BOARD_EMPTY
                self._board[sel] = selected_hunter
                self._hunter_starting_pos = -1
                self._is_hunter_turn = not(self._is_hunter_turn)
                return "Orso, scegli la tua mossa!"
            else: # Go back to picking stage
                self._hunter_starting_pos = -1
                return "Posizione non valida!"
    
    def manage_ai_hunter_selection(self) -> str:
        '''
        Use precalculated policy to select the best move for the hunter
        '''
        # Simulation of human behavior: first select, than move
        if (self._hunter_starting_pos == -1):
            hunter_positions = []
            for x in range(self.BOARD_POSITIONS):
                if self._board[x] == BOARD_HUNTER_1 or self._board[x] == BOARD_HUNTER_2 or self._board[x] == BOARD_HUNTER_3:
                    hunter_positions.append(x)

            hunter_actions = []
            for x in hunter_positions:
                moves = self.get_possible_moves(x)
                for move in moves:
                    hunter_actions.append((x, move))                    

            action = self._hunter_player.get_action(hunter_actions, self)
            self._hunter_starting_pos = action[0]
            self._hunter_ai_final = action[1]
            return "Cacciatore selezionato"
        else:
            self._board[self._hunter_ai_final] = self._board[self._hunter_starting_pos]            
            self._board[self._hunter_starting_pos] = BOARD_EMPTY
            self._hunter_starting_pos = -1
            self._hunter_ai_final = -1
            self._is_hunter_turn = not self._is_hunter_turn
            # Attesa simulazione "pensiero"
            time.sleep(1)
            return "Orso, scegli la tua mossa!"

    def get_bear_actions(self) -> list[(int, int)]:
        '''
        Return a list of tuples with starting pos and next possible move
        '''
        actions = []
        for adj in BearGameManche.ADJACENT_POSITIONS[self._bear_position]:
            if self._board[adj] == BOARD_EMPTY:
                actions.append((self._bear_position, adj))
        return actions

    def move_bear(self, new_position: int) -> None:
        '''
        Used by move_player for get_actions
        Move bear to a random position
        '''
        self._last_move = (self._bear_position, new_position)
        if new_position in self.get_possible_moves(self._bear_position):
            self._board[self._bear_position] = BOARD_EMPTY
            self._board[new_position] = BOARD_BEAR
            self._bear_position = new_position
            self._bear_moves += 1
            self._is_hunter_turn = not self._is_hunter_turn
        else:
            print(self._last_move)
            raise ValueError("Orso non può muoversi qui!")

    def move_hunter(self, start_position: int, end_position: int) -> None:
        '''
        Used by move_player for get_actions
        '''
        self._last_move = (start_position, end_position)
        start_symbol = self._board[start_position]
        self._board[start_position] = BOARD_EMPTY
        self._board[end_position] = start_symbol
        self._is_hunter_turn = not self._is_hunter_turn

    def get_hash(self) -> str:
        '''
        Return a hash of the board
        '''
        board = self._board.copy()
        # normalize the hunter ids for the Reinforcement model
        # unlink dependency logic between board game and board policy
        for i in range(len(board)):
            if board[i] == BOARD_HUNTER_3 or board[i] == BOARD_HUNTER_2 or board[i] == BOARD_HUNTER_1:
                board[i] = BOARD_HUNTER_POLICY
        return ''.join(board)

    def undo_move(self) -> None:
        '''Undo the move'''
        self._is_hunter_turn = not self._is_hunter_turn
        target_position, starting_position = self._last_move  # contrario!
        start_symbol = self._board[starting_position] # prendi il simbolo alla vecchia posizione
        self._board[starting_position] = BOARD_EMPTY
        if self._is_hunter_turn:
            self._board[target_position] = start_symbol
        else:
            self._bear_moves -= 1
            self._bear_position = target_position
            self._board[target_position] = start_symbol
        self._last_move = None

    def move_player(self, start_pos, end_pos) -> str:
        '''
        Move player to start position to end position
        '''
        if self._is_hunter_turn:
            return self.move_hunter(start_pos, end_pos)
        else:
            return self.move_bear(end_pos)

    def manage_ai_smart_bear_selection(self) -> str:
        '''
        Implement AI logic
        '''
        # Attesa simulazione "pensiero"
        time.sleep(1)
        bear_actions = self.get_bear_actions()
        action = self._bear_player.get_action(bear_actions, self)
        self.move_bear(action[1])
        return "L'orso intelligente ha mosso!"
    
    def manage_bear_selection(self,sel: int) -> str:
        '''Input selection from user; return user message to display'''
        if sel in self.get_possible_moves(self._bear_position):
            # Bear makes the move
            self._board[self._bear_position] = BOARD_EMPTY
            self._board[sel] = BOARD_BEAR
            self._bear_moves += 1
            self._bear_position = sel
            self._is_hunter_turn = not(self._is_hunter_turn)
            return "Seleziona uno dei cacciatori!"
        else:
            return "Posizione non valida..."
    
    def is_footprint_and_type(self, sel:int) -> tuple[bool, str]:
        '''
        Return a tuple:
        - if is a footprint
        - footprint type (HUNTER|BEAR), None if is not a footprint
        '''
        if self._is_hunter_turn:
            if self._hunter_starting_pos == -1:
                return (False, None)
            else:
                if sel in self.get_possible_moves(self._hunter_starting_pos):
                    return (True, "HUNTER")
                else:
                    return (False, None)
        else:
            if sel in self.get_possible_moves(self._bear_position):
                return (True, "BEAR")
            else:
                return (False, None)

    def get_possible_moves(self, position: int) -> list[int]:
        '''
        Returns the list with possible free positions
        '''
        moves = []
        #Check free positions
        for x in BearGameManche.ADJACENT_POSITIONS[position]:
            if self._board[x] == BOARD_EMPTY:
                moves.append(x)
        return moves

@functools.lru_cache()
def get_img(path):
    '''
    To optimize assets loading
    "lru_cache" decorator saves recent images into memory for fast retrieval
    '''
    return pygame.image.load(path)

@functools.lru_cache()
def get_img_alpha(path):
    '''
    To optimize assets loading for alpha images
    "lru_cache" decorator saves recent images into memory for fast retrieval
    '''
    return pygame.image.load(path).convert_alpha()

class OrsoPyGame:
    '''
    PyGame specific implementation for the game
    '''
    # Create the window
    FINESTRA_X=1536
    FINESTRA_Y=864
    DIM_CASELLA = 80

    def __init__(self):
        '''
        Game init
        '''
        # Logical game
        self.winner = None
        # Initialize pygame
        pygame.init()
        # flags to manage full screen and rescaling, working for Pygame > 2.0
        display_flags = pygame.SCALED | pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((OrsoPyGame.FINESTRA_X, OrsoPyGame.FINESTRA_Y), display_flags)
        pygame.display.set_caption("Gioco dell'orso")
        # set game clock
        self.clock = pygame.time.Clock()
        self._load_assets_menu()
        self._load_assets_game()
        # Gestione caselle: posizione e gruppo sprite
        self._caselle = [(730,0), (565,5), (900,5), #0,1,2
                    (730,135), (350,225), (730,225), #3,4,5
                    (1115,225), (315,385), (465,385), #6,7,8
                    (565,385), (730,385), (900,385), #9,10,11
                    (995,385), (1155,385), (350,565), #12,13,14
                    (730,565), (1115,565), (730,655), #15,16,17
                    (565,775), (900,775), (730,800)] #18.19.20
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
        self.USCITA_IMG = get_img('img/back.png')
        self.USCITA_RECT = self.USCITA_IMG.get_rect()
        self.LABEL = get_img('img/buttonLong.png')
        self.USCITA_RECT.center = (1355,675)
        # Scacchiera
        self.BOARD_IMG = get_img('img/board.png')

    def _load_assets_menu(self) -> None:
        '''Loading menu assets'''
        # grafica titolo creata con https://textcraft.net/
        self.ORSO_IDLE_IMG = get_img('img/little-bear-idle.png')
        self.TRE_CACCIATORI_IMG = get_img('img/TreCacciatoriTurno.png')
        self.TITOLO = get_img_alpha("img/Gioco-dellorso.png")
        self.MENU_BACKGROUND = get_img("img/3d_board.png")
        self.PBG_LOGO = get_img("img/pbg-small-empty.png")

    async def menu(self) -> None:
        '''
        Display main menu with PyGame
        '''
        if MUSIC:
            pygame.mixer.music.load('sfx/intro.ogg')
            pygame.mixer.music.play(-1)

        # Elementi di sfondo
        self.screen.blit(self.MENU_BACKGROUND, (0, 0))
        self.screen.blit(self.PBG_LOGO, (0, 0))
        self.screen.blit(self.TITOLO, (500,20))
        self.screen.blit(self.ORSO_IDLE_IMG, (250, 420))
        self.screen.blit(self.TRE_CACCIATORI_IMG, (1200, 420))
        
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
        self._m_pl_mode = OpzioneMenuAgainstComputer(self.OPZIONI_PLAYER_MODE, True, self, (580,350)) #305
        self._menu_items.add(self._m_pl_mode)
        
        # Opzione menu Mosse
        self.OPZIONI_PRIMA_MANCHE = {
            True:'Prima manche come orso                  ',
            False:'Prima manche come cacciatore           '
        }
        self._m_first_manche = OpzioneMenuFirstMancheAsBear(self.OPZIONI_PRIMA_MANCHE, False, self, (580,440))
        self._menu_items.add(self._m_first_manche)
        
        # Opzione disposizione iniziale
        self.OPZIONI_INIZIO = {
            True: 'Posizione iniziale classica        ',
            False:"Posizione iniziale centrale        "
            }
        self._m_pos_iniziali = OpzioneMenuInizio(self.OPZIONI_INIZIO, True, self, (580,530)) 
        self._menu_items.add(self._m_pos_iniziali)

        self._pos_call = (0, 0)
        self._running = True
        # Menu loop
        while self._running:
            self._pos_call = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    self.quit()
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

    def quit(self):
        '''Exit from game'''
        pygame.time.delay(500)
        if MUSIC:
            pygame.mixer.music.fadeout(500)
            pygame.mixer.music.stop()
        pygame.quit()
        sys.exit(0)

    async def _menu_call(self):
        '''Menu call'''
        pygame.time.delay(500)
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
            self.screen.blit(self.USCITA_IMG, (1250, 580))
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
                self._msg = self.una_manche.manage_ai_smart_bear_selection()
            if ((self.una_manche.against_computer) and 
                (self.una_manche.is_hunter_turn()) and 
                (self._computer == "HUNTER"))                :
                self._msg = self.una_manche.manage_ai_hunter_selection()                          
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
                self.screen.blit(self.LABEL, (580, 380))
                self.LOBSTER_25 = pygame.font.Font('LobsterTwo-Regular.otf',25)
                text = ""
                if self.una_manche.is_bear_winner():
                    #Non funziona con webasm
                    if MUSIC:
                        pygame.mixer.Channel(1).play(pygame.mixer.Sound('sfx/orso_ride.ogg'))
                    text = self.LOBSTER_25.render(f"   L'orso raggiunge {self.una_manche.get_max_bear_moves()} mosse e scappa!", 1, BLACK)
                else:
                    #Non funziona con webasm
                    if MUSIC:
                        pygame.mixer.Channel(1).play(pygame.mixer.Sound('sfx/success.ogg')) 
                    text = self.LOBSTER_25.render(f"  I cacciatori lasciano all'orso {self.una_manche.get_bear_moves()} mosse", 1, BLACK)
                self.screen.blit(text, (590,400))
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
        self._h_m_pA = HudTurnoMancheGiocatore(500,300,self.screen, self.player_A)
        self._h_t_pA = HudMosseOrsoMancheGiocatore(500,500,self.screen, self.player_A)
        self._h_m_pB = HudTurnoMancheGiocatore(850,300,self.screen, self.player_B)        
        self._h_t_pB = HudMosseOrsoMancheGiocatore(850,500,self.screen, self.player_B)       
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
        self._h_m_pA = HudTurnoMancheGiocatore(500,300,self.screen, self.player_A)
        self._h_t_pA = HudMosseOrsoMancheGiocatore(500,500,self.screen, self.player_A)
        self._h_m_pB = HudTurnoMancheGiocatore(850,300,self.screen, self.player_B)        
        self._h_t_pB = HudMosseOrsoMancheGiocatore(850,500,self.screen, self.player_B)       
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
        self._h_m_pA = HudTurnoMancheGiocatore(500,300,self.screen, self.player_A)
        self._h_t_pA = HudMosseOrsoMancheGiocatore(500,500,self.screen, self.player_A)
        self._h_m_pB = HudTurnoMancheGiocatore(850,300,self.screen, self.player_B)        
        self._h_t_pB = HudMosseOrsoMancheGiocatore(850,500,self.screen, self.player_B)       
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
    PANNELLO_UNO_IMG = get_img('img/buttonLong.png') #panel
    def __init__(self, opzioni: dict, default_value: object, game: OrsoPyGame, position: tuple):
        super().__init__()
        self.game = game
        self.LOBSTER_30 = pygame.font.Font('LobsterTwo-Regular.otf',30)
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
        self.game.screen.blit(OpzioneMenuNumeroMosse.PANNELLO_UNO_IMG, self.position)
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
        self.ESCI_GIOCO = get_img('img/buttonLong.png')
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',45)
        self._esci_str = self.LOBSTER_45.render("Esci dal gioco", 1, BLACK)
        self.rect = self._esci_str.get_rect()
        self.rect.x = 170
        self.rect.y = 690

    def update(self):
        self.game.screen.blit(self.ESCI_GIOCO, (100, 680))
        self.image = self._esci_str

    def action(self):
        self.game._running = False
        self.game.quit()
    

class OpzioneMenuInizioGioco(pygame.sprite.Sprite):
    '''Menu: inizio'''
    def __init__(self, game: OrsoPyGame):
        super().__init__()
        self.game = game
        self.INIZIA = get_img('img/buttonLong.png')
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',45)
        self._inizia_str = self.LOBSTER_45.render("  Inizia a giocare", 1, BLACK)
        self.rect = self._inizia_str.get_rect()
        self.rect.x = 1140
        self.rect.y = 690


    def update(self):
        self.game.screen.blit(self.INIZIA, (1100, 680))
        self.image = self._inizia_str

    async def action(self):
        self.game._running = False
        pygame.time.delay(800)
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
    ORSO_IDLE_IMG = get_img('img/little-bear-idle.png')
    TRE_CACCIATORI_IMG = get_img('img/TreCacciatoriTurno.png')
    
    PANNELLO_DUE_IMG = get_img('img/panel.png') #panel_due
 
    def __init__(self, game: OrsoPyGame):
        super().__init__()
        self.game = game
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',45)
        self._turno_str = self.LOBSTER_45.render("Turno", 1, BLACK)

    def update(self): 
        # Inizializzazione Pannello turno, parte fissa
        self.game.screen.blit(HudTurno.PANNELLO_DUE_IMG, (1250, 80))        
        self.game.screen.blit(self._turno_str, (1300, 90))          
        if self.game.una_manche._is_hunter_turn:
            self.rect = HudTurno.TRE_CACCIATORI_IMG.get_rect()
            self.rect.x = 1265
            self.rect.y = 160
            self.image = HudTurno.TRE_CACCIATORI_IMG
        else:
            self.rect = HudTurno.ORSO_IDLE_IMG.get_rect()
            self.rect.x = 1320
            self.rect.y = 160
            self.image = HudTurno.ORSO_IDLE_IMG



class HudMosseOrso(pygame.sprite.Sprite):
    '''HUD: pannello per il contatore mosse orso'''
    PANNELLO_DUE_IMG = get_img('img/panel.png') #panel_due

    def __init__(self, game: OrsoPyGame):
        super().__init__()
        self.game = game
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',45)
        self.LOBSTER_90 = pygame.font.Font('LobsterTwo-Regular.otf',90)
        # Pannello mosse orso
        self._mosse_str = self.LOBSTER_45.render("Mosse orso", 1, BLACK)     
            
    def update(self):
        self._mosse = self.LOBSTER_90.render(str(self.game.una_manche.get_bear_moves()), 1, BLACK)       
        self.game.screen.blit(HudMosseOrso.PANNELLO_DUE_IMG, (80, 80))  
        self.game.screen.blit(self._mosse_str, (90, 90))  
        self.rect = self._mosse.get_rect()
        self.rect.x = 145
        self.rect.y = 140
        self.image = self._mosse



#########################################
class HudTurnoMancheGiocatore(pygame.sprite.Sprite):
    '''HUD: pannello per il turno del giocatore'''
    ORSO_IMG = get_img('img/little-bear-sel.png')
    TRE_CACCIATORI_IMG = get_img('img/TreCacciatoriTurno.png')
    
    PANNELLO_DUE_IMG = get_img('img/panel.png') #panel_due
 
    def __init__(self, x, y, screen, giocatore: GamePlayer):
        super().__init__()
        self.x = x
        self.y = y
        self.screen = screen
        self.giocatore = giocatore
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',45)

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
    PANNELLO_DUE_IMG = get_img('img/panel.png') #panel_due

    def __init__(self, x, y, screen, giocatore: GamePlayer):
        super().__init__()
        self.x = x
        self.y = y
        self.screen = screen
        self.giocatore = giocatore        
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',45)
        self.LOBSTER_90 = pygame.font.Font('LobsterTwo-Regular.otf',90)
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
    PANNELLO_UNO_IMG = get_img('img/buttonLong.png') #panel

    def __init__(self, screen, msg):
        super().__init__()
        self.screen = screen
        self.msg = msg
        self.LOBSTER_45 = pygame.font.Font('LobsterTwo-Regular.otf',45)

    def update(self):
        self._text = self.LOBSTER_45.render(self.msg, 1, BLACK)
        self.screen.blit(HudGioco.PANNELLO_UNO_IMG, (580,150))
        self.rect = self._text.get_rect()
        self.rect.x = 590
        self.rect.y = 160
        self.image = self._text

#########################################
class HudMessaggi(pygame.sprite.Sprite):
    '''HUD: pannello per i messaggi'''    
    PANNELLO_UNO_IMG = get_img('img/buttonLong.png') #panel

    def __init__(self, game: OrsoPyGame):
        super().__init__()
        self.game = game
        self.LOBSTER_30 = pygame.font.Font('LobsterTwo-Regular.otf',30)

    def update(self):
        self._text = self.LOBSTER_30.render(self.game._msg, 1, BLACK)
        self.game.screen.blit(self.PANNELLO_UNO_IMG, (40, 680))
        self.rect = self._text.get_rect()
        self.rect.x = 50
        self.rect.y = 705
        self.image = self._text


class CasellaGiocoOrso(pygame.sprite.Sprite):
    '''
    Oggetto casella del gioco
    Gestisce la visualizzazione di personaggi e orme
    '''
    # Static resources
    TRASPARENTE = pygame.Surface((80,80), pygame.SRCALPHA)

    ORSO_IMG = get_img('img/little-bear.png')
    ORSO_IDLE_IMG = get_img('img/little-bear-idle.png')
    ORSO_SEL_IMG = get_img('img/little-bear-sel.png')

    CACCIATORE_UNO_IMG = get_img('img/little-hunter1.png')
    CACCIATORE_UNO_IDLE_IMG = get_img('img/little-hunter1-idle.png')
    CACCIATORE_UNO_SEL_IMG = get_img('img/little-hunter1-sel.png')

    CACCIATORE_DUE_IMG = get_img('img/little-hunter2.png')
    CACCIATORE_DUE_IDLE_IMG = get_img('img/little-hunter2-idle.png')
    CACCIATORE_DUE_SEL_IMG = get_img('img/little-hunter2-sel.png')

    CACCIATORE_TRE_IMG = get_img('img/little-hunter3.png')
    CACCIATORE_TRE_IDLE_IMG = get_img('img/little-hunter3-idle.png')
    CACCIATORE_TRE_SEL_IMG = get_img('img/little-hunter3-sel.png')
        
    # Orme
    ORMA_ORSO_IMG = get_img('img/impronta_orso.png')
    ORMA_CACCIATORE_IMG = get_img('img/impronta_cacciatore.png')

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
    opg.quit()

asyncio.run(main())
