import pygame
import sys
from os import path
from json import loads, dumps

NEON = (57, 255, 20)
BLUE = (0, 0, 255)


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

        self.SIZE = self.WIDTH, self.HEIGHT = width, height
        self.screen = pygame.display.set_mode(self.SIZE)

        self.clock = pygame.time.Clock()

        self.tile_images = {
            'wall': load_image('box.png'),
            'empty': load_image('grass.png'),
            "locked_level": load_image("locked_level.png")
        }
        # self.player_image =

        self.tile_width = self.tile_height = 50

        # группы спрайтов
        self.all_sprites = pygame.sprite.Group()
        self.tiles_group = pygame.sprite.Group()
        self.block_group = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()

        self.player = None
        self.level = None

        self.data = loads(open("data/data.json", 'rb').read())

        pygame.init()
        pygame.display.set_caption("NoNamio")

        self.menu()

    def menu(self):
        self.blit_menu_fon()
        self.render_bar()
        self.render_text("NoNamio".ljust(14), self.WIDTH // 2, 80,
                         size=120, color=NEON, italic=True, u=True)

        # словарь координат элементов и их функций
        all_elements = dict()

        # рисуем уровни
        start_x = self.WIDTH // 2 - (55 * len(self.data["levels"]) // 2)
        start_y = 250
        for i in range(8):
            # если открыт
            if self.data["levels"][str(i + 1)] == 0:
                # рисуем номер
                self.render_text(str(i + 1).rjust(2), start_x + i * 55, start_y + 10, size=50, color=(255, 255, 255))
            else:
                # иначе рисуем замок
                self.screen.blit(self.tile_images["locked_level"], (start_x + i * 55 + 5, start_y + 5))

            rect = pygame.Rect(start_x + i * 55, 250, 50, 50)
            # добовляем координаты крайних точек в словарь
            all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.width)] = (self.start_game, i + 1)
            pygame.draw.rect(self.screen, BLUE, rect, 3)  # обрамляем ячейку

        # рисуем кнопки:
        # задаем шаблон для всех рамок, нарисовав первую
        rect = self.render_text("New Game", None, 350, size=80, color=BLUE, center=True)
        self.frame_obj(rect)  # обрамляем
        # добовляем в словарь
        all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)] = (self.new_game, None)

        for new_y, name, func in ((435, "Store", self.store),
                                  (520, "Quit", self.close),
                                  (605, "Help", self.help_info)):
            rect.y = new_y  # снижаем рамку
            self.render_text(name, None, new_y, size=80, color=BLUE, center=True)
            self.frame_obj(rect)
            all_elements[(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)] = (func, None)

        pygame.display.flip()  # обновляем дисплей

        # обрабатываем события
        # т.к. меню статичное, ставим наименьший fps, чтобы не нагружать процессор
        fps = 1
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                # при клике
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    # нахдим, попала ли мышь в область
                    # функционирующих элементов
                    element = list(filter(lambda e: e[0] <= x <= e[2] and e[1] <= y <= e[3],
                                          all_elements.keys()))
                    if element:
                        element = all_elements[element[0]]
                        if element[1] is None:
                            element[0]()
                        else:
                            # если есть аргумент к функции, передаем его
                            element[0](element[1])
                        pygame.display.flip()
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

    def store(self):
        print("store")

    def close(self):
        print("quit")
        pygame.quit()
        sys.exit()

    def help_info(self):
        print("help")

    def generate_level(self, level):
        return

    def move_player(self, x, y):
        self.player.rect.x += x * 2
        self.player.rect.y += y * 2
        if pygame.sprite.spritecollideany(self.player, self.block_group):
            self.player.rect.x -= x * 2
            self.player.rect.y -= y * 2

    def blit_menu_fon(self):
        self.screen.fill((0, 0, 0))
        for x in range(0, self.WIDTH, 10):
            pygame.draw.line(self.screen, (100, 100, 100), (self.WIDTH, 0), (x, self.HEIGHT), 1)
        for y in range(0, self.HEIGHT, 10):
            pygame.draw.line(self.screen, (100, 100, 100), (self.WIDTH, 0), (0, y), 1)

    def blit_game_fon(self):
        pass

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
        coords = []
        x1 = 0
        for place in ["Menu"] + list(places):
            rect = self.render_text(place, x1 + 55, 30, size=70, color=(255, 165, 0), italic=True)
            x2 = x1 + rect.width + 55
            coords.append([(x1, 105), (x1 + 55, 0), (x2 + 55, 0), (x2, 105)])
            pygame.draw.polygon(self.screen, (255, 165, 0), coords[-1], 5)
            x1 = x2
        return coords

    def frame_obj(self, rect):
        p_list = [(rect.x - 50, rect.y + rect.height),
                  (rect.x, rect.y - 5),
                  (rect.x + rect.width + 50, rect.y - 5),
                  (rect.x + rect.width, rect.y + rect.height)]
        pygame.draw.polygon(self.screen, NEON, p_list, 3)


if __name__ == "__main__":
    Game(1000, 700)
