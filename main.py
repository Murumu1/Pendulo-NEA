import pygame
from pygame import Rect, Surface
import pygame.gfxdraw

import math
from math import sin, pi, sqrt

from dataclasses import dataclass
import colorsys

from typing import Optional, Callable

# Initialises the pygame module
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
paused = False
speed = 1

font = pygame.font.Font("arial.ttf", 15)


def create_text(text, colour, center):
    t = font.render(text, True, colour)
    t_r = t.get_rect(center=center)
    screen.blit(t, t_r)


def darken(colour: tuple, percent=0):
    r, g, b = colour
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    v = (v - (0.2 if percent == 0 else percent)) if (v >= 0.2 and percent) else 0
    return tuple(map(lambda x: x * 255, list(colorsys.hsv_to_rgb(SCREEN_HEIGHT, s, v))))


# Pendulum class Asin(tf + p)e^-dt
@dataclass
class Pendulum:
    amplitude: float
    frequency: float
    phase: float
    damping: float = 0

    # Returns x, y relative to time (t)
    def get_value(self, t) -> float:
        return (
            self.amplitude
            * 100
            * sin(t * self.frequency + self.phase)
            * pow(math.e, -self.damping * t)
        )


SLIDER_MOVED = pygame.USEREVENT + 1
SPRITE_HOVER = pygame.USEREVENT + 2

all_sprites = pygame.sprite.Group()
widget_group = pygame.sprite.Group()
slider_group = pygame.sprite.Group()
button_group = pygame.sprite.Group()


class SpriteHandler(pygame.sprite.Sprite):
    def __init__(self):
        super(SpriteHandler, self).__init__()

        self.sprite_hover = pygame.event.Event(
            SPRITE_HOVER, name=self.__class__.__name__
        )

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

        slider_group.add(self)
        widget_group.add(self)

    def update(self, *args, **kwargs) -> None:
        create_text(str(self.min_val), WHITE, (20, self.r.centery))
        create_text(str(self.max_val), WHITE, (280, self.r.centery))
        create_text(self.tag, WHITE, (150, self.r.centery - 30))

        pygame.gfxdraw.box(screen, self.r, WHITE)
        pygame.gfxdraw.hline(screen, 50, 250, self.r.centery, WHITE)

    # Moves the slider-ball to chosen position
    def on_drag(self, mouse_position, **kwargs):
        if kwargs['show']:
            new_x = mouse_position[0]
            if 250 > new_x > 50:
                self.r.center = (new_x, self.r.centery)
                self.value = ((self.max_val - self.min_val) / 300) * self.r.centerx


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

        button_group.add(self)
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


class Tab(SpriteHandler):
    no_of_tabs = 0

    def __init__(self):
        super(Tab, self).__init__()

        Tab.no_of_tabs += 1
        self.sliders = slider_group
        self.widget_rects = [
            slider_sprite.rect for slider_sprite in self.sliders.sprites()
        ]
        self.rect = self.widget_rects[0].unionall(self.widget_rects)
        self.image = Surface(self.rect.size)

        # fix this garbo make an actual panel, this only makes a single tab
        self.panel = Button(str(Tab.no_of_tabs), (Tab.no_of_tabs * 50, 275, 50, 50), self.update_buffer, WHITE)
        button_group.remove(self.panel)
        widget_group.remove(self.panel)

    def update_buffer(self):
        pygame.gfxdraw.rectangle(screen, self.rect, WHITE)
        self.sliders.update()

    def update(self, *args, **kwargs) -> None:
        self.panel.update()


class Menu(SpriteHandler):
    def __init__(self):
        super(Menu, self).__init__()
        # generalise this or smth
        self.sliders = slider_group
        self.widget_rects = [
            slider_sprite.rect for slider_sprite in self.sliders.sprites()
        ]
        self.rect = self.widget_rects[0].unionall(self.widget_rects)
        self.image = Surface(self.rect.size)

        self.tabs = pygame.sprite.Group(Tab())
        self.tab_button = Button("+", (self.rect.left + 50, self.rect.top - 50, 50, 50), self.create_tab, WHITE)
        button_group.remove(self.tab_button)
        widget_group.remove(self.tab_button)

        print(self.rect)

    def create_tab(self):
        self.tabs.add(Tab())

    def update(self, *args, **kwargs) -> None:
        self.tab_button.update()
        self.tabs.update()


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

    def update(self, *args, **kwargs) -> None:
        global time, last_point, x, y

        # Draws each point of the Harmonograph
        if SLIDER_MOVED in (ev.type for ev in pygame.event.get()):
            x = Pendulum(
                sliders[0].value, sliders[1].value, sliders[2].value, sliders[3].value
            )
            y = Pendulum(
                sliders[4].value, sliders[5].value, sliders[6].value, sliders[7].value
            )

        curr_values = curr_x, curr_y = x.get_value(time), y.get_value(time)
        if last_point:
            x1, y1 = tp(last_point)
            x2, y2 = tp(curr_values)
            pygame.gfxdraw.line(screen, x1, y1, x2, y2, (0, 255, 0))
        next_values = next_x, next_y = x.get_value(time + speed / FPS), y.get_value(
            time + speed / FPS
        )
        last_point = next_values

        point_distance = sqrt(((curr_x - next_x) ** 2) + ((curr_y - next_y) ** 2))

        step = 1
        points = [curr_values, next_values]

        while point_distance > 1:
            next_stamp = speed / FPS / (2 ** step)
            general_point = x.get_value(time + next_stamp), y.get_value(
                time + next_stamp
            )

            for s in range(1, 2 ** step, 2):
                varying_point = time + s * next_stamp
                vertex = x.get_value(varying_point), y.get_value(varying_point)
                points.insert(1, vertex)

            point_distance = sqrt(
                ((curr_x - general_point[0]) ** 2) + ((curr_y - general_point[1]) ** 2)
            )
            step += 1

        def round_points(point):
            return tuple(map(round, point))

        points = list(map(round_points, points))
        for p in points:
            p_x, p_y = tp(p)
            pygame.gfxdraw.pixel(screen, p_x, p_y, (0, 255, 0))

        time += speed / FPS


slider_info = {
    "amplitude x": (0.1, 5, 1),
    "frequency x": (1, 10, 3),
    "phase x": (0, round(pi * 2, 3), pi / 2),
    "damping x": (0, 2, 0),
    "amplitude y": (0.1, 5, 1),
    "frequency y": (1, 10, 2),
    "phase y": (0, round(pi * 2, 3), 0),
    "damping y": (0, 2, 0),
}

# List of sliders
sliders = []
keys = list(slider_info.keys())

# Creates a set of x names and y names for the sliders
# Also gives each slider an index number (to identify and position)
for i in range(0, 8):
    key = keys[i]
    value = slider_info[keys[i]]
    sliders.append(Slider(key, i + 1, *value))


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


def temp():
    pass


last_point = ()
running = True
while running:
    screen.fill((0, 0, 0), (menu.rect.left, menu.rect.top - 50, menu.rect.width, menu.rect.height + 50))
    mouse_pos = pygame.mouse.get_pos()

    # Event handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            for widget in widget_group.sprites():
                if widget.rect.collidepoint(mouse_pos):
                    widget.on_click(mouse_pos)

    if pygame.mouse.get_pressed(3)[0]:
        for widget in widget_group.sprites():
            if widget.rect.collidepoint(mouse_pos):
                widget.on_drag(mouse_pos, show=menu_btn.toggled)

    # menu_btn.draw()
    x = Pendulum(sliders[0].value, sliders[1].value, sliders[2].value, sliders[3].value)
    y = Pendulum(sliders[4].value, sliders[5].value, sliders[6].value, sliders[7].value)

    button_group.update()

    # Draws each slider

    clock.tick(FPS)

    pygame.display.flip()  # Updates the display

pygame.quit()
