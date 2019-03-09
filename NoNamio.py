"""
version 1.1

new:
    - исправлен баг с русской клавиатурой
    - добавлены некоторые комментарии, поясняющие работу кода
"""

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
            # при столкновении с блоком разворот
            self.direction *= -1
        else:
            # проверка на пустоту под ним
            for i in range(4):
                t = (self.rect.w - i) * self.direction
                self.rect.y += 10
                self.rect.x += t
                if not pygame.sprite.spritecollide(self, self.game.block_group, False):
                    self.direction *= -1
                self.rect.y -= 10
                self.rect.x -= t
        # движение на 4 пикселя
        self.rect.x += self.direction * 4


class Coin(pygame.sprite.Sprite):
    name = "coin"

    def __init__(self, game, x, y):
        super().__init__(game.all_sprites)
        self.frames = []
        self.cut_sheet(load_image("coins_animate.png"))
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.rect.move(x * game.tile_width + (game.tile_width - self.rect.w) // 2,
                                   y * game.tile_height + game.tile_height - self.rect.h)
        self.mask = pygame.mask.from_surface(self.image)

    def cut_sheet(self, sheet):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // 8, sheet.get_height() // 3)
        for j in range(3):
            for i in range(8):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(frame_location, self.rect.size)))

    def update(self, *args):
        # анимация
        self.cur_frame = (self.cur_frame + 1) % len(self.frames)
        self.image = self.frames[self.cur_frame]


class Player(pygame.sprite.Sprite):
    name = "player"

    def __init__(self, game, x, y):
        super().__init__(game.all_sprites)
        self.game = game
        self.frames1 = []
        self.frames2 = []
        hero = list(filter(lambda h: self.game.data["hero_colors"][h] == "ok", self.game.data["hero_colors"]))[0]
        if hero == "transparent_hero":
            self.cut_sheets(load_image('heroes/{}R.png'.format(hero), color_key=(0, 0, 0, 0)),
                            load_image('heroes/{}L.png'.format(hero), color_key=(0, 0, 0, 0)))
        else:
            self.cut_sheets(load_image('heroes/{}R.png'.format(hero)),
                            load_image('heroes/{}L.png'.format(hero)))
        self.cur_frame = 0
        self.image = self.frames1[self.cur_frame]
        self.rect = self.rect.move(x + (game.tile_width - self.rect.w) // 2, y)
        self.mask = pygame.mask.from_surface(self.image)
        self.moving_y = (0, 0)
        self.jumping = False
        self.moving_x = (0, 0)
        self.blink = 0
        self.take_life = False

    def cut_sheets(self, sheet1, sheet2):
        self.rect = pygame.Rect(0, 0, sheet1.get_width() // 4, sheet1.get_height() // 4)
        for j in range(4):
            for i in range(4):
                if j * 4 + i < 13:
                    frame_location = (self.rect.w * i, self.rect.h * j)
                    self.frames1.append(sheet1.subsurface(pygame.Rect(frame_location, self.rect.size)))
                    self.frames2.append(sheet2.subsurface(pygame.Rect(frame_location, self.rect.size)))

    def next_pic(self, direction):
        # сменить картинку (при ходьбе)
        if self.blink % 8 == 0:
            if direction > 0:
                # в правую сторону
                self.cur_frame = (self.cur_frame + 1) % len(self.frames1)
                self.image = self.frames1[self.cur_frame]
            elif direction < 0:
                # в левую
                self.cur_frame = (self.cur_frame + 1) % len(self.frames2)
                self.image = self.frames2[self.cur_frame]

    def move(self, x, y):
        if x:
            self.moving_x = [x, 5]
        if y and not self.jumping:
            self.moving_y = [y, 120]

    def check_collides(self, group, check_win=False):
        if check_win:
            # проверка на выигрыш, столкновение с флагом или монетой
            for sprite in pygame.sprite.spritecollide(self, group, False):
                if pygame.sprite.collide_mask(self, sprite):
                    if sprite.name == "flag":
                        return True
                    elif sprite.name == "coin":  # сбор монет
                        coins = choice(range(2, 6))
                        self.game.got_coins += coins
                        self.game.data["coins"] += coins
                        sprite.kill()
            return False
        else:
            # проверка на столкновение с заданной группой
            for sprite in pygame.sprite.spritecollide(self, group, False):
                if pygame.sprite.collide_mask(self, sprite):
                    # заодно на столкновение с жизнеотнимателями
                    if sprite.name in ("enemy", "thorns") and not self.blink:
                        if not self.take_life:  # защита от лишней потери жизней
                            self.game.lifes -= 1
                            self.take_life = True
                            if self.game.lifes:
                                # включаем неуязвимость на
                                # определенное время
                                self.blink = 50
                    return True
            return False

    def update(self, *args):
        self.take_life = False  # отнимать жизни можно опять

        if self.check_collides(self.game.all_sprites, check_win=True) and not self.blink:
            self.game.victory = True
            return True

        # при неуязвимости
        if self.blink:
            self.blink -= 1
            if self.blink % 4 == 0:
                self.image = self.game.images['empty'] if self.blink % 8 else self.frames1[self.cur_frame]
        else:
            # иначе проверяем на столкновение с передвигающимися врагами
            self.check_collides(self.game.danger_group)

        # ход по горизонтали
        i = 0
        for i in range(int(self.moving_x[1] * (1.5 if self.jumping else 1))):
            self.rect.x += self.moving_x[0]
            if self.check_collides(self.game.block_group):
                self.rect.x -= self.moving_x[0]
                self.moving_x = [0, 0]
                break
        if i:
            self.next_pic(self.moving_x[0])

        # движение фона
        for pic in self.game.game_fon:
            pic.rect.x -= self.moving_x[0] * 2
        self.moving_x = [0, 0]

        # движение по вертикали
        if self.moving_y[1] > 0:
            for i in range(10):
                self.rect.y += self.moving_y[0]
                if self.check_collides(self.game.block_group):
                    self.rect.y -= self.moving_y[0]
                    self.moving_y = [0, 0]
                    return False
            self.jumping = True
            self.moving_y[1] -= 8
            for pic in self.game.game_fon:
                pic.rect.y += 3
        else:  # падение
            for i in range(10):
                self.rect.y += 1
                if self.check_collides(self.game.block_group):
                    self.rect.y -= 1
                    self.jumping = False
                    return False
            for pic in self.game.game_fon:
                pic.rect.y -= 3


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
    # начальный сдвиг камеры
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
            "transition": pygame.mixer.Sound('data/sounds & music/transition.wav'),
        }

        self.images = {
            'box': load_image('box.png'),
            'ground': load_image('ground.png'),
            'stones': load_image('stones.png'),
            'thorns': load_image('thorns.png'),
            'step': load_image('step.png'),
            'enemy': load_image('ghost.png'),
            'flag': load_image('flag.png'),
            'empty': load_image('empty.png'),
            'pause': load_image('pause.png'),
            'dark_fon': load_image('dark_fon.png'),
            'coins': load_image('coins.png'),
            'locked_level': load_image('locked_level.png'),
            'locked_level_pay': load_image('locked_level_pay.png'),
            'sound': load_image('sound.png'),
            'music': load_image('music.png'),
            'non_sound': load_image('non_sound.png'),
            'non_music': load_image('non_music.png')
        }

        self.tile_width = self.tile_height = 70

        # загрузка данных
        try:
            self.data = loads(open('data/data.json', 'rb').read())
        except Exception:
            # или их создание
            self.null_progress()

        # запуск игры
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

        # кнопка вкл/окл звука
        img = self.images['sound' if self.data["sound"] else 'non_sound']
        self.screen.blit(img, (30, 200))
        all_elements[(30, 200, 30 + img.get_width(), 200 + img.get_height())] = self.invert_sound

        # кнопка вкл/откл музыки
        img = self.images['music' if self.data["music"] else 'non_music']
        self.screen.blit(img, (30, 260))
        all_elements[(30, 260, 30 + img.get_width(), 260 + img.get_height())] = self.invert_music

        # Строка уровней
        offset = 30  # для параллелепипеда
        space = 10  # между рамками
        frame_width = 50  # размер рамки и цифр
        start_x = self.WIDTH // 2 - ((frame_width + offset + space) * len(self.data["levels"]) // 2) + offset
        start_y = 250
        for i in range(8):
            n = str(i + 1)
            # если открыт
            if self.data["levels"][n] in (0, "ok"):
                # рисуем номер
                x1 = start_x + i * (frame_width + space + offset) + frame_width // (3 * len(n))
                y1 = start_y + frame_width // 10
                rect = self.render_text(n, x1, y1, size=frame_width, color=WHITE, italic=True)
                if self.data["levels"][n] == "ok":
                    self.render_text("v", rect.x + rect.w, y1 - frame_width // 5, size=frame_width, color=RED)
            else:
                # иначе замок
                x1 = (start_x + i * (frame_width + space + offset) +
                      (frame_width - self.images["locked_level"].get_width()) // 2)
                y1 = start_y + frame_width // 10
                # если уровень платный, выводим замок другого цвета
                img = self.images["locked_level" if self.data["levels"][n] == -1 else "locked_level_pay"]
                self.screen.blit(img, (x1, y1))

            rect = pygame.Rect(start_x + i * (frame_width + space + offset), 250, 50, 50)
            # добовляем координаты крайних точек в словарь
            all_elements[(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)] = (self.start_game, i + 1)
            # обрамляем
            self.frame_obj(rect, offset=offset)

        # Центральные кнопки:
        # задаем шаблон (rect) для всех рамок, нарисовав первую
        rect = self.render_text("New Game", None, 350, size=80, color=BLUE, center=True)
        self.frame_obj(rect)  # обрамляем
        # добовляем в словарь
        all_elements[(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)] = self.new_game

        for new_y, name, func in ((435, "Store", self.store),
                                  (520, "Quit", self.close),
                                  (605, "Help", self.help_info)):
            rect.y = new_y  # снижаем рамку
            self.render_text(name, None, new_y, size=80, color=BLUE, center=True)
            self.frame_obj(rect)
            all_elements[(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)] = func

        pygame.display.flip()  # обновляем дисплей

        # обрабатываем события
        # т.к. меню статичное, ставим наименьший fps, чтобы не нагружать процессор
        fps = 5
        # при любом обновлении информации на экране,
        # меню перерисовываем заново, возвращая True для start_ui
        while True:
            for event in pygame.event.get():
                # коректный выход
                if event.type == pygame.QUIT:
                    # спрашиваем пользователя, уверен ли он
                    if not self.close():
                        self.start_ui()
                # проверка горячих клавиши
                elif self.check_hot_keys(event):
                    return True
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    x, y = event.pos
                    # нахдим, попала ли мышь в область функционирующих элементов
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()  # звуковой переход
                        element = all_elements[element[0]]
                        # вызываем функцию кнопки
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
        for i in range(1, level):
            if self.data["levels"][str(i)] != "ok":
                return False

        self.play_fon_music(True)

        # группы спрайтов
        self.all_sprites = pygame.sprite.Group()
        self.tiles_group = pygame.sprite.Group()
        self.block_group = pygame.sprite.Group()
        self.danger_group = pygame.sprite.Group()

        # загружаем уровень
        self.level_map = load_level(level)

        # создаем фон на всю ширину и высоту карты
        self.game_fon = []
        w = 1800
        h = 1081
        for i in range(len(self.level_map[0]) // 25 + 1):
            for j in range(len(self.level_map) // 10 + 1):
                img = pygame.transform.flip(load_image('game_fon.png'),
                                            (i % 2), (j % 2))
                self.game_fon.append(MySprite(self, img, (-w // 3 + w * i),
                                              (-h // 3 + h * j), abs_coords=True))

        self.generate_level()
        self.camera = Camera(self)

        # независимые спрайты кнопки паузы и монет
        MySprite(self, self.images["pause"], 10, 10, abs_coords=True)
        MySprite(self, self.images["coins"], self.WIDTH - 270, 17, abs_coords=True)

        self.lifes = 3
        self.got_coins = 0
        self.victory = False

        keys = {
            (0, -1): False,  # UP
            (1, 0): False,  # RIGHT
            (-1, 0): False   # LEFT
        }

        fps = 50
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    self.play_sound()
                    x, y = event.pos
                    # если клик по области кнопки паузы
                    if 10 <= x <= 60 and 10 <= y <= 60:
                        answ = self.pause()
                        if answ == "RESTART":
                            self.all_sprites.clear(self.screen, self.images['dark_fon'])
                            self.start_game(level)
                            return False
                        elif answ == "Menu":
                            return False
                # обработка нажатия клавиш
                elif event.type == pygame.KEYDOWN:
                    if event.key in (32, 119, 172, 273):  # UP
                        keys[(0, -1)] = True
                    elif event.key in (100, 162, 275):  # RIGHT
                        keys[(1, 0)] = True
                    elif event.key in (97, 160, 276):  # LEFT
                        keys[(-1, 0)] = True
                    else:
                        self.check_hot_keys(event)
                # обработка отпускания клавиш
                elif event.type == pygame.KEYUP:
                    if event.key in (32, 119, 172, 273):  # UP
                        keys[(0, -1)] = False
                    elif event.key in (100, 162, 275):  # RIGHT
                        keys[(1, 0)] = False
                    elif event.key in (97, 160, 276):  # LEFT
                        keys[(-1, 0)] = False

            # проверка нажатых кнопок
            for k in keys:
                if keys[k]:
                    self.player.move(*k)

            # обновляем спрайты
            self.all_sprites.update()
            # изменяем ракурс камеры
            self.camera.update(self.player)
            # обновляем положение всех спрайтов
            for sprite in self.all_sprites:
                if sprite.name != "other":
                    self.camera.apply(sprite)

            # перерисовываем экран со спрайтами
            self.screen.fill((0, 0, 0))
            self.all_sprites.draw(self.screen)

            # отображаем жизни
            for i in range(self.lifes):
                pygame.draw.circle(self.screen, RED, (self.WIDTH - 40 - i * 30, 40), 10)
            # деньги
            self.render_text(str(self.data["coins"]), self.WIDTH - 220, 27,
                             size=40, color=BLACK, italic=True)

            # проверка на выигрыш
            if self.victory:
                answ = self.win(level)
                if answ in ("RESTART", "NEXT"):
                    self.all_sprites.clear(self.screen, self.images['dark_fon'])
                    self.start_game(level + (1 if answ == "NEXT" else 0))
                return True

            # проверка на проигрыш
            if self.lifes == 0:
                answ = self.lose()
                if answ == "RESTART":
                    self.all_sprites.clear(self.screen, self.images['dark_fon'])
                    self.start_game(level)
                return False

            pygame.display.flip()
            self.clock.tick(fps)

    def pause(self):
        self.render_dark()

        self.screen.blit(load_image('restart.png'), (220, 230))
        pygame.draw.polygon(self.screen, NEON, [(600, 230), (750, 330), (600, 430)])

        all_elements = {(220, 230, 420, 430): "RESTART",
                        (600, 230, 750, 4300): "CONTINUE"}

        all_elements.update(self.render_bar("pause"))

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        element = all_elements[element[0]]
                        if element in ("RESTART", "CONTINUE", "Menu"):
                            return element
                else:
                    self.check_hot_keys(event)
            self.clock.tick(fps)

    def win(self, level):
        self.play_fon_music(False)
        self.play_sound(pygame.mixer.Sound('data/sounds & music/win.wav'))
        self.render_dark()

        if self.data["levels"][str(level)] != "ok":
            # размер вознаграждения, если уровень пройден впервые
            self.data["levels"][str(level)] = "ok"
            coins = choice(range(level * 10, level * 15 + 1, 5))
        else:
            coins = choice(range(level * 2, level * 5 + 1, 2))

        # учитываем в вознаграждении оставшиеся жизни
        coins = int(coins * self.lifes * 2 / 3)
        # выводим на экран
        self.render_text("YOU GOT {} + {} COINS!".format(self.got_coins, coins), self.WIDTH - 500, 50,
                         size=50, color=BLUE)
        # сохраняем
        self.data["coins"] += coins + self.got_coins
        self.got_coins = 0

        all_elements = dict()
        all_elements.update(self.render_bar("WIN"))

        next_level = -1
        if level < len(self.data["levels"]):
            # если следующий уровень бесплатный, разблокируем
            if self.data["levels"][str(level + 1)] == -1:
                self.data["levels"][str(level + 1)] = 0
                next_level = 1
            elif self.data["levels"][str(level + 1)] in (0, "ok"):
                next_level = 1
            else:
                next_level = 0
        elif self.lifes != 3:
            next_level = 0

        if next_level == 1:
            self.screen.blit(load_image('restart.png'), (220, 230))
            self.screen.blit(load_image('next.png'), (600, 230))
            all_elements.update({(220, 230, 420, 430): "RESTART",
                                 (600, 230, 750, 430): "NEXT"})
        elif next_level == 0:
            # доступных уровней нет,
            # или последний уровень пройден не идеально
            self.screen.blit(load_image('restart.png'), (400, 230))
            all_elements.update({(400, 230, 650, 430): "RESTART"})
        else:
            # игра закончена
            self.render_text("YOU WON!!!", None, 200, size=120, color=NEON, center=True)
            self.render_text("ALL LEVELS UNLOCKED!", None, 350, size=60, color=NEON, center=True)

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        element = all_elements[element[0]]
                        if element in ("RESTART", "NEXT", "Menu"):
                            return element
                else:
                    self.check_hot_keys(event)
            self.clock.tick(fps)

    def lose(self):
        self.play_fon_music(False)
        self.play_sound(pygame.mixer.Sound('data/sounds & music/lose.wav'))

        self.data['coins'] -= self.got_coins
        self.got_coins = 0

        self.render_dark()
        self.screen.blit(load_image('restart.png'), (400, 230))

        all_elements = {(400, 230, 650, 430): "RESTART"}
        all_elements.update(self.render_bar("LOSE"))

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        element = all_elements[element[0]]
                        if element in ("RESTART", "Menu"):
                            return element
                else:
                    self.check_hot_keys(event)
            self.clock.tick(fps)

    def new_game(self):
        self.render_menu_fon()
        self.render_dark()
        all_elements = dict()

        rect = self.render_text("YES", 200, 350, size=80, color=BLUE)
        self.frame_obj(rect)
        all_elements[(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)] = self.null_progress

        rect.x = self.WIDTH - rect.x - rect.w
        self.render_text("NO", 700, 350, size=80, color=BLUE)
        self.frame_obj(rect)
        all_elements[(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)] = None

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
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        element = all_elements[element[0]]
                        if element:
                            element()
                        return False
                else:
                    self.check_hot_keys(event)
            self.clock.tick(fps)

    def store(self):
        self.render_menu_fon()
        self.render_dark()

        self.screen.blit(self.images["coins"], (self.WIDTH - 200, 45))

        self.render_text(str(self.data["coins"]), self.WIDTH - 150, 53,
                         size=40, color=WHITE, italic=True)

        all_elements = dict()
        all_elements.update(self.render_bar("store"))

        # цвета героя
        self.render_text("Additional colors:", None, 130, size=35,
                         color=WHITE, italic=True, center=True)
        colors = list(self.data['hero_colors'])
        n = len(colors)
        for i in range(n):
            curr_x = int((self.WIDTH // (n + 1)) * (i + 0.6))
            c = colors[i]
            rect = self.render_text(c[:-5], curr_x, 300, size=35, color=WHITE)

            # изображение
            pic = pygame.Surface((44, 70))
            pic.fill((255, 255, 255, 150))
            pic.blit(load_image("heroes/{}L.png".format(colors[i])).subsurface(
                pygame.Rect(0, 0, 44, 70)), (0, 0)
            )
            rect_pic = pygame.Rect(rect.x + (rect.w - 44) // 2, 200, 44, 70)
            self.screen.blit(pic, (rect_pic.x, rect_pic.y))

            # стоимость
            cost = self.data['hero_colors'][c]
            if type(cost) is int and cost:
                func = (self.buy_thing, 'hero_colors', c)
                rect = self.render_text(str(cost) + '$', None, 350,
                                        size=45, color=WHITE, center=(rect.x, rect.w))
                self.frame_obj(rect)
            else:
                # если куплен
                func = (self.choose_thing, 'hero_colors', c)
                if cost == 'ok':
                    rect = self.render_text(' ok ', None, 350,
                                            size=45, color=BLUE, center=(rect.x, rect.w))
                else:
                    rect = rect_pic

            # добавление в словарь элемента
            all_elements[(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)] = func

        # доп. уровни
        levels = list(filter(lambda lev: type(self.data['levels'][lev]) is int and self.data['levels'][lev],
                             list(self.data['levels'])[5:]
                             )
                      )
        if levels:
            self.render_text("Additional levels:", None, self.HEIGHT - 260,
                             size=35, color=WHITE, italic=True, center=True)
            n = len(levels)
            for i in range(n):
                w = int((self.WIDTH // (n + 1)) * (i + 1))
                level = levels[i]
                rect = self.render_text(level, w, self.HEIGHT - 200, size=60, color=WHITE)

                cost = self.data['levels'][level]
                rect = self.render_text(str(cost) + '$', None, self.HEIGHT - 120,
                                        size=45, color=WHITE, center=(rect.x, rect.w))
                func = (self.buy_thing, 'levels', level)
                self.frame_obj(rect)
                all_elements[(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)] = func

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if not self.close():
                        self.start_ui()
                elif self.check_hot_keys(event):
                    return True
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        element = all_elements[element[0]]
                        if type(element) == str:
                            if element == "Menu":
                                return True
                        elif type(element) == tuple:
                            if element[0](*element[1:]):
                                self.store()
                                return True
            self.clock.tick(fps)

    def help_info(self):
        self.render_menu_fon()
        self.render_dark()

        all_elements = dict()
        all_elements.update(self.render_bar("help"))

        with open('data/help_info.txt') as data:
            help_text = data.read().split('\n')

        for i in range(len(help_text)):
            # построчно отображаем текст из информационного файла
            self.render_text(help_text[i], 50, 140 + i * 40, color=(200, 200, 200))

        pygame.display.flip()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if not self.close():
                        self.start_ui()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    x, y = event.pos
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        self.play_sound()
                        if all_elements[element[0]] == "Menu":
                            return True
                else:
                    self.check_hot_keys(event)
            self.clock.tick(fps)

    def generate_level(self):
        for y in range(len(self.level_map)):
            for x in range(len(self.level_map[0])):
                if self.level_map[y][x] == '#':
                    Tile(self, 'ground', x, y, self.block_group, self.tiles_group, name="ground")

                elif self.level_map[y][x] == '+':
                    Tile(self, 'box', x, y, self.block_group, self.tiles_group, name="box")

                elif self.level_map[y][x] == '%':
                    Tile(self, 'stones', x, y, self.block_group, self.tiles_group, name="stones")

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

    def render_dark(self):
        self.screen.blit(self.images['dark_fon'], (0, 0))

    def render_text(self, text, x, y, size=30, color=BLACK,
                    italic=False, u=False, center=()):
        font = pygame.font.Font(None, size)
        font.set_italic(italic)
        font.set_underline(u)
        string_rendered = font.render(text, 1, color)
        rect = string_rendered.get_rect()
        if center:
            if center is True:
                rect.x = self.WIDTH // 2 - rect.w // 2
            elif type(center) == tuple:
                x = center[0]
                w = center[1]
                rect.x = x + (w - rect.w) // 2
        else:
            rect.x = x
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
                                    color=(RED if i == n - 1 else ORANGE),
                                    italic=(False if i == n - 1 else True))
            x2 = x1 + rect.w + 55
            points = [(x1, y2), (x1 + 55, y1), (x2 + 55, y1), (x2, y2)]
            pygame.draw.polygon(self.screen, (255, 165, 0), points, 5)
            all_elements[(x1 + 55, y1, x2, y2)] = places[i]
            x1 = x2
        return all_elements

    def frame_obj(self, rect, offset=50, color=NEON, w=3):
        p_list = [(rect.x - offset, rect.y + rect.h),
                  (rect.x, rect.y - 5),
                  (rect.x + rect.w + offset, rect.y - 5),
                  (rect.x + rect.w, rect.y + rect.h)]
        pygame.draw.polygon(self.screen, color, p_list, w)

    def check_hot_keys(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == 105:
                self.invert_sound()
                return True
            elif event.key == 111:
                self.invert_music()
                return True

    def buy_thing(self, category, thing):
        cost = self.data[category][thing]
        # если достаточно денег
        if self.data["coins"] >= cost:
            self.data[category][thing] = 0
            self.data["coins"] -= cost
            return True
        return False

    def choose_thing(self, category, thing):
        # если предмет куплен
        if self.data[category][thing] == 0:
            for i in self.data[category]:
                if self.data[category][i] == "ok":
                    self.data[category][i] = 0
                elif i == thing:
                    self.data[category][thing] = "ok"
            return True
        return False

    def play_sound(self, sound=None):
        if self.data["sound"]:
            if sound:
                sound.play()
            else:
                self.sounds["transition"].play()

    def play_fon_music(self, val):
        if val and self.data["music"]:
            pygame.mixer.music.load('data/sounds & music/fon_music.wav')
            pygame.mixer.music.play(-1)
        else:
            pygame.mixer.music.stop()

    def invert_sound(self):
        self.sounds['transition'].stop()
        self.data["sound"] = 0 if self.data["sound"] else 1

    def invert_music(self):
        self.sounds['transition'].stop()
        if self.data["music"]:
            self.data["music"] = 0
            self.play_fon_music(False)
        else:
            self.data["music"] = 1
            self.play_fon_music(True)

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
                "7": 150,
                "8": 200
            },

            "coins": 0,

            "hero_colors": {
                "classic_hero": "ok",
                "red_hero": 50,
                "blue_hero": 50,
                "green_hero": 100,
                "transparent_hero": 300
            },

            "sound": 1,
            "music": 0
        }
        self.save_progress()

    def close(self):
        self.render_menu_fon()
        self.render_dark()
        all_elements = dict()

        rect = self.render_text("YES", 200, 350, size=80, color=BLUE)
        self.frame_obj(rect)
        all_elements[(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)] = self.terminate

        rect.x = self.WIDTH - rect.x - rect.w
        self.render_text("NO", 700, 350, size=80, color=BLUE)
        self.frame_obj(rect)
        all_elements[(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)] = None

        self.render_text("Are you sure?", None, 150, size=80, color=BLUE, italic=True, center=True)

        pygame.display.flip()

        self.save_progress()

        fps = 5
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.terminate()
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
