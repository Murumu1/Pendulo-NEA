import pygame
from pygame import Rect, Surface
import pygame.gfxdraw

import sympy
import colorsys

from typing import Optional, Callable

from pygame.sprite import Group

pygame.init()

# Common colours
BLACK = 0, 0, 0
WHITE = 255, 255, 255
screen = pygame.display.set_mode(flags=pygame.FULLSCREEN)
SCREEN_SIZE = SCREEN_WIDTH, SCREEN_HEIGHT, = (
    pygame.display.Info().current_w,
    pygame.display.Info().current_h,
)

# Manage frame rate
clock = pygame.time.Clock()
FPS = 1200
time = 0
speed = 1

A, F, P, D, T = sympy.symbols("a, f, p, d, t")
PENDULUM_EXPR = 50 * A * sympy.sin(T * F + P) * sympy.exp(-D * T)

font = pygame.font.Font("arial-unicode-ms.ttf", 15)


def create_text(text, colour, center):
    t = font.render(text, True, colour)
    t_r = t.get_rect(center=center)
    screen.blit(t, t_r)
    return t_r


def darken(colour: tuple, percent=0):
    r, g, b = colour
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    v = (v - (0.2 if percent == 0 else percent)) if (v >= 0.2 and percent) else 0
    return tuple(map(lambda x: x * 255, list(colorsys.hsv_to_rgb(SCREEN_HEIGHT, s, v))))


SLIDER_MOVED = pygame.USEREVENT + 1
SPRITE_HOVER = pygame.USEREVENT + 2
TAB_CREATED = pygame.USEREVENT + 3

all_sprites = pygame.sprite.Group()
widget_group = pygame.sprite.Group()


class SpriteHandler(pygame.sprite.Sprite):
    def __init__(self):
        super(SpriteHandler, self).__init__()

        self.sprite_hover = pygame.event.Event(
            SPRITE_HOVER, name=self.__class__.__name__
        )

        self.active = True

    def on_click(self, *args, **kwargs) -> None:
        pass

    def on_drag(self, *args, **kwargs) -> None:
        pass


class Slider(SpriteHandler):
    def __init__(self, tag, index, min_val, max_val, default):
        super(Slider, self).__init__()

        self.min_val = min_val
        self.max_val = max_val
        self.i = index
        self.tag = tag
        self.default = default

        # x positions
        # self.bar_start = 50
        # self.bar_end = 250
        # self.bar_length = self.bar_start + self.bar_end

        self.r = Rect((0, 0), (30, 30))
        self.r.center = (
            ((self.default * 300) / (self.max_val - self.min_val)) + 50,
            SCREEN_HEIGHT - (self.i * 70) + 30,
        )

        self.image = Surface((300, 60))
        self.rect = self.image.get_rect(center=(150, self.r.centery - 15))

        self.slider_event = pygame.event.Event(SLIDER_MOVED, tag=tag, slider_id=index)
        self.value = self.default

        widget_group.add(self)

    def update(self, *args, **kwargs) -> None:
        create_text(str(self.min_val), WHITE, (20, self.r.centery))
        create_text(str(self.max_val), WHITE, (280, self.r.centery))
        create_text(self.tag, WHITE, (150, self.r.centery - 30))

        pygame.gfxdraw.box(screen, self.r, WHITE)
        pygame.gfxdraw.hline(screen, 50, 250, self.r.centery, WHITE)

    # Moves the slider-ball to chosen position
    def on_drag(self, mouse_position, **kwargs):
        if kwargs["show"]:
            new_x = mouse_position[0]
            if 250 > new_x > 50:
                self.r.center = (new_x, self.r.centery)
                self.value = ((self.max_val - self.min_val) / 300) * self.r.centerx

            pygame.event.post(self.slider_event)


class Button(SpriteHandler):
    """
    Main Button class for when things happen when its clicked, doesn't constantly
    do the function call

    :param dimensions: tuple(top, left, width, height)
    :param function: any procedure, should not return
    :param image: the surface object of the loaded image
    :param toggle_periodicity: how many clicks to turn off
    """

    def __init__(
        self,
        tag: str,
        dimensions: tuple,
        function: Callable[..., None],
        colour: Optional[tuple] = None,
        image: Optional[Surface] = None,
        toggle_periodicity: int = 2,
    ):
        super(Button, self).__init__()
        self.tag = tag
        self.function = function
        self.image = Surface((dimensions[2], dimensions[3]))

        self.toggle_periodicity = toggle_periodicity
        self.toggles = 0
        self.toggled = False

        if image:
            self.image = image
            self.image = pygame.transform.scale(
                self.image, (dimensions[2], dimensions[3])
            )
        else:
            self.image.fill(colour)

        self.rect = self.image.get_rect(topleft=(dimensions[0], dimensions[1]))

        widget_group.add(self)

    def update(self, *args, **kwargs) -> None:
        screen.blit(self.image, self.rect)
        create_text(self.tag, BLACK, self.rect.center)

    def on_click(self, *args, **kwargs) -> None:
        self.toggles = (self.toggles + 1) % self.toggle_periodicity
        if self.toggles != 0:
            self.toggled = True
        else:
            self.toggled = False
        self.function()


class ToggleButton(Button):
    """
    This is for buttons with a toggle periodicity of 2, used for when functions occur
    when toggled hence the name :)

    :param status: the name of the button followed by the toggled text
    :param dimensions: tuple(top, left, width, height)
    :param function: any procedure, should not return
    :param colours: the original colour followed by the toggled colour
    """

    def __init__(
        self,
        status: tuple,
        dimensions: tuple,
        function: Callable[..., None],
        colours: Optional[tuple] = None,
        image: Optional[Surface] = None,
        reverse: bool = False,
    ):
        super(ToggleButton, self).__init__(
            status[0],
            dimensions,
            function,
            colour=colours[0] if colours else None,
            image=image,
        )

        self.reverse = reverse
        self.status = status
        self.colours = colours
        self.object_image = image

    def on_toggle(self, index):
        if not self.object_image:
            self.image.fill(self.colours[index])
        self.tag = self.status[index]
        if (index == 1 and not self.reverse) or (index == 0 and self.reverse):
            self.function()

    def update(self, *args, **kwargs) -> None:
        if self.toggled:
            self.on_toggle(1)
        else:
            self.on_toggle(0)
        screen.blit(self.image, self.rect)
        create_text(self.tag, BLACK, self.rect.center)

    def on_click(self, *args, **kwargs) -> None:
        self.toggled = not self.toggled


tabs = pygame.sprite.Group()


class Tab(SpriteHandler):
    def __init__(self):
        super(Tab, self).__init__()

        self.sliders_x = pygame.sprite.Group(
            Slider("amplitude x", 1, 0.1, 5, 1),
            Slider("frequency x", 2, 1, 10, 3),
            Slider("phase x", 3, 0, round(sympy.pi * 2, 3), sympy.pi / 2),
            Slider("damping x", 4, 0, 2, 0),
        )

        self.sliders_y = pygame.sprite.Group(
            Slider("amplitude y", 5, 0.1, 5, 1),
            Slider("frequency y", 6, 1, 10, 2),
            Slider("phase y", 7, 0, round(sympy.pi * 2, 3), 0),
            Slider("damping y", 8, 0, 2, 0),
        )

        self.all_sliders = pygame.sprite.Group(
            *self.sliders_x.sprites(), *self.sliders_y.sprites()
        )

        self.index = len(tabs) + 1
        self.slider_rects = [
            slider_sprite.rect for slider_sprite in self.all_sliders.sprites()
        ]
        self.rect = self.slider_rects[0].unionall(self.slider_rects)
        self.image = Surface(self.rect.size)

        self.panel = ToggleButton(
            (str(self.index), str(self.index)),
            (self.index * 50, 275, 50, 50),
            self.update_buffer,
            (WHITE, (255, 0, 255)),
        )

    def update_buffer(self):
        print(tabs.sprites())
        for tab in tabs.sprites():
            if tab != self:
                tab.panel.toggled = False

        pygame.gfxdraw.rectangle(screen, self.rect, WHITE)

    def update(self, *args, **kwargs) -> None:
        for slider in self.all_sliders.sprites():
            slider.active = self.panel.toggled and menu_btn.toggled


class Menu(SpriteHandler):
    def __init__(self):
        super(Menu, self).__init__()

        self.tab_button = Button(
            "+",
            (0, 275, 50, 50),
            self.create_tab,
            WHITE,
        )

        self.rect = self.tab_button.rect.unionall(
            [tab.panel.rect for tab in tabs.sprites()]
        )
        self.image = Surface(self.rect.size)

        self.tab_created_event = pygame.event.Event(TAB_CREATED)
        self.create_tab()

    def create_tab(self):
        if len(tabs) == 3:
            return

        tabs.add(Tab())
        self.rect.width += 50
        self.image = Surface(self.rect.size)
        pygame.event.post(self.tab_created_event)


class Canvas(SpriteHandler):
    """
    This is where the harmonograph is drawn, the update function draws each point
    at each frame, and based on the distance between the point and if the sliders move,
    the pen will adjust and try to keep things neat :)
    """

    def __init__(self):
        super(Canvas, self).__init__()

        self.image = Surface((500, 500))
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))

        self.x_expr = 0
        self.y_expr = 0
        self.x = sympy.Function("x")
        self.y = sympy.Function("y")

        self.last_point = ()

        self.SUBS_CONSTS = [A, F, P, D]
        self.update_coords()

    def update_coords(self):
        self.x_expr = 0
        self.y_expr = 0

        for tab in tabs.sprites():
            x_values = [sl_x.value for sl_x in tab.sliders_x.sprites()]
            self.x_expr += PENDULUM_EXPR.xreplace(dict(zip(self.SUBS_CONSTS, x_values)))

            y_values = [sl_y.value for sl_y in tab.sliders_y.sprites()]
            self.y_expr += PENDULUM_EXPR.xreplace(dict(zip(self.SUBS_CONSTS, y_values)))

        self.x = sympy.lambdify(T, self.x_expr)
        self.y = sympy.lambdify(T, self.y_expr)

    def coords_at_time(self, t):
        return self.x(t), self.y(t)

    def update(self, *args, **kwargs) -> None:

        fill_rect = Rect(0, 0, 740, 51)
        fill_rect.center = (SCREEN_WIDTH / 2, 38)
        screen.fill(BLACK, fill_rect)

        create_text(
            "x(t) = {}".format(sympy.pretty(self.x_expr / 50).replace("⋅", "")),
            WHITE,
            (SCREEN_WIDTH / 2, 25),
        )
        create_text(
            "y(t) = {}".format(sympy.pretty(self.y_expr / 50).replace("⋅", "")),
            WHITE,
            (SCREEN_WIDTH / 2, 50),
        )

        curr_point = curr_x, curr_y = self.coords_at_time(time)

        if self.last_point:
            x1, y1 = tp(self.last_point)
            x2, y2 = tp(curr_point)
            pygame.gfxdraw.line(screen, x1, y1, x2, y2, (0, 255, 0))

        next_values = next_x, next_y = self.coords_at_time(time + speed / FPS)
        self.last_point = next_values

        point_distance = sympy.sqrt(((curr_x - next_x) ** 2) + ((curr_y - next_y) ** 2))

        step = 1
        points = [curr_point, next_values]

        while point_distance > 1:
            next_stamp = speed / FPS / (2 ** step)
            general_point = self.coords_at_time(time + next_stamp)

            for s in range(1, 2 ** step, 2):
                varying_point = time + s * next_stamp
                vertex = self.coords_at_time(varying_point)
                points.insert(1, vertex)

            point_distance = sympy.sqrt(
                ((curr_x - general_point[0]) ** 2) + ((curr_y - general_point[1]) ** 2)
            )
            step += 1

        def round_points(point):
            return tuple(map(round, point))

        points = list(map(round_points, points))
        for p in points:
            p_x, p_y = tp(p)
            pygame.gfxdraw.pixel(screen, p_x, p_y, (0, 255, 0))


menu = Menu()
canvas = Canvas()


# Converts cartesian coordinates to pygame
def tp(coordinate):
    return (
        (SCREEN_WIDTH // 2) + int(coordinate[0]),
        (SCREEN_HEIGHT // 2) - int(coordinate[1]),
    )


def fill_black():
    screen.fill(BLACK)


def inc_speed():
    global speed
    if speed == 128:
        speed = 1
    else:
        speed *= 2


quit_btn = Button("Quit", (80, 10, 60, 60), pygame.quit, (255, 0, 0))
cls_btn = Button(
    "Clear", (220, 10, 60, 60), fill_black, (0, 0, 255), toggle_periodicity=1
)
spd_btn = Button(
    "Speed", (290, 10, 60, 60), inc_speed, (255, 255, 0), toggle_periodicity=7
)
menu_btn = ToggleButton(
    ("Menu", "Close"),
    (10, 10, 60, 60),
    menu.update,
    image=pygame.image.load("home_icon.png"),
)

pause_btn = ToggleButton(
    ("Pause", "Paused"),
    (150, 10, 60, 60),
    canvas.update,
    ((0, 255, 0), (255, 0, 0)),
    reverse=True,
)

running = True
while running:
    screen.fill(
        (0, 0, 0),
        (menu.rect.left, menu.rect.top - 50, menu.rect.width, menu.rect.height + 50),
    )
    screen.fill(BLACK, tabs.sprites()[0].rect)
    mouse_pos = pygame.mouse.get_pos()

    menu.tab_button.active = menu_btn.toggled
    for tab in tabs.sprites():
        tab.panel.active = menu_btn.toggled

    # Event handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            for widget in widget_group.sprites():
                if widget.rect.collidepoint(mouse_pos) and widget.active:
                    widget.on_click(mouse_pos)
        if event.type == SLIDER_MOVED or TAB_CREATED:
            canvas.update_coords()

    if pygame.mouse.get_pressed(3)[0]:
        for widget in widget_group.sprites():
            if widget.rect.collidepoint(mouse_pos) and widget.active:
                widget.on_drag(mouse_pos, show=menu_btn.toggled)

    for widget in widget_group.sprites():
        if widget.active:
            widget.update()

    tabs.update()

    if not pause_btn.toggled:
        time += speed / FPS
    clock.tick(FPS)
    pygame.display.flip()

pygame.quit()
