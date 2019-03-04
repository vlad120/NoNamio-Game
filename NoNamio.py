import pygame
import sys
from json import loads, dumps
from random import choice

NEON = (57, 255, 20)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
ORANGE = (255, 165, 0)


def load_image(name, color_key=None):
    fullname = 'data/' + name
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)

    if color_key:
        if color_key is -1:
            color_key = image.get_at((0, 0))
        image.set_colorkey(color_key)
    return image


def load_level(number):
    with open('data/levels.txt', 'r') as mapFile:
        mapFile = "\n".join(list(line.strip() for line in mapFile)).strip()
        mapFile = [[j for j in i] for i in mapFile.split("level")[number].strip().split('\n')]
    return mapFile


class Tile(pygame.sprite.Sprite):
    name = "tile"

    def __init__(self, game, tile_type, pos_x, pos_y, *groups, name=None):
        super().__init__(game.all_sprites, *groups)
        self.image = game.images[tile_type]
        self.rect = self.image.get_rect().move(game.tile_width * pos_x,
                                               game.tile_height * pos_y)
        self.mask = pygame.mask.from_surface(self.image)
        if name:
            self.name = name


class Enemy(pygame.sprite.Sprite):
    name = "enemy"

    def __init__(self, game, pos_x, pos_y):
        super().__init__(game.all_sprites, game.danger_group)
        self.image = game.images["enemy"]
        self.rect = self.image.get_rect().move(game.tile_width * pos_x,
                                               game.tile_height * pos_y)
        self.game = game
        self.direction = 1

    def update(self, *args):
        if pygame.sprite.spritecollide(self, self.game.block_group, False):
            self.direction *= -1
        else:
            # проверка на пустоту под ним
            for i in range(4):
                t = (self.rect.width - i) * self.direction
                self.rect.y += 10
                self.rect.x += t
                if not pygame.sprite.spritecollide(self, self.game.block_group, False):
                    self.direction *= -1
                self.rect.y -= 10
                self.rect.x -= t
        self.rect.x += self.direction * 4


class Coin(pygame.sprite.Sprite):
    name = "coin"

    def __init__(self, game, x, y):
        super().__init__(game.all_sprites)
        self.frames = []
        self.cut_sheet(load_image("coins_animate.png"))
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.rect.move(x * game.tile_width + (game.tile_width - self.rect.width) // 2,
                                   y * game.tile_height + game.tile_height - self.rect.height)
        self.mask = pygame.mask.from_surface(self.image)

    def cut_sheet(self, sheet):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // 8, sheet.get_height() // 3)
        for j in range(3):
            for i in range(8):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(frame_location, self.rect.size)))

    def update(self, *args):
        self.cur_frame = (self.cur_frame + 1) % len(self.frames)
        self.image = self.frames[self.cur_frame]


class Player(pygame.sprite.Sprite):
    name = "player"

    def __init__(self, game, x, y):
        super().__init__(game.all_sprites)
        self.frames1 = []
        self.frames2 = []
        self.cut_sheet(load_image('heroR.png'), load_image('heroL.png'))
        self.cur_frame = 0
        self.image = self.frames1[self.cur_frame]
        self.rect = self.rect.move(x + (game.tile_width - self.rect.w) // 2, y)
        self.mask = pygame.mask.from_surface(self.image)
        self.game = game
        self.moving_y = (0, 0)
        self.jumping = False
        self.moving_x = (0, 0)
        self.blink = 0

    def cut_sheet(self, sheet1, sheet2):
        self.rect = pygame.Rect(0, 0, sheet1.get_width() // 4, sheet1.get_height() // 4)
        for j in range(4):
            for i in range(4):
                if j * 4 + i < 13:
                    frame_location = (self.rect.w * i, self.rect.h * j)
                    self.frames1.append(sheet1.subsurface(pygame.Rect(frame_location, self.rect.size)))
                    self.frames2.append(sheet2.subsurface(pygame.Rect(frame_location, self.rect.size)))

    def next_pic(self, direction):
        if self.blink % 8 == 0:
            if direction > 0:
                self.cur_frame = (self.cur_frame + 1) % len(self.frames1)
                self.image = self.frames1[self.cur_frame]
            elif direction < 0:
                self.cur_frame = (self.cur_frame + 1) % len(self.frames2)
                self.image = self.frames2[self.cur_frame]

    def move(self, x, y):
        if x:
            self.moving_x = [x, 5]
        if y and not self.jumping:
            self.moving_y = [y, 120]

    def check_collides(self, group, check_win=False):
        if check_win:
            for sprite in pygame.sprite.spritecollide(self, group, False):
                if pygame.sprite.collide_mask(self, sprite):
                    if sprite.name == "flag":
                        return True
                    elif sprite.name == "coin":
                        self.game.data["coins"] += choice((5, 10, 15, 20))
                        sprite.kill()
            return False
        else:
            for sprite in pygame.sprite.spritecollide(self, group, False):
                if pygame.sprite.collide_mask(self, sprite):
                    if sprite.name in ("enemy", "thorns") and not self.blink:
                        self.game.lifes -= 1
                        if self.game.lifes:
                            self.blink = 50
                    return True
            return False

    def update(self, *args):
        if self.check_collides(self.game.all_sprites, check_win=True) and not self.blink:
            self.game.victory = True
            return True

        if self.blink:
            self.blink -= 1
            if self.blink % 4 == 0:
                self.image = self.game.images['empty'] if self.blink % 8 else self.frames1[self.cur_frame]
        else:
            self.check_collides(self.game.danger_group)

        # ход по горизонтали
        i = 0
        for i in range(int(self.moving_x[1] * (1.5 if self.jumping else 1))):
            self.rect.x += self.moving_x[0]
            if self.check_collides(self.game.block_group):
                self.rect.x -= self.moving_x[0]
                break
        if i:
            self.game.player.next_pic(self.moving_x[0])
        self.moving_x = [0, 0]

        for pic in self.game.game_fon:
            pic.rect.x += self.moving_x[0] * 2

        # движение по вертикали
        if self.moving_y[1] > 0:
            for i in range(8):
                self.rect.y += self.moving_y[0]
                if self.check_collides(self.game.tiles_group):
                    self.rect.y -= self.moving_y[0]
                    self.moving_y = [0, 0]
                    return False
            self.jumping = True
            self.moving_y[1] -= 8
            for pic in self.game.game_fon:
                pic.rect.y += 2
        else:  # падение
            for i in range(10):
                self.rect.y += 1
                if self.check_collides(self.game.block_group):
                    self.rect.y -= 1
                    self.jumping = False
                    return False
            for pic in self.game.game_fon:
                pic.rect.y -= 2


class MySprite(pygame.sprite.Sprite):
    name = "other"

    def __init__(self, game, img, x, y, abs_coords=False):
        super().__init__(game.all_sprites)
        self.image = load_image(img) if type(img) == str else img
        if abs_coords:
            self.rect = self.image.get_rect().move(x, y)
        else:
            self.rect = self.image.get_rect().move(x * game.tile_width, y * game.tile_height)


class Camera:
    # зададим начальный сдвиг камеры
    def __init__(self, game):
        self.dx = 0
        self.dy = 0
        self.WIDTH = game.WIDTH
        self.HEIGHT = game.HEIGHT

    # сдвинуть объект obj на смещение камеры
    def apply(self, obj):
        obj.rect.x += self.dx
        if obj.name != "other":
            obj.rect.y += self.dy

    # позиционировать камеру на объекте target
    def update(self, target):
        self.dx = self.WIDTH // 2 - (target.rect.x + target.rect.w // 2)
        self.dy = self.HEIGHT // 2 - (target.rect.y + target.rect.h // 2)


class Game:
    def __init__(self, width, height):
        pygame.init()
        pygame.display.set_caption("NoNamio")

        self.SIZE = self.WIDTH, self.HEIGHT = width, height
        self.screen = pygame.display.set_mode(self.SIZE)

        self.clock = pygame.time.Clock()

        pygame.mixer.pre_init(frequency=44100)
        self.sounds = {
            "transition": pygame.mixer.Sound('data/transition.wav')
        }

        self.images = {
            'box': load_image('box.png'),
            'ground': load_image('ground.png'),
            'thorns': load_image('thorns.png'),
            'step': load_image('step.png'),
            'enemy': load_image('ghost.png'),
            'flag': load_image('flag.png'),
            'empty': load_image('empty.png'),
            'pause': load_image('pause.png'),
            'pause_fon': load_image('pause_fon.png'),
            'coins': load_image('coins.png'),
            'locked_level': load_image('locked_level.png'),
            'sound': load_image('sound.png'),
            'music': load_image('music.png'),
            'non_sound': load_image('non_sound.png'),
            'non_music': load_image('non_music.png')
        }

        self.tile_width = self.tile_height = 70

        try:
            self.data = loads(open('data/data.json', 'rb').read())
        except Exception:
            self.null_progress()

        self.start_ui()

    def start_ui(self):
        while self.menu():
            pass

    def menu(self):
        self.play_fon_music(False)
        self.render_menu_fon()
        self.render_text("NoNamio".ljust(14), self.WIDTH // 2, 80,
                         size=120, color=NEON, italic=True, u=True)

        self.screen.blit(self.images["coins"], (20, 140))

        self.render_text(str(self.data["coins"]), 70, 150,
                         size=40, color=WHITE, italic=True)

        # словарь координат элементов и их функций
        all_elements = dict()
        all_elements.update(self.render_bar())
        all_elements.update(self.render_sound_button())
        all_elements.update(self.render_music_button(do=False))

        # рисуем уровни
        offset = 30  # для параллелепипеда
        space = 10  # между рамками
        frame_width = 50  # размер рамки и цифр
        start_x = self.WIDTH // 2 - ((frame_width + offset + space) * len(self.data["levels"]) // 2) + offset
        start_y = 250
        for i in range(8):
            # если открыт
            if self.data["levels"][str(i + 1)] in (0, "ok"):
                # рисуем номер
                n = str(i + 1)
                x1 = start_x + i * (frame_width + space + offset) + frame_width // (3 * len(n))
                y1 = start_y + frame_width // 10
                rect = self.render_text(n, x1, y1, size=frame_width, color=WHITE, italic=True)
                if self.data["levels"][n] == "ok":
                    self.render_text("v", rect.x + rect.width, y1 - frame_width // 5, size=frame_width, color=RED)
            else:
                # иначе рисуем замок
                x1 = (start_x + i * (frame_width + space + offset) +
                      (frame_width - self.images["locked_level"].get_width()) // 2)
                y1 = start_y + frame_width // 10
                self.screen.blit(self.images["locked_level"], (x1, y1))

            rect = pygame.Rect(start_x + i * (frame_width + space + offset), 250, 50, 50)
            # добовляем координаты крайних точек в словарь
            all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.width)] = (self.start_game, i + 1)
            # обрамляем
            self.frame_obj(rect, offset=offset)

        # рисуем кнопки:
        # задаем шаблон для всех рамок, нарисовав первую
        rect = self.render_text("New Game", None, 350, size=80, color=BLUE, center=True)
        self.frame_obj(rect)  # обрамляем
        # добовляем в словарь
        all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)] = self.new_game

        for new_y, name, func in ((435, "Store", self.store),
                                  (520, "Quit", self.close),
                                  (605, "Help", self.help_info)):
            rect.y = new_y  # снижаем рамку
            self.render_text(name, None, new_y, size=80, color=BLUE, center=True)
            self.frame_obj(rect)
            all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)] = func

        pygame.display.flip()  # обновляем дисплей

        # обрабатываем события
        # т.к. меню статичное, ставим наименьший fps, чтобы не нагружать процессор
        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if not self.close():
                        self.start_ui()
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    # нахдим, попала ли мышь в область
                    # функционирующих элементов
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()  # звуковой переход
                        element = all_elements[element[0]]
                        # вызываем функцию кнопки, если она есть
                        if type(element) == tuple:
                            # если есть аргумент, передаем его
                            element[0](element[1])
                            return True
                        elif callable(element):
                            element()
                            return True
            self.clock.tick(fps)

    def start_game(self, level):
        # проверка на доступность уровня
        if self.data["levels"][str(level)] not in (0, "ok"):
            return False

        self.play_fon_music(True)

        # группы спрайтов
        self.all_sprites = pygame.sprite.Group()
        self.tiles_group = pygame.sprite.Group()
        self.block_group = pygame.sprite.Group()
        self.danger_group = pygame.sprite.Group()

        self.level_map = load_level(level)

        # создание фона на всю ширину карты
        self.game_fon = []
        w = 1800
        h = 1081
        for i in range(len(self.level_map[0]) // 30 + 1):
            self.game_fon.append(MySprite(self, 'game_fon.png' if i % 2 else 'game_fon_reflected.png',
                                          i * w, -h // 3, abs_coords=True))

        self.generate_level()
        self.camera = Camera(self)

        MySprite(self, self.images["pause"], 10, 10, abs_coords=True)

        MySprite(self, self.images["coins"], self.WIDTH - 270, 17, abs_coords=True)

        self.lifes = 3
        self.victory = False

        keys = {32:  [False, (0, -1)],  # UP
                119: [False, (0, -1)],
                273: [False, (0, -1)],

                275: [False, (1, 0)],   # LEFT
                100:  [False, (1, 0)],

                276: [False, (-1, 0)],  # RIGHT
                97: [False, (-1, 0)]}

        fps = 50
        running = True
        while running:
            # обработка событий
            for event in pygame.event.get():
                # корректный выход
                if event.type == pygame.QUIT:
                    self.close()

                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.play_sound()
                    x, y = event.pos
                    if 10 <= x <= 60 and 10 <= y <= 60:
                        answ = self.pause()
                        if answ == "RESTART":
                            self.all_sprites.clear(self.screen, self.images['pause_fon'])
                            self.start_game(level)
                            return False
                        elif answ == "Menu":
                            return False

                elif event.type == pygame.KEYDOWN:
                    if event.key in keys:
                        keys[event.key][0] = True
                        if keys[275][0] and keys[276][0]:
                            keys[275 if event.key == 276 else 276][0] = False
                elif event.type == pygame.KEYUP:
                    if event.key in keys:
                        keys[event.key][0] = False

            # проверка нажатых кнопок
            for k in keys:
                if keys[k][0]:
                    self.player.move(*keys[k][1])

            # обновляем спрайты
            self.all_sprites.update()
            # изменяем ракурс камеры
            self.camera.update(self.player)
            # # обновляем положение всех спрайтов
            for sprite in self.all_sprites:
                if sprite.name != "other":
                    self.camera.apply(sprite)
            # перерисовываем экран со спрайтами
            self.screen.fill((0, 0, 0))
            self.all_sprites.draw(self.screen)

            # отображение жизней
            for i in range(self.lifes):
                pygame.draw.circle(self.screen, RED, (self.WIDTH - 40 - i * 30, 40), 10)

            # отображение денег
            self.render_text(str(self.data["coins"]), self.WIDTH - 220, 27,
                             size=40, color=BLACK, italic=True)

            if self.victory:
                answ = self.win(level)
                if answ in ("RESTART", "NEXT"):
                    self.all_sprites.clear(self.screen, self.images['pause_fon'])
                    self.start_game(level + (1 if answ == "NEXT" else 0))
                return True

            if self.lifes == 0:
                answ = self.lose()
                if answ == "RESTART":
                    self.all_sprites.clear(self.screen, self.images['pause_fon'])
                    self.start_game(level)
                return False

            pygame.display.flip()
            self.clock.tick(fps)

    def pause(self):
        self.screen.blit(self.images['pause_fon'], (0, 0))
        all_elements = {(220, 230, 420, 430): "RESTART",
                        (600, 230, 750, 4300): "CONTINUE"}

        self.screen.blit(load_image('restart.png'), (220, 230))
        pygame.draw.polygon(self.screen, NEON, [(600, 230), (750, 330), (600, 430)])

        all_elements.update(self.render_sound_button(y=230))
        all_elements.update(self.render_music_button(y=310))
        all_elements.update(self.render_bar("pause"))

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        element = all_elements[element[0]]
                        if element in ("RESTART", "CONTINUE", "Menu"):
                            return element
                        elif callable(element):
                            element()
            self.clock.tick(fps)

    def win(self, level):
        self.next_level = 0

        self.data["levels"][str(level)] = "ok"  # уровень пройден
        if level < len(self.data["levels"]):
            # если следующий уровень бесплатный, разблокируем
            if self.data["levels"][str(level + 1)] in (-1, 0):
                self.data["levels"][str(level + 1)] = 0
                self.next_level = 1
        else:
            # если уровни закончились
            self.next_level = -1

        # размер вознаграждения
        coins = choice(range(level * 10, level * 15 + 1, 5))
        self.data["coins"] += coins

        self.screen.blit(self.images['pause_fon'], (0, 0))
        all_elements = dict()

        all_elements.update(self.render_bar("Win"))
        all_elements.update(self.render_sound_button())
        all_elements.update(self.render_music_button())

        if self.next_level == 1:
            self.screen.blit(load_image('restart.png'), (220, 230))
            self.screen.blit(load_image('next.png'), (600, 230))
            all_elements.update({(220, 230, 420, 430): "RESTART",
                                 (600, 230, 750, 430): "NEXT"})
        elif self.next_level == 0:
            # доступных уровней нет, но остались платные
            self.screen.blit(load_image('restart.png'), (400, 230))
            all_elements.update({(400, 230, 650, 430): "RESTART"})
        else:
            self.render_text("YOU WON!!!", None, 200, size=120, color=NEON, center=True)
            self.render_text("ALL LEVELS UNLOCKED!", None, 350, size=60, color=NEON, center=True)

        self.render_text("YOU GOT {} COINS!".format(coins), self.WIDTH - 400, 50,
                         size=50, color=BLUE)

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        element = all_elements[element[0]]
                        if element in ("RESTART", "NEXT", "Menu"):
                            return element
                        elif callable(element):
                            element()
            self.clock.tick(fps)

    def lose(self):
        self.screen.blit(self.images['pause_fon'], (0, 0))
        all_elements = {(400, 230, 650, 430): "RESTART"}

        all_elements.update(self.render_bar("LOSE"))
        all_elements.update(self.render_sound_button())
        all_elements.update(self.render_music_button())

        self.screen.blit(load_image('restart.png'), (400, 230))

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        element = all_elements[element[0]]
                        if element in ("RESTART", "Menu"):
                            return element
                        elif callable(element):
                            element()
            self.clock.tick(fps)

    def new_game(self):
        self.render_menu_fon()
        all_elements = dict()

        rect = self.render_text("YES", 200, 350, size=80, color=BLUE)
        self.frame_obj(rect)
        all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)] = self.null_progress

        rect.x = self.WIDTH - rect.x - rect.width
        self.render_text("NO", 700, 350, size=80, color=BLUE)
        self.frame_obj(rect)
        all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)] = None

        self.render_text("Are you sure?", None, 130, size=80,
                         color=BLUE, italic=True, center=True)
        self.render_text("All the progress will be lost!", None, 200,
                         size=80, color=BLUE, italic=True, center=True)

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        element = all_elements[element[0]]
                        if element:
                            element()
                        return False
            self.clock.tick(fps)

    def store(self):
        self.render_menu_fon()
        all_elements = dict()
        all_elements.update(self.render_bar("store"))

        ###########

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if not self.close():
                        self.start_ui()
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        if all_elements[element[0]] == "Menu":
                            return 0
            self.clock.tick(fps)

    def help_info(self):
        self.render_menu_fon()
        all_elements = dict()
        all_elements.update(self.render_bar("help"))

        help_text = [(0, "Правила игры:", 50),
                     (1, "    - Нужно то-то се-то...", 40)]
        for i, line, size in help_text:
            self.render_text(line, 50, 200 + i * 50, size=size, color=WHITE)

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if not self.close():
                        self.start_ui()
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        if all_elements[element[0]] == "Menu":
                            return 0
            self.clock.tick(fps)

    def generate_level(self):
        for y in range(len(self.level_map)):
            for x in range(len(self.level_map[0])):
                if self.level_map[y][x] == '#':
                    Tile(self, 'ground', x, y, self.block_group, self.tiles_group, name="ground")
                elif self.level_map[y][x] == '+':
                    Tile(self, 'box', x, y, self.block_group, self.tiles_group, name="box")
                elif self.level_map[y][x] == '^':
                    Tile(self, 'thorns', x, y, self.block_group, self.danger_group, name="thorns")
                elif self.level_map[y][x] == '-':
                    Tile(self, 'step', x, y, self.block_group, name='step')
                elif self.level_map[y][x] == '*':
                    Enemy(self, x, y)
                elif self.level_map[y][x] == '&':
                    Tile(self, 'flag', x, y, name="flag")
                elif self.level_map[y][x] == "$":
                    Coin(self, x, y)
                elif self.level_map[y][x] == '@':
                    player = (x, y)

        self.player = Player(self, player[0] * self.tile_width, player[1] * self.tile_height)

    def render_menu_fon(self):
        self.screen.fill((0, 0, 0))
        for x in range(0, self.WIDTH, 10):
            pygame.draw.line(self.screen, (100, 100, 100), (self.WIDTH, 0), (x, self.HEIGHT), 1)
        for y in range(0, self.HEIGHT, 10):
            pygame.draw.line(self.screen, (100, 100, 100), (self.WIDTH, 0), (0, y), 1)

    def render_text(self, text, x, y, size=30, color=BLACK, italic=False, u=False, center=False):
        font = pygame.font.Font(None, size)
        font.set_italic(italic)
        font.set_underline(u)
        string_rendered = font.render(text, 1, color)
        rect = string_rendered.get_rect()
        rect.x = x if not center else self.WIDTH // 2 - rect.width // 2
        rect.y = y
        self.screen.blit(string_rendered, rect)
        return rect

    def render_bar(self, *places):
        all_elements = dict()
        x1 = 0
        y1, y2 = 0, 105
        places = ["Menu"] + list(places)
        n = len(places)
        for i in range(n):
            rect = self.render_text(places[i], x1 + 55, 30, size=70,
                                    color=(RED if i == n - 1 else ORANGE), italic=True)
            x2 = x1 + rect.width + 55
            points = [(x1, y2), (x1 + 55, y1), (x2 + 55, y1), (x2, y2)]
            pygame.draw.polygon(self.screen, (255, 165, 0), points, 5)
            all_elements[(x1 + 55, y1, x2, y2)] = places[i]
            x1 = x2
        return all_elements

    def frame_obj(self, rect, offset=50):
        p_list = [(rect.x - offset, rect.y + rect.height),
                  (rect.x, rect.y - 5),
                  (rect.x + rect.width + offset, rect.y - 5),
                  (rect.x + rect.width, rect.y + rect.height)]
        pygame.draw.polygon(self.screen, NEON, p_list, 3)

    def render_sound_button(self, x=30, y=200):
        img = self.images['sound' if self.data["sound"] else 'non_sound']
        self.screen.blit(img, (x, y))
        return {(x, y, x + img.get_width(), y + img.get_height()): lambda: self.invert("sound")}

    def render_music_button(self, x=30, y=260, do=True):
        img = self.images['music' if self.data["music"] else 'non_music']
        self.screen.blit(img, (x, y))
        return {(x, y, x + img.get_width(), y + img.get_height()): lambda: self.invert("music", do=do)}

    def play_sound(self):
        if self.data["sound"]:
            self.sounds["transition"].play()

    def play_fon_music(self, val):
        if val and self.data["music"]:
            pygame.mixer.music.load('data/fon_music.wav')
            pygame.mixer.music.play(-1)
        else:
            pygame.mixer.music.stop()

    def invert(self, parameter, do=False):
        self.sounds['transition'].stop()
        self.data[parameter] = 0 if self.data[parameter] else 1
        if parameter == "music" and do:
            self.play_fon_music(True if self.data[parameter] else False)

    def save_progress(self):
        with open('data/data.json', 'w') as data_file:
            data_file.write(dumps(self.data))

    def null_progress(self):
        self.data = {
            "levels": {
                "1": 0,
                "2": -1,
                "3": -1,
                "4": -1,
                "5": -1,
                "6": 100,
                "7": 100,
                "8": 100
            },

            "coins": 0,

            "heroes": {
                "classic": 0,
                "red": 50,
                "blue": 50,
                "green": 100,
                "transparent": 300
            },

            "sound": 1,
            "music": 0
        }
        self.save_progress()

    def close(self):
        self.render_menu_fon()
        all_elements = dict()

        rect = self.render_text("YES", 200, 350, size=80, color=BLUE)
        self.frame_obj(rect)
        all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)] = self.terminate

        rect.x = self.WIDTH - rect.x - rect.width
        self.render_text("NO", 700, 350, size=80, color=BLUE)
        self.frame_obj(rect)
        all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)] = None

        self.render_text("Are you sure?", None, 150, size=80, color=BLUE, italic=True, center=True)

        pygame.display.flip()

        self.save_progress()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.terminate()
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        element = all_elements[element[0]]
                        if element:
                            element()
                        return 0
            self.clock.tick(fps)

    def terminate(self):
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game(1000, 700)
