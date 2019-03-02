import pygame
import sys
from os import path
from json import loads, dumps

NEON = (57, 255, 20)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)


def load_image(name, colorkey=None):
    fullname = path.join('data', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)

    if colorkey:
        if colorkey is -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    return image


def load_level(filename):
    filename = "data/" + filename
    # читаем уровень, убирая символы перевода строки
    with open(filename, 'r') as mapFile:
        level_map = [line.strip() for line in mapFile]

    # и подсчитываем максимальную длину
    max_width = max(map(len, level_map))

    # дополняем каждую строку пустыми клетками ('.')
    return list(map(lambda x: x.ljust(max_width, '.'), level_map))


class AnimatedSprite(pygame.sprite.Sprite):
    def __init__(self, game, sheet, columns, rows, x, y):
        super().__init__(game.all_sprites)
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.rect.move(x, y)

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(frame_location, self.rect.size)))

    def update(self):
        self.cur_frame = (self.cur_frame + 1) % len(self.frames)
        self.image = self.frames[self.cur_frame]


class Camera:
    # зададим начальный сдвиг камеры
    def __init__(self, screen_width, screen_height):
        self.dx = 0
        self.dy = 0
        self.WIDTH = screen_width
        self.HEIGHT = screen_height

    # сдвинуть объект obj на смещение камеры
    def apply(self, obj):
        obj.rect.x += self.dx
        obj.rect.y += self.dy

    # позиционировать камеру на объекте target
    def update(self, target):
        self.dx = -(target.rect.x + target.rect.w // 2 - self.WIDTH // 2)
        self.dy = -(target.rect.y + target.rect.h // 2 - self.HEIGHT // 2)


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
            'wall': load_image('box.png'),
            'empty': load_image('grass.png'),
            'locked_level': load_image('locked_level.png'),
            'coins': load_image('coins.png'),
            'sound': load_image('sound.png'),
            'non_sound': load_image('non_sound.png'),
            'music': load_image('music.png'),
            'non_music': load_image('non_music.png')
        }

        self.tile_width = self.tile_height = 50

        # группы спрайтов
        self.all_sprites = pygame.sprite.Group()
        self.tiles_group = pygame.sprite.Group()
        self.block_group = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()

        self.player = None
        self.level = None

        self.data = loads(open('data/data.json', 'rb').read())

        # self.play_fon_music(True)

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
        print("start")
        # level = load_level("level1.txt")
        #
        # player, level_w, level_h, first_spr, last_spr = self.generate_level(level)
        # camera = Camera()
        #
        # keys = {273: [False, (0, -1)],  # UP
        #         274: [False, (0, 1)],   # DOWN
        #         275: [False, (1, 0)],  # LEFT
        #         276: [False, (-1, 0)]}   # RIGHT
        #
        # fps = 50
        # running = True
        # while running:
        #     # обработка событий
        #     for event in pygame.event.get():
        #         # корректный выход
        #         if event.type == pygame.QUIT:
        #             running = False
        #
        #         if event.type == pygame.KEYDOWN:
        #             if event.key in keys:
        #                 keys[event.key][0] = True
        #         elif event.type == pygame.KEYUP:
        #             if event.key in keys:
        #                 keys[event.key][0] = False
        #
        #     for k in keys:
        #         if keys[k][0]:
        #             self.move_player(*keys[k][1])
        #
        #     # обновляем спрайты
        #             self.all_sprites.update()
        #     # изменяем ракурс камеры
        #     camera.update(player)
        #     # # обновляем положение всех спрайтов
        #     for sprite in self.all_sprites:
        #         camera.apply(sprite)
        #     # перерисовываем экран со спрайтами
        #     self.blit_game_fon()
        #     self.all_sprites.draw(self.screen)
        #
        #     pygame.display.flip()
        #     self.clock.tick(fps)

    def new_game(self):
        print("new game")

    def generate_level(self, level):
        return

    def store(self):
        self.render_menu_fon()
        all_elements = self.render_bar("store")

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
        all_elements = self.render_bar("help")

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

    def play_fon_music(self, val):
        if val:
            pygame.mixer.music.load('data/fon.mp3')
            pygame.mixer.music.play()
        else:
            pygame.mixer.music.stop()

    def move_player(self, x, y):
        self.player.rect.x += x * 2
        self.player.rect.y += y * 2
        if pygame.sprite.spritecollideany(self.player, self.block_group):
            self.player.rect.x -= x * 2
            self.player.rect.y -= y * 2

    def render_menu_fon(self):
        self.screen.fill((0, 0, 0))
        for x in range(0, self.WIDTH, 10):
            pygame.draw.line(self.screen, (100, 100, 100), (self.WIDTH, 0), (x, self.HEIGHT), 1)
        for y in range(0, self.HEIGHT, 10):
            pygame.draw.line(self.screen, (100, 100, 100), (self.WIDTH, 0), (0, y), 1)

    def render_game_fon(self):
        pass

    def render_text(self, text, x, y, size=30, color=(0, 0, 0),
                    italic=False, u=False, center=False):
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

    def invert(self, parameter):
        self.data[parameter] = 0 if self.data[parameter] else 1

    def play_sound(self):
        if self.data["sound"]:
            self.sounds["transition"].play()

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
