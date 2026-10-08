# -*- coding: utf-8 -*-
"""
=====================================================================
 AJEDREZ EN PYTHON (ventana grafica con tkinter)
=====================================================================
 Es la misma version del juego en HTML/JavaScript, pasada a Python.

 QUE HACE (resumen):
   - Menu de introduccion: elegir color de tus piezas (blancas/negras)
     y la dificultad: Basico, Intermedio o Avanzado.
   - "Como jugar y consejos": movimientos, reglas especiales, estrategia.
   - Tablero completo con TODAS las reglas: jaque, jaque mate, rey
     ahogado (tablas), enroque, captura al paso y coronacion (a dama).
   - Botones: Pista, Deshacer, Reiniciar y Menu.
   - Apariencia: 6 colores de tablero y 6 estilos de pieza
     (Clasico, Contorno, Fichas, Iniciales, Neon, Metalico).
     Se guarda tu eleccion en el archivo  .ajedrez_config.json
     (en tu carpeta de usuario).

 COMO EJECUTARLO:
   No necesita instalar nada (tkinter ya viene con Python).
      python ajedrez.py          (o el boton Run de VS Code)

 ESTRUCTURA DEL CODIGO:
   1. Motor de ajedrez  : estado, generar jugadas, aplicar, legales.
   2. Inteligencia (IA) : evaluacion + minimax con poda alfa-beta.
   3. Dibujo de piezas  : 6 estilos sobre un Canvas.
   4. Interfaz (clase Ajedrez): menu, tutorial, tablero y apariencia.

 PROBLEMAS MATEMATICOS / ALGORITMOS:
   - El tablero es una lista de 64 casillas (0 = a8 ... 63 = h1).
     Fila = i // 8, columna = i % 8.
   - Evaluacion: material (peon 100, caballo 320, alfil 330, torre 500,
     dama 900) + bonus por centro + avance de peones.
   - Minimax en version NEGAMAX con poda ALFA-BETA: se prueban jugadas
     a "d" niveles de profundidad y se corta la rama cuando ya no puede
     mejorar el resultado. Complejidad aproximada O(b^(d/2)) en el
     mejor caso (b = jugadas posibles, d = profundidad).
   - Nivel Basico: profundidad 1 + ruido aleatorio (comete errores).
     Intermedio: profundidad 2.  Avanzado: profundidad 4.
=====================================================================
"""

import json
import os
import random
import sys
import threading
import tkinter as tk

# ===================================================================
#  DATOS BASICOS
# ===================================================================
# Tablero: lista de 64 casillas. Mayuscula = blancas, minuscula = negras.
# El estado es la tupla (tablero, turno, enroques, casilla_al_paso).
VALOR = {'p': 100, 'n': 320, 'b': 330, 'r': 500, 'q': 900, 'k': 0}
NIVELES = {1: (1, 220), 2: (2, 25), 3: (4, 0)}          # (profundidad, ruido)
NOMBRES = {1: 'Básico', 2: 'Intermedio', 3: 'Avanzado'}
KN = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
DG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ST = [(1, 0), (-1, 0), (0, 1), (0, -1)]

# Colores del tablero: (nombre, casilla clara, casilla oscura, piezas blancas, piezas negras)
TEMAS = [('Verde', '#eeeed2', '#769656', '#ffffff', '#111111'),
         ('Madera', '#f0d9b5', '#b58863', '#fff8e7', '#2b1b0e'),
         ('Azul', '#dee3e6', '#8ca2ad', '#ffffff', '#10243a'),
         ('Morado', '#e8dff5', '#9f7fd0', '#ffffff', '#2a1245'),
         ('Rojo', '#f7e1d7', '#d0716b', '#fff4ee', '#3a0f0f'),
         ('Gris', '#d4d7dc', '#5b6370', '#ffffff', '#12151a')]
ESTILOS = ['Clásico', 'Contorno', 'Fichas', 'Iniciales', 'Neón', 'Metálico']

GLIFOS = {'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚'}
CONTORNO = {'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙'}
LETRAS = {'K': 'R', 'Q': 'D', 'R': 'T', 'B': 'A', 'N': 'C', 'P': 'P'}  # Rey, Dama, Torre...

if sys.platform.startswith('win'):
    FUENTE = 'Segoe UI Symbol'
elif sys.platform == 'darwin':
    FUENTE = 'Apple Symbols'
else:
    FUENTE = 'DejaVu Sans'

BG, FG, ACC = '#f4f1ea', '#222222', '#3b6fb6'
CONFIG = os.path.join(os.path.expanduser('~'), '.ajedrez_config.json')


# ===================================================================
#  1. MOTOR DE AJEDREZ
# ===================================================================
def estado_inicial():
    """
    QUE HACE: crea la posicion inicial de la partida.
    ENTRADA : ninguna.
    PROCESO : convierte el texto 'rnbqkbnr/pppppppp/8/...' en 64 casillas.
    SALIDA  : (tablero, turno='w', enroques='KQkq', al_paso=-1)
    """
    b = []
    for fila in 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'.split('/'):
        for ch in fila:
            if ch.isdigit():
                b.extend([''] * int(ch))
            else:
                b.append(ch)
    return (b, 'w', 'KQkq', -1)


def atacada(b, sq, por):
    """
    QUE HACE: indica si la casilla sq esta atacada por el color 'por'.
    ENTRADA : tablero, casilla (0-63) y color atacante ('w' o 'b').
    PROCESO : busca desde sq peones, caballos, rey y piezas deslizantes
              (alfil/torre/dama) del color atacante.
    SALIDA  : True / False. Sirve para saber si hay jaque o si el
              rey puede pasar por una casilla (enroque).
    """
    r, c = sq >> 3, sq & 7
    w = por == 'w'
    pr = r + (1 if w else -1)                      # fila donde estaria un peon atacante
    if 0 <= pr < 8:
        peon = 'P' if w else 'p'
        for cc in (c - 1, c + 1):
            if 0 <= cc < 8 and b[pr * 8 + cc] == peon:
                return True
    caballo = 'N' if w else 'n'
    for dr, dc in KN:
        rr, cc = r + dr, c + dc
        if 0 <= rr < 8 and 0 <= cc < 8 and b[rr * 8 + cc] == caballo:
            return True
    rey = 'K' if w else 'k'
    for dr, dc in DG + ST:
        rr, cc = r + dr, c + dc
        if 0 <= rr < 8 and 0 <= cc < 8 and b[rr * 8 + cc] == rey:
            return True
    for dirs, piezas in ((DG, 'bq'), (ST, 'rq')):
        for dr, dc in dirs:
            rr, cc = r + dr, c + dc
            while 0 <= rr < 8 and 0 <= cc < 8:
                x = b[rr * 8 + cc]
                if x:
                    if x.isupper() == w and x.lower() in piezas:
                        return True
                    break
                rr += dr
                cc += dc
    return False


def generar(S):
    """
    QUE HACE: genera las jugadas pseudo-legales (todavia sin comprobar
              si dejan al propio rey en jaque).
    ENTRADA : estado S.
    PROCESO : recorre las piezas del turno y aplica el movimiento de cada una
              (peon, caballo, rey, alfil, torre, dama) + enroque.
    SALIDA  : lista de jugadas (origen, destino, tipo) donde tipo es
              None normal, 'p' coronacion, 'd' peon avanza 2,
              'e' captura al paso, 'c' enroque.
    """
    b, t, c, ep = S
    w = t == 'w'
    ms = []
    for i in range(64):
        ch = b[i]
        if not ch or ch.isupper() != w:
            continue
        p = ch.lower()
        r, cl = i >> 3, i & 7
        if p == 'p':
            d = -1 if w else 1
            r1 = r + d
            if r1 < 0 or r1 > 7:
                continue
            pr = 'p' if r1 == (0 if w else 7) else None
            if not b[r1 * 8 + cl]:
                ms.append((i, r1 * 8 + cl, pr))
                if r == (6 if w else 1) and not b[(r1 + d) * 8 + cl]:
                    ms.append((i, (r1 + d) * 8 + cl, 'd'))
            for dc in (-1, 1):
                cc = cl + dc
                if cc < 0 or cc > 7:
                    continue
                to = r1 * 8 + cc
                if b[to] and b[to].isupper() != w:
                    ms.append((i, to, pr))
                elif to == ep:
                    ms.append((i, to, 'e'))
        elif p in 'nk':
            for dr, dc in (KN if p == 'n' else DG + ST):
                rr, cc = r + dr, cl + dc
                if 0 <= rr < 8 and 0 <= cc < 8:
                    to = rr * 8 + cc
                    if not b[to] or b[to].isupper() != w:
                        ms.append((i, to, None))
        else:
            dirs = DG if p == 'b' else ST if p == 'r' else DG + ST
            for dr, dc in dirs:
                rr, cc = r + dr, cl + dc
                while 0 <= rr < 8 and 0 <= cc < 8:
                    to = rr * 8 + cc
                    if not b[to]:
                        ms.append((i, to, None))
                    else:
                        if b[to].isupper() != w:
                            ms.append((i, to, None))
                        break
                    rr += dr
                    cc += dc
    # Enroque: rey y torre sin mover, casillas libres y sin pasar por jaque
    o = 'b' if w else 'w'
    fila = 56 if w else 0
    K, R = ('K', 'R') if w else ('k', 'r')
    if b[fila + 4] == K and not atacada(b, fila + 4, o):
        if (K in c and b[fila + 7] == R and not b[fila + 5] and not b[fila + 6]
                and not atacada(b, fila + 5, o)):
            ms.append((fila + 4, fila + 6, 'c'))
        if (('Q' if w else 'q') in c and b[fila] == R and not b[fila + 1]
                and not b[fila + 2] and not b[fila + 3] and not atacada(b, fila + 3, o)):
            ms.append((fila + 4, fila + 2, 'c'))
    return ms


def aplicar(S, m):
    """
    QUE HACE: ejecuta una jugada sobre una COPIA del tablero.
    ENTRADA : estado S y jugada m = (origen, destino, tipo).
    PROCESO : mueve la pieza; si es captura al paso retira el peon;
              si es enroque mueve la torre; si es coronacion pone dama;
              actualiza los derechos de enroque y la casilla al paso.
    SALIDA  : nuevo estado (el original no se modifica).
    """
    b0, t, c, _ = S
    b = b0[:]
    f, to, k = m
    ch = b[f]
    w = t == 'w'
    ep = -1
    b[to] = ('Q' if w else 'q') if k == 'p' else ch
    b[f] = ''
    if k == 'e':
        b[to + (8 if w else -8)] = ''
    if k == 'c':
        fila = f - 4
        if to > f:
            b[fila + 5], b[fila + 7] = b[fila + 7], ''
        else:
            b[fila + 3], b[fila] = b[fila], ''
    if k == 'd':
        ep = (f + to) // 2
    if ch == 'K':
        c = c.replace('K', '').replace('Q', '')
    if ch == 'k':
        c = c.replace('k', '').replace('q', '')
    for s in (f, to):
        if s == 63: c = c.replace('K', '')
        if s == 56: c = c.replace('Q', '')
        if s == 7: c = c.replace('k', '')
        if s == 0: c = c.replace('q', '')
    return (b, 'b' if w else 'w', c, ep)


def casilla_rey(b, blancas):
    """QUE HACE: devuelve la casilla del rey (blanco o negro). SALIDA: 0-63."""
    return b.index('K' if blancas else 'k')


def legales(S):
    """
    QUE HACE: deja solo las jugadas legales.
    PROCESO : de las pseudo-legales descarta las que dejan al propio rey en jaque.
    SALIDA  : lista de jugadas legales.
    """
    w = S[1] == 'w'
    o = 'b' if w else 'w'
    res = []
    for m in generar(S):
        n = aplicar(S, m)
        if not atacada(n[0], casilla_rey(n[0], w), o):
            res.append(m)
    return res


def en_jaque(S):
    """QUE HACE: indica si el rey del jugador que tiene el turno esta en jaque."""
    w = S[1] == 'w'
    return atacada(S[0], casilla_rey(S[0], w), 'b' if w else 'w')


# ===================================================================
#  2. INTELIGENCIA ARTIFICIAL
# ===================================================================
def evaluar(b):
    """
    QUE HACE: da un puntaje a la posicion (positivo = ventaja blancas).
    PROCESO : suma el valor de cada pieza + bonus por estar cerca del centro
              (caballo, alfil, dama) + bonus por avance de los peones.
    SALIDA  : numero entero/decimal.
    """
    s = 0
    for i in range(64):
        ch = b[i]
        if not ch:
            continue
        p = ch.lower()
        w = ch.isupper()
        r, c = i >> 3, i & 7
        v = VALOR[p]
        cen = 7 - abs(c - 3.5) - abs(r - 3.5)
        if p == 'p':
            v += ((6 - r) if w else (r - 1)) * 8 + cen * 2
        elif p in 'nb':
            v += cen * 6
        elif p == 'q':
            v += cen
        s += v if w else -v
    return s


def buscar(S, d, a, b):
    """
    QUE HACE: busqueda NEGAMAX con poda ALFA-BETA.
    ENTRADA : estado, profundidad d, ventana (a, b).
    PROCESO : prueba cada jugada (capturas primero para podar mas) y llama
              recursivamente; corta cuando el puntaje ya supera la ventana.
              Si no hay jugadas: jaque mate (muy negativo) o tablas (0).
    SALIDA  : puntaje de la posicion desde el punto de vista de quien mueve.
    """
    if d == 0:
        return (1 if S[1] == 'w' else -1) * evaluar(S[0])
    ms = legales(S)
    if not ms:
        return -99000 - d if en_jaque(S) else 0
    bd = S[0]
    ms.sort(key=lambda m: -(VALOR[bd[m[1]].lower()] if bd[m[1]] else 0))
    for m in ms:
        s = -buscar(aplicar(S, m), d - 1, -b, -a)
        if s >= b:
            return b
        if s > a:
            a = s
    return a


def mejor(S, d, ruido):
    """
    QUE HACE: elige la jugada de la maquina.
    ENTRADA : estado, profundidad d y ruido (aleatoriedad: a mas ruido, mas errores).
    SALIDA  : la mejor jugada (origen, destino, tipo).
    """
    bm, bs = None, -10 ** 9
    for m in legales(S):
        s = -buscar(aplicar(S, m), d - 1, -10 ** 9, 10 ** 9) + random.random() * ruido
        if s > bs:
            bs, bm = s, m
    return bm


# ===================================================================
#  3. DIBUJO DE LAS PIEZAS (6 estilos)
# ===================================================================
def mezclar(hexa, rgb, a):
    """
    QUE HACE: mezcla un color '#rrggbb' con otro color rgb (resaltados).
    ENTRADA : color base, color rgb (r, g, b) y proporcion a (0 a 1).
    SALIDA  : color '#rrggbb'.
    """
    base = (int(hexa[1:3], 16), int(hexa[3:5], 16), int(hexa[5:7], 16))
    return '#%02x%02x%02x' % tuple(int(x * (1 - a) + y * a) for x, y in zip(base, rgb))


def rect_redondo(cv, x1, y1, x2, y2, r, **kw):
    """QUE HACE: dibuja un rectangulo con esquinas redondeadas en el Canvas."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
           x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def dibujar_pieza(cv, cx, cy, tam, ch, estilo, tema):
    """
    QUE HACE: dibuja una pieza en el Canvas segun el estilo elegido.
    ENTRADA : canvas, centro (cx, cy), tamano de casilla, letra de la pieza
              (mayuscula = blanca), estilo (0 a 5) y tema de colores.
    PROCESO : 0 Clasico (figura con borde)   1 Contorno (blancas huecas)
              2 Fichas (disco)               3 Iniciales (R, D, T, A, C, P)
              4 Neon (brillo)                5 Metalico (relieve)
    SALIDA  : dibuja en pantalla (no devuelve nada).
    """
    blanca = ch.isupper()
    p = ch.upper()
    pw, pb = tema[3], tema[4]
    o = max(1, tam // 40)
    tam_f = int(tam * 0.74)
    fam = FUENTE

    def texto(dx, dy, color, size=tam_f, f=None):
        cv.create_text(cx + dx, cy + dy + tam * 0.02, text=GLIFOS[p] if f is None else f,
                       fill=color, font=(fam, -size))

    if estilo == 0:                                           # Clasico
        borde = '#000000' if blanca else '#aaaaaa'
        for dx in (-o, 0, o):
            for dy in (-o, 0, o):
                if dx or dy:
                    texto(dx, dy, borde)
        texto(0, 0, pw if blanca else pb)
    elif estilo == 1:                                         # Contorno
        texto(0, 0, pb, f=CONTORNO[p] if blanca else GLIFOS[p])
    elif estilo == 2:                                         # Fichas
        r = tam * 0.39
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=pw if blanca else pb,
                       outline=pb if blanca else pw, width=1)
        texto(0, 0, pb if blanca else pw, size=int(tam * 0.46))
    elif estilo == 3:                                         # Iniciales
        r = tam * 0.37
        rect_redondo(cv, cx - r, cy - r, cx + r, cy + r, tam * 0.1,
                     fill=pw if blanca else pb, outline=pb if blanca else pw, width=2)
        cv.create_text(cx, cy, text=LETRAS[p], fill=pb if blanca else pw,
                       font=('Georgia', -int(tam * 0.42), 'bold'))
    elif estilo == 4:                                         # Neon
        brillo = '#00ffff' if blanca else '#ff00ff'
        for dx in (-2 * o, 0, 2 * o):
            for dy in (-2 * o, 0, 2 * o):
                if dx or dy:
                    texto(dx, dy, brillo)
        texto(0, 0, '#ffffff' if blanca else '#111111')
    else:                                                     # Metalico
        borde = '#000000' if blanca else '#ffffff'
        for dx in (-o, 0, o):
            for dy in (-o, 0, o):
                if dx or dy:
                    texto(dx, dy, borde)
        texto(o, o, '#8a8f99' if blanca else '#5a5f69')       # sombra
        texto(-o, -o, pw if blanca else pb)                   # brillo


# ===================================================================
#  4. INTERFAZ GRAFICA
# ===================================================================
SQ = 56      # tamano de cada casilla del tablero (pixeles)
PV = 34      # tamano de cada casilla de la vista previa

# Texto de "Como jugar y consejos". **negrita** se muestra en negrita.
TUTORIAL = [
    ('h', 'Objetivo'),
    ('p', 'Dar **jaque mate**: atacar al rey rival de modo que no pueda escapar, ni se pueda '
          'bloquear o capturar la pieza que lo ataca. Si el jugador no tiene jugadas pero su '
          'rey no está en jaque, es **tablas** (rey ahogado).'),
    ('h', 'Cómo se mueve cada pieza'),
    ('l', '**Peón ♟:** avanza 1 casilla (2 en su primer movimiento). Captura en diagonal, un paso adelante.'),
    ('l', '**Torre ♜:** en línea recta, horizontal o vertical, cualquier distancia.'),
    ('l', '**Alfil ♝:** en diagonal, cualquier distancia. Siempre se queda en su color de casilla.'),
    ('l', '**Caballo ♞:** en "L" (2 casillas y 1 al lado). Es la única pieza que salta.'),
    ('l', '**Dama ♛:** como torre y alfil juntos. La pieza más poderosa.'),
    ('l', '**Rey ♚:** 1 casilla en cualquier dirección. Nunca puede quedar en jaque.'),
    ('h', 'Movimientos especiales'),
    ('l', '**Enroque:** el rey se mueve 2 casillas hacia una torre y la torre pasa al otro lado. '
          'Se hace si ni el rey ni esa torre se han movido, no hay piezas en medio y el rey no '
          'está en jaque ni cruza casillas atacadas. Para hacerlo, mueve el rey 2 casillas.'),
    ('l', '**Captura al paso:** si un peón rival avanza 2 casillas y queda a tu lado, puedes '
          'capturarlo en diagonal como si hubiera avanzado 1, pero solo en la jugada inmediata.'),
    ('l', '**Coronación:** un peón que llega al final del tablero se convierte en pieza. '
          'Aquí siempre se convierte en dama.'),
    ('h', 'Cómo usar este juego'),
    ('p', 'Haz clic en una de tus piezas: se marcan sus jugadas (punto = mover, aro rojo = '
          'capturar). Haz clic en la casilla destino. Usa **Pista** si estás atascado y '
          '**Deshacer** para corregir.'),
    ('h', 'Consejos de movimientos'),
    ('l', '**Controla el centro** (e4, d4, e5, d5) con peones y piezas.'),
    ('l', '**Desarrolla caballos y alfiles** antes de mover la dama.'),
    ('l', '**Enroca pronto** para poner a salvo al rey.'),
    ('l', 'No muevas la misma pieza dos veces en la apertura sin necesidad.'),
    ('l', 'Antes de mover, mira **qué amenaza tu rival** y si tu pieza queda sin protección.'),
    ('l', 'Valor aproximado: peón 1, caballo 3, alfil 3, torre 5, dama 9. Cambia piezas solo si te conviene.'),
    ('l', 'En el final, **activa el rey** y avanza tus peones para coronar.'),
    ('l', 'Busca **horquillas**: un caballo o peón que ataque dos piezas a la vez.'),
]


class Ajedrez:
    """
    CLASE PRINCIPAL DE LA INTERFAZ.
    Guarda el estado de la partida y construye las 3 pantallas:
    menu, tutorial y juego, mas el panel de apariencia.
    """

    def __init__(self, root):
        """
        QUE HACE: crea la ventana, las pantallas y carga la apariencia guardada.
        ENTRADA : ventana principal de tkinter.
        SALIDA  : ventana lista, mostrando el menu.
        """
        self.root = root
        root.title('Ajedrez')
        root.configure(bg=BG)
        # Estado de la partida
        self.S = None
        self.hist = []
        self.sel = -1
        self.nivel = 1
        self.yo = 'w'
        self.terminado = False
        self.ocupado = False
        self.ultimo = None
        self.pista = None
        self.ticket = 0           # identifica la partida (para ignorar jugadas viejas de la IA)
        # Apariencia (se carga de archivo si existe)
        self.th, self.st = 0, 0
        try:
            with open(CONFIG, encoding='utf-8') as f:
                self.th, self.st = json.load(f)
        except Exception:
            pass
        if not (0 <= self.th < len(TEMAS)):
            self.th = 0
        if not (0 <= self.st < len(ESTILOS)):
            self.st = 0

        tk.Label(root, text='♞ Ajedrez', font=(FUENTE, 22, 'bold'), bg=BG, fg=FG).pack(pady=(8, 0))
        cuerpo = tk.Frame(root, bg=BG)
        cuerpo.pack(padx=12, pady=8)
        self.izq = tk.Frame(cuerpo, bg=BG)
        self.izq.pack(side='left', anchor='n')
        self.der = tk.Frame(cuerpo, bg=BG)
        self.der.pack(side='left', anchor='n', padx=(16, 0))

        self.f_menu = self.construir_menu()
        self.f_how = self.construir_tutorial()
        self.f_game = self.construir_juego()
        self.construir_apariencia()
        self.aplicar_apariencia()
        self.mostrar('menu')

    # ---------------------------------------------------------------
    def mostrar(self, nombre):
        """
        QUE HACE: cambia de pantalla ('menu', 'how' o 'game').
        PROCESO : oculta todas, muestra la elegida y oculta el panel de
                  apariencia solo en el tutorial. Cancela a la IA si estaba pensando.
        """
        self.ticket += 1
        self.ocupado = False
        for f in (self.f_menu, self.f_how, self.f_game):
            f.pack_forget()
        {'menu': self.f_menu, 'how': self.f_how, 'game': self.f_game}[nombre].pack()
        self.der.pack_forget()
        if nombre != 'how':
            self.der.pack(side='left', anchor='n', padx=(16, 0))

    # ---------------------------------------------------------------
    def construir_menu(self):
        """
        QUE HACE: arma la pantalla de INTRODUCCION.
        CONTENIDO: eleccion de color (blancas/negras), 3 niveles de
                   dificultad y el boton "Como jugar y consejos".
        SALIDA  : el Frame del menu.
        """
        f = tk.Frame(self.izq, bg=BG)
        tk.Label(f, text='Elige tu color y la dificultad\n(a la derecha puedes cambiar los colores\ny el estilo de las piezas):',
                 bg=BG, fg='#666666', font=('Helvetica', 10)).pack(pady=(0, 8))
        fila = tk.Frame(f, bg=BG)
        fila.pack(pady=4)
        self.bt_color = {}
        for c, txt in (('w', '⚪ Blancas'), ('b', '⚫ Negras')):
            b = tk.Button(fila, text=txt, width=14, font=('Helvetica', 11),
                          command=lambda c=c: self.elegir_color(c))
            b.pack(side='left', padx=4)
            self.bt_color[c] = b
        niveles = [(1, 'Básico', 'La máquina comete errores. Ideal para aprender.'),
                   (2, 'Intermedio', 'Piensa 2 jugadas por adelantado.'),
                   (3, 'Avanzado', 'Piensa 4 jugadas por adelantado. Puede tardar unos segundos.')]
        for n, t, d in niveles:
            tk.Button(f, text=f'{t}\n{d}', width=46, anchor='w', justify='left', padx=10, pady=6,
                      font=('Helvetica', 10), command=lambda n=n: self.iniciar(n)).pack(pady=5)
        tk.Button(f, text='Cómo jugar y consejos\nMovimientos, reglas especiales y estrategia',
                  width=46, anchor='w', justify='left', padx=10, pady=6, bg=ACC, fg='white',
                  activebackground=ACC, activeforeground='white', font=('Helvetica', 10),
                  command=lambda: self.mostrar('how')).pack(pady=5)
        self.elegir_color('w')
        return f

    def elegir_color(self, c):
        """QUE HACE: guarda con que color jugaras y resalta el boton elegido."""
        self.yo = c
        for k, b in self.bt_color.items():
            b.config(relief='sunken' if k == c else 'raised', bd=4 if k == c else 2,
                     font=('Helvetica', 11, 'bold' if k == c else 'normal'))

    # ---------------------------------------------------------------
    def construir_tutorial(self):
        """
        QUE HACE: arma la pantalla "Como jugar y consejos".
        PROCESO : inserta el texto de TUTORIAL en un cuadro con barra de
                  desplazamiento; **texto** se muestra en negrita.
        SALIDA  : el Frame del tutorial.
        """
        f = tk.Frame(self.izq, bg=BG)
        marco = tk.Frame(f, bg=BG)
        marco.pack()
        txt = tk.Text(marco, width=64, height=24, wrap='word', font=('Helvetica', 10), padx=10,
                      pady=6, bg='white', fg=FG, relief='flat')
        sb = tk.Scrollbar(marco, command=txt.yview)
        txt.config(yscrollcommand=sb.set)
        txt.pack(side='left')
        sb.pack(side='left', fill='y')
        txt.tag_config('h', font=('Helvetica', 12, 'bold'), spacing1=10, spacing3=3)
        txt.tag_config('b', font=('Helvetica', 10, 'bold'))
        txt.tag_config('l', lmargin1=12, lmargin2=24, spacing1=2)
        for tipo, contenido in TUTORIAL:
            if tipo == 'h':
                txt.insert('end', contenido + '\n', 'h')
                continue
            if tipo == 'l':
                txt.insert('end', '•  ', 'l')
            partes = contenido.split('**')
            for i, parte in enumerate(partes):
                etiquetas = ('b',) if i % 2 else ()
                txt.insert('end', parte, etiquetas + (('l',) if tipo == 'l' else ()))
            txt.insert('end', '\n')
        txt.config(state='disabled')
        tk.Button(f, text='← Volver al menú', bg=ACC, fg='white', activebackground=ACC,
                  activeforeground='white', font=('Helvetica', 11), padx=10, pady=4,
                  command=lambda: self.mostrar('menu')).pack(pady=8)
        return f

    # ---------------------------------------------------------------
    def construir_juego(self):
        """
        QUE HACE: arma la pantalla de JUEGO.
        CONTENIDO: mensaje de turno, tablero (Canvas), botones Pista,
                   Deshacer, Reiniciar, Menu y etiqueta del nivel.
        SALIDA  : el Frame del juego.
        """
        f = tk.Frame(self.izq, bg=BG)
        self.msg_var = tk.StringVar()
        tk.Label(f, textvariable=self.msg_var, bg=BG, fg=FG, font=('Helvetica', 12, 'bold')).pack(pady=(0, 4))
        self.cv = tk.Canvas(f, width=SQ * 8, height=SQ * 8, highlightthickness=2,
                            highlightbackground=FG)
        self.cv.pack()
        self.cv.bind('<Button-1>', self.clic)
        barra = tk.Frame(f, bg=BG)
        barra.pack(pady=8)
        for txt, cmd in (('Pista', self.dar_pista), ('Deshacer', self.deshacer),
                         ('Reiniciar', lambda: self.iniciar(self.nivel)),
                         ('Menú', lambda: self.mostrar('menu'))):
            tk.Button(barra, text=txt, width=10, command=cmd).pack(side='left', padx=3)
        self.lvl_var = tk.StringVar()
        tk.Label(f, textvariable=self.lvl_var, bg=BG, fg='#666666').pack()
        return f

    # ---------------------------------------------------------------
    def construir_apariencia(self):
        """
        QUE HACE: arma el panel de APARIENCIA (derecha).
        CONTENIDO: 6 botones de color de tablero, 6 de estilo de pieza y
                   una vista previa con piezas blancas y negras.
        """
        f = self.der
        tk.Label(f, text='Color del tablero (6 opciones)', bg=BG, fg=FG,
                 font=('Helvetica', 10, 'bold')).pack(anchor='w')
        g = tk.Frame(f, bg=BG)
        g.pack(pady=4)
        self.bt_th = []
        for i, t in enumerate(TEMAS):
            b = tk.Button(g, text=t[0], width=10, bg=t[2], fg='white', activebackground=t[2],
                          activeforeground='white', command=lambda i=i: self.elegir_tema(i))
            b.grid(row=i // 2, column=i % 2, padx=2, pady=2)
            self.bt_th.append(b)
        tk.Label(f, text='Estilo de las piezas (6 opciones)', bg=BG, fg=FG,
                 font=('Helvetica', 10, 'bold')).pack(anchor='w', pady=(10, 0))
        g2 = tk.Frame(f, bg=BG)
        g2.pack(pady=4)
        self.bt_st = []
        for i, n in enumerate(ESTILOS):
            b = tk.Button(g2, text=n, width=10, command=lambda i=i: self.elegir_estilo(i))
            b.grid(row=i // 2, column=i % 2, padx=2, pady=2)
            self.bt_st.append(b)
        self.pv = tk.Canvas(f, width=PV * 6, height=PV * 2, highlightthickness=2,
                            highlightbackground=FG)
        self.pv.pack(pady=10)

    def elegir_tema(self, i):
        """QUE HACE: cambia el color del tablero y vuelve a dibujar."""
        self.th = i
        self.aplicar_apariencia()

    def elegir_estilo(self, i):
        """QUE HACE: cambia el estilo de las piezas y vuelve a dibujar."""
        self.st = i
        self.aplicar_apariencia()

    def aplicar_apariencia(self):
        """
        QUE HACE: refresca botones, vista previa y tablero con la eleccion
                  actual y la guarda en el archivo de configuracion.
        """
        tema = TEMAS[self.th]
        for i, b in enumerate(self.bt_th):
            b.config(relief='sunken' if i == self.th else 'raised', bd=4 if i == self.th else 2)
        for i, b in enumerate(self.bt_st):
            b.config(relief='sunken' if i == self.st else 'raised', bd=4 if i == self.st else 2)
        self.pv.delete('all')
        for k in range(12):
            r, c = divmod(k, 6)
            x, y = c * PV, r * PV
            self.pv.create_rectangle(x, y, x + PV, y + PV, outline='',
                                     fill=tema[2] if (r + c) % 2 else tema[1])
            p = 'KQRBNP'[c]
            dibujar_pieza(self.pv, x + PV / 2, y + PV / 2, PV, p if r == 0 else p.lower(),
                          self.st, tema)
        if self.S is not None:
            self.dibujar()
        try:
            with open(CONFIG, 'w', encoding='utf-8') as f:
                json.dump([self.th, self.st], f)
        except Exception:
            pass

    # ---------------------------------------------------------------
    def msg(self, texto):
        """QUE HACE: muestra un mensaje arriba del tablero."""
        self.msg_var.set(texto)

    def turno(self):
        """QUE HACE: devuelve el texto 'Tu turno (blancas/negras)'."""
        return 'Tu turno (' + ('blancas' if self.yo == 'w' else 'negras') + ')'

    def iniciar(self, nivel):
        """
        QUE HACE: empieza una partida nueva.
        ENTRADA : nivel 1, 2 o 3.
        PROCESO : reinicia el estado, muestra el tablero y, si juegas con
                  negras, deja que la maquina haga la primera jugada.
        """
        self.nivel = nivel
        self.S = estado_inicial()
        self.hist, self.sel, self.ultimo, self.pista = [], -1, None, None
        self.terminado = False
        self.mostrar('game')                      # (tambien cancela a la IA anterior)
        self.lvl_var.set(f'Nivel: {NOMBRES[nivel]} · Juegas con '
                         + ('blancas' if self.yo == 'w' else 'negras'))
        self.dibujar()
        self.siguiente()

    # ---------------------------------------------------------------
    def dibujar(self):
        """
        QUE HACE: dibuja el tablero completo.
        PROCESO : casillas (con resaltados: ultima jugada, pista, seleccion,
                  jaque), puntos de jugadas posibles, aros de captura y piezas.
                  Si juegas con negras el tablero se gira.
        """
        cv, S, tema = self.cv, self.S, TEMAS[self.th]
        cv.delete('all')
        destinos = ([m[1] for m in legales(S) if m[0] == self.sel] if self.sel >= 0 else [])
        rey = casilla_rey(S[0], S[1] == 'w') if en_jaque(S) else -1
        for i in range(64):
            r, c = i >> 3, i & 7
            fila, col = (r, c) if self.yo == 'w' else (7 - r, 7 - c)
            x, y = col * SQ, fila * SQ
            color = tema[2] if (r + c) % 2 else tema[1]
            if self.ultimo and i in (self.ultimo[0], self.ultimo[1]):
                color = mezclar(color, (255, 235, 59), .40)
            if self.pista and i in (self.pista[0], self.pista[1]):
                color = mezclar(color, (0, 200, 120), .50)
            if i == self.sel:
                color = mezclar(color, (80, 160, 255), .55)
            if i == rey:
                color = mezclar(color, (255, 40, 40), .60)
            cv.create_rectangle(x, y, x + SQ, y + SQ, fill=color, outline='')
            ch = S[0][i]
            if i in destinos:
                if ch:
                    cv.create_rectangle(x + 2, y + 2, x + SQ - 2, y + SQ - 2, outline='#dc2828', width=4)
                else:
                    cv.create_oval(x + SQ * .36, y + SQ * .36, x + SQ * .64, y + SQ * .64,
                                   fill=mezclar(color, (0, 0, 0), .35), outline='')
            if ch:
                dibujar_pieza(cv, x + SQ / 2, y + SQ / 2, SQ, ch, self.st, tema)

    # ---------------------------------------------------------------
    def clic(self, ev):
        """
        QUE HACE: atiende el clic del jugador en el tablero.
        PROCESO : convierte el pixel a casilla; si hay una pieza propia
                  seleccionada y la casilla es un destino legal, juega;
                  si no, selecciona la pieza clicada.
        """
        if self.terminado or self.ocupado or self.S[1] != self.yo:
            return
        col, fila = ev.x // SQ, ev.y // SQ
        if not (0 <= col < 8 and 0 <= fila < 8):
            return
        i = fila * 8 + col if self.yo == 'w' else (7 - fila) * 8 + (7 - col)
        m = next((x for x in legales(self.S) if x[0] == self.sel and x[1] == i), None)
        if m:
            self.hist.append(self.S)
            self.S, self.ultimo, self.sel, self.pista = aplicar(self.S, m), m, -1, None
            self.dibujar()
            self.siguiente()
            return
        ch = self.S[0][i]
        self.sel = i if ch and ch.isupper() == (self.yo == 'w') else -1
        self.pista = None
        self.dibujar()

    def siguiente(self):
        """
        QUE HACE: decide que pasa despues de cada jugada.
        PROCESO : si no hay jugadas legales -> jaque mate o tablas.
                  Si le toca a la maquina, calcula su jugada en un HILO
                  aparte (para que la ventana no se congele) y la juega.
        """
        S = self.S
        if not legales(S):
            self.terminado = True
            if en_jaque(S):
                self.msg('Jaque mate. Gana la máquina.' if S[1] == self.yo else '¡Jaque mate! ¡Ganaste!')
            else:
                self.msg('Tablas por rey ahogado.')
            self.dibujar()
            return
        if S[1] != self.yo:
            self.ocupado = True
            self.msg('La máquina piensa…')
            d, ruido = NIVELES[self.nivel]
            res, ticket = [None], self.ticket

            def trabajo():
                res[0] = mejor(S, d, ruido)

            threading.Thread(target=trabajo, daemon=True).start()
            self.root.after(100, lambda: self.esperar(res, ticket))
        else:
            self.msg(('¡Jaque! ' if en_jaque(S) else '') + self.turno())

    def esperar(self, res, ticket):
        """
        QUE HACE: revisa cada 0,1 s si la maquina ya eligio su jugada.
        PROCESO : si la partida cambio (menu/reiniciar) la ignora; si ya
                  hay resultado, la juega y llama a siguiente().
        """
        if ticket != self.ticket:
            return
        if res[0] is None:
            self.root.after(100, lambda: self.esperar(res, ticket))
            return
        self.hist.append(self.S)
        self.S, self.ultimo = aplicar(self.S, res[0]), res[0]
        self.ocupado = False
        self.dibujar()
        self.siguiente()

    def deshacer(self):
        """
        QUE HACE: retrocede tu ultima jugada (y la de la maquina).
        PROCESO : saca estados del historial hasta que sea tu turno.
        """
        if self.ocupado or not self.hist:
            return
        self.S = self.hist.pop()
        if self.S[1] != self.yo and self.hist:
            self.S = self.hist.pop()
        self.terminado, self.ultimo, self.pista, self.sel = False, None, None, -1
        self.dibujar()
        self.siguiente()

    def dar_pista(self):
        """QUE HACE: calcula una buena jugada (profundidad 2) y la resalta en verde."""
        if self.ocupado or self.terminado or self.S[1] != self.yo:
            return
        self.pista, self.sel = mejor(self.S, 2, 0), -1
        self.dibujar()


# ===================================================================
#  PUNTO DE ENTRADA
# ===================================================================
def main():
    """QUE HACE: crea la ventana de tkinter y arranca el juego."""
    root = tk.Tk()
    Ajedrez(root)
    root.mainloop()


# Se ejecuta solo si corremos este archivo directamente
if __name__ == '__main__':
    main()