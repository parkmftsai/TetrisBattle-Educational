'''
Tetris Battle

originally Ccreated by Yuwei Xu, Eman Igbokwe

modified by Yi-Lin Sung

this is a similar version to the ever popular tetris battle
game with not many changes"
'''

#basic modules needed for game to run
import os
import pygame
import random

import numpy as np

from .settings import *

from copy import deepcopy

import time as t
from collections import Counter

def put_block_in_grid(grid, block, px, py):
    feasibles = block.return_pos_color(px, py)

    for x, y, c in feasibles:
        '''
        TODO: y boundary
        '''
        if -1 < x < GRID_WIDTH and -1 < y < len(grid[0]):
            grid[x][y] = c

def collide(grid, block, px, py):
    feasibles = block.get_feasible()

    # print(px)
    # print(block)
    # excess = len(grid[0]) - GRID_DEPTH
    for pos in feasibles:
        # print(px + pos[0], py + pos[1])
        if px + pos[0] > GRID_WIDTH - 1:   # right
            return True

        if px + pos[0] < 0:   # left
            return True

        if py + pos[1] > len(grid[0]) - 1:  # down
            return True

        if py + pos[1] < 0:   # up
            continue
        
        if grid[px + pos[0]][py + pos[1]] > 0:
            # print(px, py)
            # print(px + pos[0], py + pos[1])
            # print("Touch")
            return True

    return False

# collidedown function
# for i in range 4(y position)
# if px+y=20 then collidedown =true
# used for move down and rotation collisions
def collideDown(grid, block, px, py):
    return collide(grid, block, px, py + 1)

# collideleft function
# for i in range 4(x positions)
# if blockx +x =0 then collide left = True
# used for moving block and rotation collision
def collideLeft(grid, block, px, py):
    return collide(grid, block, px - 1, py)

# collideright function
# for i in range 4(x positions)
# if blockx +x +1>9 then collide left = True
# plus 1 is there cuz pxis on left of the piece
# used for moving block and rotation collision
def collideRight(grid, block, px, py):
    return collide(grid, block, px + 1, py)

# rotatecollision function
# when respective rotate buttons are pressed
# this function checks if collide(left right or down has occured)
# if it hasnt then rotation occurs
def rotateCollide(grid, block, px, py):
    feasibles = block.get_feasible()

    left_most = 100
    right_most = 0
    up_most = 100
    down_most = 0

    for pos in feasibles:
        right_most = max(right_most, pos[0])
        left_most = min(left_most, pos[0])

        down_most = max(down_most, pos[1])
        up_most = min(up_most, pos[1])

    c = Counter()
    # print(px)
    # print(block)
    excess = len(grid[0]) - GRID_DEPTH
    for pos in feasibles:
        # print(px + pos[0], py + pos[1])
        if px + pos[0] > 9:   # right
            c.update({"right": 1})

        if px + pos[0] < 0:   # left
            c.update({"left": 1})

        if py + pos[1] > len(grid[0]) - 1:  # down
            c.update({"down": 1})

        # if py + pos[1] < excess:   # up
        #     c.update({"up": 1})

        if 0 <= px + pos[0] <= 9 and excess <= py + pos[1] <= len(grid[0]) - 1:
        
            if grid[px + pos[0]][py + pos[1]] > 0:
                if pos[0] == left_most:
                    c.update({"left": 1})
                elif pos[0] == right_most:
                    c.update({"right": 1})
                elif pos[1] == down_most:
                    c.update({"down": 1})
                # elif pos[1] == up_most:
                #     c.update({"up": 1})

    # print(c)
    if len(c) == 0:
        return False
    else:
        return c.most_common()[0][0]


#this function checks if a tspin has occured
#checks all possible tspin positions
#then spins the t piece into the spot
def tspinCheck(grid, block, px, py):

    if collideDown(grid, block, px, py) == True:
        if block.block_type() == 'T':
            if px + 2 < GRID_WIDTH and py + 3 < len(grid[0]):
                if grid[px][py + 1] > 0 and grid[px][py + 3] > 0 and grid[px + 2][py + 3] > 0:

                    return True
                elif grid[px][py + 3] > 0 and grid[px + 2][py + 3] > 0 and grid[px + 2][py + 1] > 0:

                    return True
    return False

# this function rotates the piece
# when rotation button is hit the next grid in the piece list becomes the piece
def rotate(grid, block, px, py, _dir=1):
    # print(grid)

    block.rotate(_dir)

    # b = block.now_block()

    collision = rotateCollide(grid, block, px, py) # checks for collisions
    # print(collision)
    find = 0

    if collision == "left":
        y_list = [0, 1, -1]
        for s_x in range(0, 3):
            for s_y in y_list:
                if not find and not collide(grid, block, px + s_x, py + s_y):
                    px += s_x
                    py += s_y
                    find = 1
    elif collision == "right":
        y_list = [0, 1, -1]
        for s_x in reversed(range(-2, 0)):
            for s_y in y_list:
                if not find and not collide(grid, block, px + s_x, py + s_y):
                    px += s_x
                    py += s_y
                    find = 1
    elif collision == "down":
        # y_list = [-1, -2]
        x_list = [0, -1, 1, -2, 2]
        for s_y in reversed(range(-1, 0)):
            for s_x in x_list:
                if not find and not collide(grid, block, px + s_x, py + s_y):
                    px += s_x
                    py += s_y
                    find = 1

    elif collision == "up":
        x_list = [0, -1, 1, -2, 2]
        for s_y in range(1, 2):
            for s_x in x_list:
                if not find and not collide(grid, block, px + s_x, py + s_y):
                    px += s_x
                    py += s_y
                    find = 1

    if collision != False and not find:
        block.rotate(- _dir) 

    # print(collision)

    tspin = 0
    if tspinCheck(grid, block, px, py) == True:
        tspin = 1
        print("Tspin rotate")

    # return [block, px, py, tspin]

    return block, px, py, tspin


# Modern human-play controls (SRS rotation + instantaneous input).
# Y axis increases downwards, unlike the SRS tables on Tetris Wiki.
_JLSTZ_KICKS = {
    (0, 1): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (1, 2): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (2, 3): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
    (3, 0): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (1, 0): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (2, 1): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (3, 2): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (0, 3): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
}
_I_KICKS = {
    (0, 1): ((0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)),
    (1, 2): ((0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)),
    (2, 3): ((0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)),
    (3, 0): ((0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)),
    (1, 0): ((0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)),
    (2, 1): ((0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)),
    (3, 2): ((0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)),
    (0, 3): ((0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)),
}


def rotate_srs(grid, block, px, py, direction=1):
    """Try SRS tests in order; revert rotation if all positions are blocked.

    Returns (block, x, y, succeeded). Only used by the human game; the
    original Gym/AI `rotate` logic stays unchanged for reproducibility.
    """
    before = block.current_shape_id
    after = (before + direction) % len(block.possible_shapes)
    block.rotate(direction)
    kind = block.block_type()
    tests = ((0, 0),) if kind == "O" else (
        _I_KICKS if kind == "I" else _JLSTZ_KICKS
    ).get((before, after), ((0, 0),))
    for dx, dy in tests:
        if not collide(grid, block, px + dx, py + dy):
            return block, px + dx, py + dy, True
    block.current_shape_id = before
    return block, px, py, False


# this function drops the piece as far as it can go until
# it collides with a piece below it
def hardDrop(grid, block, px, py):
    y = 0
    x = 0
    if collideDown(grid, block, px, py) == False:
        x = 1
    if x == 1:
        while True:
            py += 1
            y += 1
            if collideDown(grid, block, px, py) == True:
                break
        
    return y

# this function enables you to hold a piece
def hold(block, held, _buffer):
    # when piece is held the block at pos[0]
    # in the nextlist becomes the newpiece
    if held == None:
        held = block
        block = _buffer.new_block()

    # the piece switches with the held piece     
    else:
        block, held = held, block
        
    return [block, held]

def freeze(last_time):
    start = t.time()
    while t.time() - start < last_time:
        pass

def get_infos(board):
    # board is equal to grid

    # borrow from https://github.com/scuriosity/machine-learning-tetris/blob/master/tetris.py
    # This function will calculate different parameters of the current board

    # Initialize some stuff
    heights = [0] * len(board)
    diffs = [0] * (len(board) - 1)
    holes = 0
    diff_sum = 0

    # Calculate the maximum height of each column
    for i in range(0, len(board)):  # Select a column
        for j in range(0, len(board[0])):  # Search down starting from the top of the board
            if int(board[i][j]) > 0:  # Is the cell occupied?
                heights[i] = len(board[0]) - j  # Store the height value
                break

    # Calculate the difference in heights
    for i in range(0, len(diffs)):
        diffs[i] = heights[i + 1] - heights[i]

    # Calculate the maximum height
    max_height = max(heights)

    # Count the number of holes
    for i in range(0, len(board)):
        occupied = 0  # Set the 'Occupied' flag to 0 for each new column
        for j in range(0, len(board[0])):  # Scan from top to bottom
            if int(board[i][j]) > 0:
                occupied = 1  # If a block is found, set the 'Occupied' flag to 1
            if int(board[i][j]) == 0 and occupied == 1:
                holes += 1  # If a hole is found, add one to the count

    height_sum = sum(heights)

    for i in diffs:
        diff_sum += abs(i)

    return height_sum, diff_sum, max_height, holes

class Piece(object):
    def __init__(self, _type, possible_shapes):

        self._type = _type
        self.possible_shapes = possible_shapes

        self.current_shape_id = 0 

    def block_type(self):
        return self._type

    def reset(self):
        self.current_shape_id = 0

    def return_pos_color(self, px, py):
        feasibles = []

        block = self.now_block()

        for x in range(BLOCK_WIDTH):
            for y in range(BLOCK_LENGTH):
                if block[x][y] > 0:
                    feasibles.append([px + x, py + y, block[x][y]])
        return feasibles

    def return_pos(self, px, py):
        feasibles = []

        block = self.now_block()

        for x in range(BLOCK_WIDTH):
            for y in range(BLOCK_LENGTH):
                if block[x][y] > 0:
                    feasibles.append([px + x, py + y])
        return feasibles

    def get_feasible(self):
        feasibles = []

        b = self.now_block()

        for x in range(BLOCK_WIDTH):
            for y in range(BLOCK_LENGTH):
                if b[x][y] > 0:
                    feasibles.append([x, y])

        return feasibles

    def now_block(self):
        return self.possible_shapes[self.current_shape_id]

    # def move_right(self, unit=1):
    #     self.px += unit

    # def move_left(self, unit=1):
    #     self.px -= unit

    # def move_up(self, unit=1):
    #     self.py -= unit

    # def move_down(self, unit=1):
    #     self.py += unit

    def rotate(self, _dir=1):
        self.current_shape_id += _dir
        self.current_shape_id %= len(self.possible_shapes)

class Buffer(object):
    '''
    Stores the coming pieces, every 7 pieces in a group.
    '''
    def __init__(self):
        self.now_list = []
        self.next_list = []

        self.fill(self.now_list)
        self.fill(self.next_list)

    '''
    make sure "now list" are filled

                     now list           next list
    next piece <- [           ]   <-  [            ]
 
    '''
    def new_block(self):
        out = self.now_list.pop(0)
        self.now_list.append(self.next_list.pop(0))

        if len(self.next_list) == 0:
            self.fill(self.next_list)

        return out

    def fill(self, _list):
        pieces_keys = deepcopy(POSSIBLE_KEYS)
        random.shuffle(pieces_keys)

        for key in pieces_keys:
            _list.append(Piece(key, PIECES_DICT[key]))


'''

class for player

'''

class Player(object):
    def __init__(self, info_dict):

        self._id = info_dict.get("id")

        self._drop = info_dict.get("drop")
        self._hold = info_dict.get("hold")
        self._bomb = info_dict.get("bomb")
        self._rotate_right = info_dict.get("rotate_right")
        self._rotate_left = info_dict.get("rotate_left")
        self._down = info_dict.get("down")
        self._left = info_dict.get("left")
        self._right = info_dict.get("right")

    def is_pressed(self, action, key):
        """Match a key or alternative binding without changing AI action IDs."""
        binding = getattr(self, "_" + action)
        if binding is None:
            return False
        if isinstance(binding, (tuple, list, set)):
            return key in binding
        return key == binding

    @property
    def id(self):
        return self._id

    @property
    def drop(self):
        return self._drop

    @property
    def hold(self):
        return self._hold

    @property
    def bomb(self):
        return self._bomb

    @property
    def rotate_right(self):
        return self._rotate_right

    @property
    def rotate_left(self):
        return self._rotate_left

    @property
    def down(self):
        return self._down

    @property
    def left(self):
        return self._left

    @property
    def right(self):
        return self._right

'''

class Judge

'''

class Judge(object):

    @staticmethod
    def check_ko_win(tetris, max_ko):
        if tetris.KO >= max_ko:
            return 1

        return 0

    @staticmethod
    def who_win(tetris_1, tetris_2):
        if tetris_2.KO > tetris_1.KO: # Checks who is the winner of the game
            return tetris_2.get_id() # a is screebn.copy,endgame ends the game,2 is player 2 wins
        if tetris_1.KO > tetris_2.KO:
            return tetris_1.get_id() # a is screebn.copy,endgame ends the game,1 is player 1 wins
        if tetris_1.KO == tetris_2.KO:
            if tetris_2.sent > tetris_1.sent:
                return tetris_2.get_id() # a is screebn.copy,endgame ends the game,2 is player 2 wins
            elif tetris_1.sent > tetris_2.sent:
                return tetris_1.get_id() # a is screebn.copy,endgame ends the game,1 is player 1 wins
            elif tetris_1.get_maximum_height() > tetris_2.get_maximum_height():
                return tetris_2.get_id()
            elif tetris_2.get_maximum_height() > tetris_1.get_maximum_height():
                return tetris_1.get_id()
            else:
                return tetris_1.get_id() # no UI of draw

class Tetris(object):
    def __init__(self, player, gridchoice, bombs_enabled=False, modern_controls=False,
                 das_ms=120.0, arr_ms=25.0, soft_drop_ms=30.0):

        if gridchoice == "none":
            self.o_grid = [[0] * GRID_DEPTH for i in range(GRID_WIDTH)]

        if gridchoice == "classic":
            self.o_grid = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 3], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]

        if gridchoice == "comboking":
            self.o_grid = [[0, 0, 0, 0, 0, 5, 5, 5, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], 
                          [0, 0, 0, 0, 0, 6, 6, 6, 4, 5, 5, 6, 6, 6, 6, 6, 6, 6, 4, 5], 
                          [0, 0, 0, 0, 0, 0, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], 
                          [0, 0, 0, 0, 0, 0, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5], 
                          [0, 0, 0, 0, 0, 6, 6, 6, 4, 5, 5, 6, 6, 6, 6, 6, 6, 6, 4, 5], 
                          [0, 0, 0, 0, 0, 5, 5, 5, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]]

        if gridchoice == "lunchbox":
            self.o_grid = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 5, 5, 5, 5, 5, 5, 5, 5, 1], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 5, 2, 2, 2, 2, 2, 2, 5, 1], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 5, 2, 4, 4, 4, 4, 2, 5, 1], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 5, 2, 4, 4, 4, 4, 2, 5, 6], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 5, 2, 2, 2, 2, 2, 2, 5, 6], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 5, 5, 5, 5, 5, 5, 5, 5, 6], 
                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6]]


        self.player = player
        # Human keyboard responsiveness is opt-in so the existing Gym/AI
        # action timing and rotation semantics are left untouched.
        self.modern_controls = bool(modern_controls)
        self.das_ms = float(das_ms)
        self.arr_ms = float(arr_ms)
        self.soft_drop_ms = float(soft_drop_ms)
        if not (0 <= self.das_ms <= 500 and 1 <= self.arr_ms <= 250
                and 1 <= self.soft_drop_ms <= 250):
            raise ValueError("Input timing out of range: DAS 0-500, ARR/soft drop 1-250 milliseconds")
        # Bombs are opt-in: human TetrisBattle enables them; legacy gym/API
        # environments retain their original action/observation semantics.
        self.bombs_enabled = bool(bombs_enabled)
        # Human UI registers a callback for sound, while AI interfaces do not.
        self.on_event = None

        self.reset()

    def emit_event(self, name):
        if self.on_event is not None:
            self.on_event(name)

    def reset(self):
        self.grid = deepcopy(self.o_grid)

        self.oldko = 0 # these two used to keep track of ko's

        self._n_used_block = 1

        self.buffer = Buffer()
        # list of the held piece
        self.held = None
        self.block = self.buffer.new_block()

        # amount of lines sent for p1 and p2
        self.sent = 0
        self.tempsend = 0 # tempsending for p1 and p2
        self.oldcombo = self.combo = -1 # used for checking comboas
        self.tspin = 0 # for t spin
        self.now_back2back = 0
        self.pre_back2back = 0
        self.tetris = 0

        #for "KO"
        self._KO = 0 

        self._attacked = 0
        self._is_fallen = 0
        # Bombs are NOT inventory items. In original Facebook Battle 2P,
        # they live inside incoming garbage rows and detonate on contact.
        # Keep these deprecated attributes only for old integrations.
        self.bomb_charges = 0
        self.bomb_armed = False
        self.bomb_charge_progress = 0
        self.bombs_used = 0
        self.last_bomb_rows = 0
        self.bomb_chain_count = 0
        self.garbage_overflow = False
        self.topped_out = False
        self.last_blast = []
        self.last_cleared_rows = []
        self.total_lines = 0
        self.perfect_clears = 0
        self.last_bomb_removed = 0
        self.attack_outgoing = 0
        self.garbage_cancelled = 0

        self.px = 4
        self.py = -2

        # DEFINING VARIABLES
        self.cleared = 0
        self.kocounter = 0
        self.stopcounter = 0

        self.isholded = 0

        self.pressedRight = False
        self.pressedLeft = False
        self.pressedDown = False
        # Instant first press, 120 ms DAS, 25 ms ARR, 30 ms soft drop at 100 FPS.
        # Counters stay independent across actions; no global 100ms lockout.
        self._held_actions = set()
        self._direction_keys = {"left": set(), "right": set(), "down": set()}
        self._horizontal_active = None
        self._horizontal_elapsed_ms = 0.0
        self._horizontal_repeats = 0
        self._down_elapsed_ms = 0.0
        self._modern_last_rotation = False

        self.LAST_ROTATE_TIME = 0
        self.LAST_MOVE_SHIFT_TIME = 0
        self.LAST_MOVE_DOWN_TIME = 0
        self.LAST_COMBO_DRAW_TIME = 0
        self.LAST_TETRIS_DRAW_TIME = 0
        self.LAST_TSPIN_DRAW_TIME = 0
        self.LAST_BACK2BACK_DRAW_TIME = 0
        self.LAST_NATRUAL_FALL_TIME = 0
        self.LAST_FALL_DOWN_TIME = 0


        self.tetris_drawing = 0
        self.tspin_drawing = 0
        self.back2back_drawing = 0

        self.combo_counter = 0

        self.natural_down_counter = 0
        self._check_spawn_topout()

    def _check_spawn_topout(self):
        """A blocked new/held piece is a top-out before it can move or lock.

        Only flag new spawns, never the piece that has just been locked
        (which naturally overlaps the frozen blocks in the grid).
        """
        if self.modern_controls and collide(self.grid, self.block, self.px, self.py):
            self.topped_out = True
        return self.topped_out

    def increment_timer(self):
        self.LAST_ROTATE_TIME += 1
        self.LAST_MOVE_SHIFT_TIME += 1
        self.LAST_MOVE_DOWN_TIME += 1
        self.LAST_COMBO_DRAW_TIME += 1
        self.LAST_TETRIS_DRAW_TIME += 1
        self.LAST_TSPIN_DRAW_TIME += 1
        self.LAST_BACK2BACK_DRAW_TIME += 1
        self.LAST_NATRUAL_FALL_TIME += 1
        self.LAST_FALL_DOWN_TIME += 1

    @property
    def is_fallen(self):
        return self._is_fallen

    @property
    def n_used_block(self):
        return self._n_used_block

    @property
    def KO(self):
        return self._KO

    @property
    def attacked(self):
        return self._attacked
    
    def get_grid(self):
        excess = len(self.grid[0]) - GRID_DEPTH
        return_grids = np.zeros(shape=(GRID_WIDTH, GRID_DEPTH), dtype=np.float32)
        
        block, px, py = self.block, self.px, self.py
        excess = len(self.grid[0]) - GRID_DEPTH
        b = block.now_block()

        for i in range(len(self.grid)):
            return_grids[i] = np.array(self.grid[i][excess:GRID_DEPTH], dtype=np.float32)
        return_grids[return_grids > 0] = 1

        add_y = hardDrop(self.grid, self.block, self.px, self.py)

        for x in range(BLOCK_WIDTH):
            for y in range(BLOCK_LENGTH):
                if b[x][y] > 0:
                    # draw ghost grid
                    if -1 < px + x < 10 and -1 < py + y + add_y - excess < 20:
                        return_grids[px + x][py + y + add_y - excess] = 0.3
                        
                    if -1 < px + x < 10 and -1 < py + y - excess < 20:
                        return_grids[px + x][py + y - excess] = 0.7

        informations = np.zeros(shape=(len(PIECE_NUM2TYPE) - 1, GRID_DEPTH), dtype=np.float32)
        if self.held != None:
            informations[PIECE_TYPE2NUM[self.held.block_type()] - 1][0] = 1

        nextpieces = self.buffer.now_list
        for i in range(5): # 5 different pieces 
            _type = nextpieces[i].block_type()
            informations[PIECE_TYPE2NUM[_type] - 1][i + 1] = 1
        # index start from 6

        informations[0][6] = self.sent / 100
        informations[1][6] = self.combo / 10
        informations[2][6] = self.pre_back2back
        informations[3][6] = self._attacked / GRID_DEPTH
        # informations[3][7] = self.time / MAX_TIME

        return_grids = np.concatenate((return_grids, informations), axis=0)

        return np.transpose(return_grids, (1, 0))

    def get_board(self):
        excess = len(self.grid[0]) - GRID_DEPTH
        return_grids = np.zeros(shape=(GRID_WIDTH, GRID_DEPTH), dtype=np.float32)
        
        block, px, py = self.block, self.px, self.py
        excess = len(self.grid[0]) - GRID_DEPTH
        # b = block.now_block()

        for i in range(len(self.grid)):
            return_grids[i] = np.array(self.grid[i][excess:GRID_DEPTH], dtype=np.float32)
        return_grids[return_grids > 0] = 1
        # for x in range(BLOCK_WIDTH):
        #     for y in range(BLOCK_LENGTH):
        #         if b[x][y] > 0:
        #             if -1 < px + x < 10 and -1 < py + y - excess < 20:
        #                 return_grids[px + x][py + y - excess] = 0.5


        return return_grids

    def get_maximum_height(self):
        max_height = 0
        for i in range(0, len(self.grid)):  # Select a column
            for j in range(0, len(self.grid[0])):  # Search down starting from the top of the board
                if int(self.grid[i][j]) > 0:  # Is the cell occupied?
                    max_height = max(max_height, len(self.grid[0]) - j) 
                    break
        return max_height

    def reset_pos(self):
        self.px = 4
        self.py = -2 + len(self.grid[0]) - GRID_DEPTH

    def get_id(self):
        return self.player.id

    def add_attacked(self, attacked):
        if attacked > 0 and self._attacked == 0:
            self.emit_event("warning")
        self._attacked += attacked
        self._attacked = min(self._attacked, GRID_DEPTH)

    def arm_bomb(self):
        """Legacy compatibility: original bomb garbage is AUTOMATIC, not a key item."""
        return False

    def explode_bomb(self):
        """Deprecated manual 3x3 ability; intentionally disabled."""
        return 0

    def detonate_contact_bombs(self, placed_cells):
        """Clear full bomb garbage rows under the piece that just locked.

        A resting tetromino must touch the bomb in the square immediately
        beneath one of its minos. Two or more vertically aligned bomb cells
        chain downward together; the second and later rows award one attack
        line each. Every removed row collapses the board from above.
        """
        self.last_bomb_rows = 0
        self.last_blast = []
        self.last_bomb_removed = 0
        self.bomb_chain_count = 0
        if not self.bombs_enabled:
            return 0
        height = len(self.grid[0])
        touched = set()
        for x, y in placed_cells:
            if 0 <= x < GRID_WIDTH and 0 <= y + 1 < height and self.grid[x][y + 1] == BOMB_CELL:
                touched.add((x, y + 1))
        if not touched:
            return 0
        rows = set()
        for x, first_y in touched:
            y = first_y
            while y < height and self.grid[x][y] == BOMB_CELL:
                rows.add(y)
                y += 1
        for y in sorted(rows):
            # Row is bomb garbage, never a 3x3 deletion of player blocks.
            for x in range(GRID_WIDTH):
                del self.grid[x][y]
                self.grid[x].insert(0, 0)
        self.last_bomb_rows = self.bomb_chain_count = len(rows)
        # The overlay uses the original contact coordinates for a blast burst.
        self.last_blast = sorted(touched) + [(x, y) for y in rows for x in range(GRID_WIDTH)]
        self.last_bomb_removed = GRID_WIDTH * len(rows)
        self.emit_event("bomb_explode")
        if len(rows) > 1:
            self.emit_event("bomb_chain")
        return len(rows)

    def _modern_step_side(self, action):
        dx = 1 if action == "right" else -1
        if not collide(self.grid, self.block, self.px + dx, self.py):
            self.px += dx
            self._modern_last_rotation = False
            self.tspin = 0
            self.emit_event("move")
            return True
        return False

    def _modern_step_down(self):
        if not collideDown(self.grid, self.block, self.px, self.py):
            self.py += 1
            self._modern_last_rotation = False
            self.tspin = 0
            self.LAST_FALL_DOWN_TIME = 0
            self.emit_event("soft_drop")
            return True
        return False

    def _modern_trigger(self, evt):
        if evt.type == pygame.KEYUP:
            self._held_actions.discard(evt.key)
            for direction in ("left", "right", "down"):
                held = self._direction_keys[direction]
                if evt.key in held:
                    held.remove(evt.key)
                    if direction == self._horizontal_active and not held:
                        other = "left" if direction == "right" else "right"
                        self._horizontal_active = other if self._direction_keys[other] else None
                        self._horizontal_elapsed_ms = 0.0
                        self._horizontal_repeats = 0
                        if self._horizontal_active:
                            self._modern_step_side(self._horizontal_active)
                    if direction == "down" and not held:
                        self._down_elapsed_ms = 0.0
            self.pressedLeft = bool(self._direction_keys["left"])
            self.pressedRight = bool(self._direction_keys["right"])
            self.pressedDown = bool(self._direction_keys["down"])
            return
        if evt.type != pygame.KEYDOWN:
            return
        if evt.key in self._held_actions:
            return  # Ignore OS key-repeat; pieces drop only once per press.
        if not any(self.player.is_pressed(action, evt.key) for action in
                   ("left", "right", "down", "rotate_right", "rotate_left",
                    "drop", "hold")):
            return
        self._held_actions.add(evt.key)
        for direction in ("left", "right", "down"):
            if self.player.is_pressed(direction, evt.key):
                self._direction_keys[direction].add(evt.key)
                if direction == "down":
                    self.pressedDown = True
                    self._down_elapsed_ms = 0.0
                    self._modern_step_down()
                else:
                    setattr(self, "pressed" + direction.capitalize(), True)
                    self._horizontal_active = direction
                    self._horizontal_elapsed_ms = 0.0
                    self._horizontal_repeats = 0
                    self._modern_step_side(direction)
                return

        direction = (1 if self.player.is_pressed("rotate_right", evt.key) else
                     -1 if self.player.is_pressed("rotate_left", evt.key) else 0)
        if direction:
            self.block, self.px, self.py, rotated = rotate_srs(
                self.grid, self.block, self.px, self.py, direction)
            self._modern_last_rotation = rotated
            self.tspin = 0  # Re-evaluate 3-corner condition only when locking.
            if rotated:
                self.emit_event("rotate")
            return
        if self.player.is_pressed("drop", evt.key):
            self.py += hardDrop(self.grid, self.block, self.px, self.py)
            self.LAST_FALL_DOWN_TIME = FALL_DOWN_FREQ
            self.emit_event("hard_drop")
            return
        if self.player.is_pressed("hold", evt.key):
            if not self.isholded:
                self.block, self.held = hold(self.block, self.held, self.buffer)
                self.held.reset()
                self.reset_pos()
                self._check_spawn_topout()
                self.isholded = 1
                self._modern_last_rotation = False
                self.tspin = 0
                self.emit_event("hold")
            return

    def sync_single_space(self, pressed):
        """Backwards-compatible method for the held-Space regression tests."""
        if not self.modern_controls:
            return
        self._sync_one_bound_key(pygame.K_SPACE, bool(pressed))

    def _sync_one_bound_key(self, key, pressed):
        """Reconcile Pygame's physical key state with the keyboard event cache.

        The map chooser can consume KEYDOWN. Some window managers can also
        miss KEYUP during focus changes. Both must be handled here so that
        actions always work from the first frame and never remain stuck.
        """
        held = key in self._held_actions
        if pressed and not held:
            self._modern_trigger(type("KeyEvent", (), {"type": pygame.KEYDOWN,
                                                      "key": key})())
        elif not pressed and held:
            self._modern_trigger(type("KeyEvent", (), {"type": pygame.KEYUP,
                                                      "key": key})())
        elif pressed and held:
            # release_movement() clears held directions when pause/focus is
            # lost, but deliberately retains the Space/rotate key edge so
            # resuming while holding them does NOT trigger another action.
            for direction in ("left", "right", "down"):
                if self.player.is_pressed(direction, key) and key not in self._direction_keys[direction]:
                    self._direction_keys[direction].add(key)
                    if direction == "down":
                        self.pressedDown = True
                        self._down_elapsed_ms = 0.0
                    else:
                        setattr(self, "pressed" + direction.capitalize(), True)
                        self._horizontal_active = direction
                        self._horizontal_elapsed_ms = 0.0

    def sync_pressed_keys(self, physical_keys):
        """Recover all human control keys, not only Space, from real SDL state.

        Input events still apply immediately. This is an additional guard
        against swallowed events and layout transitions. A pressed key is
        dispatched once; directional auto-repeat stays in _modern_move().
        """
        if not self.modern_controls:
            return
        # Direction and rotation keys come before hard drop if a user happens
        # to hold multiple keys while starting a match.
        actions = ("left", "right", "down", "rotate_left",
                   "rotate_right", "hold", "drop")
        ordered = []
        for action in actions:
            value = getattr(self.player, action)
            if value is None:
                continue
            codes = value if isinstance(value, (tuple, list, set)) else (value,)
            for code in codes:
                if code not in ordered:
                    ordered.append(code)
        for code in ordered:
            try:
                pressed = bool(physical_keys[code])
            except (IndexError, KeyError, TypeError, ValueError):
                # Some backends do not expose every special key in the array.
                # KEYDOWN/KEYUP events still work for those keys.
                continue
            self._sync_one_bound_key(code, pressed)

    def _modern_move(self, elapsed_ms=10.0):
        dt = max(0.0, min(100.0, float(elapsed_ms)))
        action = self._horizontal_active
        if action and self._direction_keys[action]:
            before = self._horizontal_elapsed_ms
            self._horizontal_elapsed_ms += dt
            # DAS/ARR are time-based. Catch up if the renderer
            # briefly falls behind, rather than slowing control speed.
            def ticks(duration):
                return 0 if duration < self.das_ms else 1 + int((duration - self.das_ms) / self.arr_ms)
            count = min(5, ticks(self._horizontal_elapsed_ms) - ticks(before))
            for _ in range(count):
                if not self._modern_step_side(action):
                    break
        if self._direction_keys["down"]:
            before = self._down_elapsed_ms
            self._down_elapsed_ms += dt
            count = min(8, int(self._down_elapsed_ms / self.soft_drop_ms) - int(before / self.soft_drop_ms))
            for _ in range(count):
                if not self._modern_step_down():
                    break

    def _modern_tspin_at_lock(self):
        if self.block.block_type() != "T" or not self._modern_last_rotation:
            return False
        # T pivot is at local (1,2) in the project's [x][y] layouts.
        cx, cy = self.px + 1, self.py + 2
        occupied = 0
        for x in (cx - 1, cx + 1):
            for y in (cy - 1, cy + 1):
                if not (0 <= x < GRID_WIDTH and 0 <= y < len(self.grid[0])) or self.grid[x][y] > 0:
                    occupied += 1
        return occupied >= 3

    def natural_down(self):
        if self.LAST_NATRUAL_FALL_TIME >= NATRUAL_FALL_FREQ:
            if collideDown(self.grid, self.block, self.px, self.py) == False:
                self.stopcounter = 0
                # self.block.move_down()
                self.py += 1
                if self.modern_controls:
                    self._modern_last_rotation = False
                # pass

            self.LAST_NATRUAL_FALL_TIME = 0
        # else:
        #     self.natural_down_counter += 1

    def trigger(self, evt):
        if self.modern_controls:
            self._modern_trigger(evt)
            return
        if evt.type == pygame.KEYDOWN:
            if self.player.is_pressed("rotate_right", evt.key) and self.LAST_ROTATE_TIME >= ROTATE_FREQ:
                previous = self.block.current_shape_id, self.px, self.py
                self.block, self.px, self.py, self.tspin = rotate(
                    self.grid, self.block, self.px, self.py, _dir=1)
                self.LAST_ROTATE_TIME = 0
                if previous != (self.block.current_shape_id, self.px, self.py):
                    self.emit_event("rotate")

            if self.player.is_pressed("rotate_left", evt.key) and self.LAST_ROTATE_TIME >= ROTATE_FREQ:
                previous = self.block.current_shape_id, self.px, self.py
                self.block, self.px, self.py, self.tspin = rotate(
                    self.grid, self.block, self.px, self.py, _dir=-1)
                self.LAST_ROTATE_TIME = 0
                if previous != (self.block.current_shape_id, self.px, self.py):
                    self.emit_event("rotate")

            if self.player.is_pressed("drop", evt.key):
                self.py += hardDrop(self.grid, self.block, self.px, self.py)
                self.LAST_FALL_DOWN_TIME = FALL_DOWN_FREQ
                self.emit_event("hard_drop")


            if self.player.is_pressed("hold", evt.key) and not self.isholded:
                self.block, self.held = hold(self.block, self.held, self.buffer)
                self.held.reset()
                self.reset_pos()
                self.isholded = 1
                self.emit_event("hold")

            if self.player.is_pressed("right", evt.key):
                self.pressedRight = True
            if self.player.is_pressed("left", evt.key):
                self.pressedLeft = True
            if self.player.is_pressed("down", evt.key):
                self.pressedDown = True

        if evt.type == pygame.KEYUP:
            if self.player.is_pressed("right", evt.key):
                self.pressedRight = False
            if self.player.is_pressed("left", evt.key):
                self.pressedLeft = False
            if self.player.is_pressed("down", evt.key):
                self.pressedDown = False

    def release_movement(self):
        """Do not keep moving after releasing keys during a game pause."""
        if self.modern_controls:
            # Preserve one-shot key edges through pause, so continuing while
            # physically holding Space cannot accidentally drop a new piece.
            for keys in self._direction_keys.values():
                keys.clear()
            self._horizontal_active = None
            self._horizontal_elapsed_ms = 0.0
            self._down_elapsed_ms = 0.0
        self.pressedRight = self.pressedLeft = self.pressedDown = False

    # move function
    # when respective buttons are pressed
    def move(self, elapsed_ms=10.0):
        if self.modern_controls:
            self._modern_move(elapsed_ms)
            return
        # if keys[self.right]:
        if self.pressedRight and self.LAST_MOVE_SHIFT_TIME > MOVE_SHIFT_FREQ:
            if collideRight(self.grid, self.block, self.px, self.py) == False:    
                self.LAST_MOVE_SHIFT_TIME = 0

                # self.block.move_right()
                self.px += 1
                self.emit_event("move")

        if self.pressedLeft and self.LAST_MOVE_SHIFT_TIME > MOVE_SHIFT_FREQ:
            if collideLeft(self.grid, self.block, self.px, self.py) == False:
                self.LAST_MOVE_SHIFT_TIME = 0

                # self.block.move_left()
                self.px -= 1
                self.emit_event("move")

        if self.pressedDown and self.LAST_MOVE_DOWN_TIME > MOVE_DOWN_FREQ:
            if collideDown(self.grid, self.block, self.px, self.py) == False:
                self.LAST_MOVE_DOWN_TIME = 0
                # self.stopcounter = 0

                # self.block.move_down()
                self.py += 1
                self.emit_event("soft_drop")

    def check_fallen(self):
        if collideDown(self.grid, self.block, self.px, self.py) == True:
            # self.stopcounter += 1
            if self.LAST_FALL_DOWN_TIME >= FALL_DOWN_FREQ:
                if self.modern_controls:
                    self.tspin = int(self._modern_tspin_at_lock())
                self._is_fallen = 1
                placed = self.block.return_pos(self.px, self.py)
                if self.modern_controls and any(y < len(self.grid[0]) - GRID_DEPTH for x, y in placed):
                    # Top-out also occurs when a piece locks outside the
                    # visible playfield, even if it does not fill row 0.
                    self.topped_out = True
                put_block_in_grid(self.grid, self.block, self.px, self.py)
                self.emit_event("lock")
                self.detonate_contact_bombs(placed)
                # print("fallen")

                return True

        else:
            self._is_fallen = 0
            # self.stopcounter = 0
            self.LAST_FALL_DOWN_TIME = 0

        return False

        # if self.stopcounter >= COLLIDE_DOWN_COUNT: # adds adequate delay  
        #     if block_in_grid(self.grid, self.block):
        #         self.is_fallen = 1
        #         return True

        # return False

    # compute the scores when the block is fallen down.
    # return True if the computation is done.

    def compute_scores(self, cleared, combo, tspin, tetris, pre_back2back):

        if cleared == 0:
            scores = 0
        else:
            scores = cleared if cleared == 4 else cleared - 1

            # scores from combos
            if combo > 0:
                if combo <= 8:
                    combo_scores = int((combo + 1) / 2)
                else: combo_scores = 4
            else:
                combo_scores = 0

            scores += combo_scores

            # 2 line tspin 
            if tspin and cleared == 2:
                scores += 3

            if pre_back2back:
                if tspin or tetris:
                    scores += 2

        return scores

    def clear(self):

        cleared = 0

        # self.tetris = 0

        is_combo = 0
        self.last_cleared_rows = []

        for y in reversed(range(GRID_DEPTH)):
            y = -(y + 1)
            row = 0 # starts checking from row zero
            for x in range(GRID_WIDTH):
                if self.grid[x][y] > 0 and self.grid[x][y] < 8:
                    row += 1

            if row == GRID_WIDTH:
                self.last_cleared_rows.append((y + len(self.grid[0])) % len(self.grid[0]))
                cleared += 1
                for i in range(GRID_WIDTH):
                    del self.grid[i][y] # deletes cleared lines
                    self.grid[i] = [0] + self.grid[i] # adds a row of zeros to the grid
                        
        if cleared >= 1: # for sending lines
            self.combo += 1
            if cleared == 4: # a tetris
                self.tetris = 1
            else:
                self.tetris = 0

            self.pre_back2back = self.now_back2back   
        else:
            # Bomb-only detonations preserve the current Combo/B2B streak.
            # An ordinary non-clearing lock still breaks the Combo.
            if not self.last_bomb_rows:
                self.combo = -1
            self.tetris = 0

        # compute scores
        scores = self.compute_scores(cleared, self.combo, self.tspin, self.tetris, self.pre_back2back)

        if cleared >= 1:
            if self.tspin or self.tetris:
                print("next backtoback")
                self.now_back2back = 1
            else:
                self.now_back2back = 0
        # print(self.pre_back2back, self.now_back2back)
        # self.tspin = 0

        self.cleared = cleared
        self.total_lines += cleared
        # Facebook bomb-chain bonus: 1 bomb = 0 sent, 2 = 1, 3 = 2.
        # It stacks with ordinary line clears, then nets against incoming.
        bomb_bonus = max(0, self.last_bomb_rows - 1)
        total_attack = scores + bomb_bonus
        # First use outgoing power to cancel pending incoming garbage; only
        # the remainder can be sent to the opponent (never double spend).
        incoming = self._attacked
        self.garbage_cancelled = min(incoming, total_attack)
        # Preserve legacy Gym scoring when bombs are off. Human bomb battles
        # counter pending garbage first and send only the remainder.
        self.attack_outgoing = max(0, total_attack - incoming) if self.bombs_enabled else scores
        self.sent += self.attack_outgoing
        real_attacked = max(0, incoming - total_attack)
        self.build_garbage(self.grid, real_attacked)
        self._attacked = 0
        if self.garbage_cancelled:
            self.emit_event("garbage_cancel")

        if cleared == 4:
            self.emit_event("tetris")
        elif cleared:
            self.emit_event("line_clear")
        if self.combo > 0 and cleared:
            self.emit_event("combo")
        if cleared and self.tspin:
            self.emit_event("tspin")
        if cleared and self.pre_back2back and (self.tspin or self.tetris):
            self.emit_event("back_to_back")
        if cleared and all(cell == 0 for col in self.grid for cell in col):
            self.perfect_clears += 1
            self.emit_event("perfect_clear")

        return scores

        # return scores

    def check_KO(self):
        if self.garbage_overflow or getattr(self, "topped_out", False):
            return True
        is_ko = False
        #if your grid hits the top ko = true
        excess = len(self.grid[0]) - GRID_DEPTH

        for i in range(GRID_WIDTH):
            if self.grid[i][excess] > 0:
                is_ko = True
                break

        return is_ko
        
    def clear_garbage(self):
        """Remove complete garbage rows on KO (including bomb garbage)."""
        height = len(self.grid[0])
        garbage_rows = [y for y in range(height)
                        if any(self.grid[x][y] in (GARBAGE_CELL, BOMB_CELL)
                               for x in range(GRID_WIDTH))]
        # Remove from the highest row first; inserting a new row at the top
        # otherwise shifts unprocessed rows and leaves ghost garbage behind.
        for y in garbage_rows:
            for x in range(GRID_WIDTH):
                del self.grid[x][y]
                self.grid[x].insert(0, 0)
        self.garbage_overflow = False

    def build_garbage(self, grid, attacked, bomb_columns=None):
        """Add bottom garbage rows (fixed board height, preserving collisions).

        Bombs are the default 2P garbage type. Each pair of lines from one
        attack uses the same column for possible vertical chain detonation.
        Explicit columns make replays and unit tests deterministic.
        """
        count = min(max(0, int(attacked)), GRID_DEPTH)
        if bomb_columns is not None and len(bomb_columns) != count:
            raise ValueError("bomb_columns length must equal attacked rows")
        last_column = None
        height = len(grid[0])
        for index in range(count):
            if self.bombs_enabled:
                column = (int(bomb_columns[index]) if bomb_columns is not None else
                          last_column if index % 2 == 1 else random.randrange(GRID_WIDTH))
                if not 0 <= column < GRID_WIDTH:
                    raise ValueError("Invalid bomb column: {}".format(column))
                last_column = column
            else:
                column = None
            if any(grid[x][0] for x in range(GRID_WIDTH)):
                self.garbage_overflow = True
            for x in range(GRID_WIDTH):
                del grid[x][0]
                grid[x].append(BOMB_CELL if x == column else GARBAGE_CELL)
        assert all(len(column) == height for column in grid)

    def check_combo(self):
        return self.combo - self.oldcombo >= 1

    def new_block(self):
        self.block = self.buffer.new_block()
        if self.modern_controls:
            self._modern_last_rotation = False
        self.reset_pos()
        self._check_spawn_topout()
        self.isholded = 0
        self.tspin = 0
        self.last_bomb_rows = 0
        self.bomb_chain_count = 0
        self._n_used_block += 1

    def update_ko(self):
        self.oldko = self._KO
        self._KO += 1

    def update_combo(self):
        self.oldcombo = self.combo
        self.combo += 1
