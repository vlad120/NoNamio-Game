import pygame
import sys
from json import loads, dumps

NEON = (57, 255, 20)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)


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
    def __init__(self, game, tile_type, pos_x, pos_y, *groups):
        super().__init__(game.all_sprites, *groups)
        self.image = game.images[tile_type]
        self.rect = self.image.get_rect().move(game.tile_width * pos_x,
                                               game.tile_height * pos_y)
        self.mask = pygame.mask.from_surface(self.image)
        self.name = "tile"


class Enemy(pygame.sprite.Sprite):
    def __init__(self, game, pos_x, pos_y):
        super().__init__(game.all_sprites, game.enemy_group)
        self.image = game.images["enemy"]
        self.rect = self.image.get_rect().move(game.tile_width * pos_x,
                                               game.tile_height * pos_y)
        self.game = game
        self.direction = 1
        self.name = "enemy"

    def update(self, *args):
        if pygame.sprite.spritecollide(self, self.game.tiles_group, False):
            self.direction *= -1
        self.rect.x += self.direction * 2


class Player(pygame.sprite.Sprite):
    def __init__(self, game, x, y):
        super().__init__(game.all_sprites)
        self.frames1 = []
        self.frames2 = []
        self.cut_sheet(game.images['playerR'], game.images['playerL'])
        self.cur_frame = 0
        self.image = self.frames1[self.cur_frame]
        self.rect = self.rect.move(x + (game.tile_width - self.rect.width) // 2, y)
        self.mask = pygame.mask.from_surface(self.image)
        self.name = "player"

    def cut_sheet(self, sheet1, sheet2):
        self.rect = pygame.Rect(0, 0, sheet1.get_width() // 4, sheet1.get_height() // 4)
        for j in range(4):
            for i in range(4):
                if j * 4 + i < 13:
                    frame_location = (self.rect.w * i, self.rect.h * j)
                    self.frames1.append(sheet1.subsurface(pygame.Rect(frame_location, self.rect.size)))
                    self.frames2.append(sheet2.subsurface(pygame.Rect(frame_location, self.rect.size)))

    def next_pic(self, direction):
        if direction > 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames1)
            self.image = self.frames1[self.cur_frame]
        elif direction < 0:
            self.cur_frame = (self.cur_frame + 1) % len(self.frames2)
            self.image = self.frames2[self.cur_frame]


class GameFon(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__(game.all_sprites)
        self.image = game.images['game_fon']
        self.rect = self.image.get_rect()
        self.name = "fon"


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
        if obj.name != "fon":
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
            'game_fon': load_image('game_fon.jpg'),
            'playerR': load_image('heroR.png'),
            'playerL': load_image('heroL.png'),
            'enemy': load_image('ghost.png'),
            'locked_level': load_image('locked_level.png'),
            'coins': load_image('coins.png'),
            'sound': load_image('sound.png'),
            'non_sound': load_image('non_sound.png'),
            'music': load_image('music.png'),
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
        self.render_menu_fon()
        self.render_text("NoNamio".ljust(14), self.WIDTH // 2, 80,
                         size=120, color=NEON, italic=True, u=True)

        self.screen.blit(self.images["coins"], (20, 140))

        self.render_text(str(self.data["coins"]), 70, 150,
                         size=40, color=WHITE, italic=True)

        # словарь координат элементов и их функций
        all_elements = self.render_bar()

        all_elements.update(self.render_sound_button())
        all_elements.update(self.render_music_button())

        # рисуем уровни
        offset = 30  # для параллелепипеда
        space = 10  # между рамками
        frame_width = 50  # размер рамки
        start_x = self.WIDTH // 2 - ((frame_width + offset + space) * len(self.data["levels"]) // 2) + offset
        start_y = 250
        for i in range(8):
            # если открыт
            if self.data["levels"][str(i + 1)] == 0:
                # рисуем номер
                n = str(i + 1)
                x1 = start_x + i * (frame_width + space + offset) + frame_width // (3 * len(n))
                y1 = start_y + frame_width // 10
                self.render_text(n, x1, y1, size=frame_width, color=WHITE)
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
        if self.data["levels"][str(level)] != 0:
            return False

        self.play_fon_music(True)

        # группы спрайтов
        self.all_sprites = pygame.sprite.Group()
        self.tiles_group = pygame.sprite.Group()
        self.block_group = pygame.sprite.Group()
        self.enemy_group = pygame.sprite.Group()

        GameFon(self)
        self.generate_level(level)
        self.camera = Camera(self)

        keys = {273: [False, (0, -1)],  # UP
                274: [False, (0, 1)],   # DOWN
                275: [False, (1, 0)],   # LEFT
                276: [False, (-1, 0)]}  # RIGHT

        fps = 30
        running = True
        while running:
            # обработка событий
            for event in pygame.event.get():
                # корректный выход
                if event.type == pygame.QUIT:
                    self.close()

                if event.type == pygame.KEYDOWN:
                    if event.key in keys:
                        keys[event.key][0] = True
                        if keys[275][0] and keys[276][0]:
                            keys[275 if event.key == 276 else 276][0] = False
                elif event.type == pygame.KEYUP:
                    if event.key in keys:
                        keys[event.key][0] = False

            for k in keys:
                if keys[k][0]:
                    self.move_player(*keys[k][1])

            # обновляем спрайты
            self.all_sprites.update()
            # изменяем ракурс камеры
            self.camera.update(self.player)
            # # обновляем положение всех спрайтов
            for sprite in self.all_sprites:
                self.camera.apply(sprite)
            # перерисовываем экран со спрайтами
            self.all_sprites.draw(self.screen)

            pygame.display.flip()
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

    def move_player(self, x, y):
        self.player.rect.x += x * 3
        self.player.rect.y += y * 3
        for sprite in self.block_group:
            if pygame.sprite.collide_mask(self.player, sprite):
                self.player.rect.x -= x * 3
                self.player.rect.y -= y * 3
                return False
        self.player.next_pic(x)

    def generate_level(self, level):
        self.level_map = load_level(level)

        for y in range(len(self.level_map)):
            for x in range(len(self.level_map[0])):
                if self.level_map[y][x] == '#':
                    Tile(self, 'ground', x, y, self.block_group, self.tiles_group)
                elif self.level_map[y][x] == '^':
                    Tile(self, 'box', x, y, self.block_group, self.tiles_group)
                elif self.level_map[y][x] == '*':
                    Enemy(self, x, y)
                elif self.level_map[y][x] == '@':
                    player = (x, y)

        self.player = Player(self, player[0] * self.tile_width, player[1] * self.tile_height)

    def render_menu_fon(self):
        self.screen.fill((0, 0, 0))
        for x in range(0, self.WIDTH, 10):
            pygame.draw.line(self.screen, (100, 100, 100), (self.WIDTH, 0), (x, self.HEIGHT), 1)
        for y in range(0, self.HEIGHT, 10):
            pygame.draw.line(self.screen, (100, 100, 100), (self.WIDTH, 0), (0, y), 1)

    def render_text(self, text, x, y, size=30, color=(0, 0, 0), italic=False, u=False, center=False):
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
        for place in ["Menu"] + list(places):
            rect = self.render_text(place, x1 + 55, 30, size=70, color=(255, 165, 0), italic=True)
            x2 = x1 + rect.width + 55
            points = [(x1, y2), (x1 + 55, y1), (x2 + 55, y1), (x2, y2)]
            pygame.draw.polygon(self.screen, (255, 165, 0), points, 5)
            all_elements[(x1 + 55, y1, x2, y2)] = place
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

    def render_music_button(self, x=30, y=260):
        img = self.images['music' if self.data["music"] else 'non_music']
        self.screen.blit(img, (x, y))
        return {(x, y, x + img.get_width(), y + img.get_height()): lambda: self.invert("music")}

    def play_sound(self):
        if self.data["sound"]:
            self.sounds["transition"].play()

    def play_fon_music(self, val):
        if val and self.data["music"]:
            pygame.mixer.music.load('data/fon_music.wav')
            pygame.mixer.music.play()
        else:
            pygame.mixer.music.stop()

    def invert(self, parameter):
        self.sounds['transition'].stop()
        if parameter == "music":
            pygame.mixer.music.stop()
        self.data[parameter] = 0 if self.data[parameter] else 1

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
