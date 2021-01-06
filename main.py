from collections import namedtuple

import pygame
from pygame import Rect
from pygame.font import Font
from random import randint
from typing import Union
import sys
import math
from math import sin, pi, sqrt
from dataclasses import dataclass, astuple
import colorsys

# Initialises the pygame module
pygame.init()

# Common colours
black = 0, 0, 0
white = 255, 255, 255
screen = pygame.display.set_mode(flags=pygame.FULLSCREEN)
size = w, h, = (
    pygame.display.Info().current_w,
    pygame.display.Info().current_h,
)

# Manage frame rate
clock = pygame.time.Clock()
fps = 1200
time = 0
paused = False
speed = 1


@dataclass()
class Text:
    text_obj: Font
    text_rect: Rect


def text(font, text, colour, center):
    t = font.render(text, True, colour)
    t_r = t.get_rect(center=center)
    return Text(t, t_r)


def darken(colour: tuple, percent=0):
    r, g, b = colour
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    v = (v - (0.2 if percent == 0 else percent)) if (v >= 0.2 and percent) else 0
    return tuple(map(lambda x: x * 255, list(colorsys.hsv_to_rgb(h, s, v))))


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


@dataclass
class SliderInfo:
    min_val: float
    max_val: float
    default: float


SLIDER_MOVED = pygame.USEREVENT + 1
CONTAINER_HOVER = pygame.USEREVENT + 2


class Container:
    def __init__(
        self, tag: str, container_size: tuple[int, int], center: tuple[int, int]
    ):
        self.container_rect = Rect((0, 0), container_size)
        self.container_rect.center = center
        self.container_event = pygame.event.Event(CONTAINER_HOVER, name=tag)
        self.size = size

    def is_hover(self):
        if self.container_rect.collidepoint(pygame.mouse.get_pos()):
            return True
        else:
            return False


class Widget(Container):
    def __init__(self, tag, rects: list[Rect], texts: list[Text], function):
        self.function = function
        self.widget_rect = rects[0].unionall(rects + [text.text_rect for text in texts])
        self.rects = rects
        self.texts = texts

        super(Widget, self).__init__(
            tag, self.widget_rect.size, self.widget_rect.center
        )

    def on_click(self):
        if self.is_hover() and pygame.mouse.get_pressed()[0]:
            self.function()

    def draw(self, colour=white):
        for rect in self.rects:
            pygame.draw.rect(screen, colour, rect)
        for text in self.texts:
            screen.blit(text.text_obj, text.text_rect)


class Slider(Widget):
    def __init__(self, tag, min_val, max_val, index, default, function=None):
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
            h - (self.i * 70) + 30,
        )

        self.line_rect = Rect((50, self.r.centery), (201, 1))
        self.rects = [self.r, self.line_rect]

        self.font = pygame.font.SysFont("Arial", 15)
        self.min_val_label = text(
            self.font, str(self.min_val), white, (20, self.r.centery)
        )
        self.max_val_label = text(
            self.font, str(self.max_val), white, (280, self.r.centery)
        )
        self.tag_label = text(
            self.font, self.tag, white, (self.line_rect.centerx, self.r.centery - 30)
        )
        self.texts = [self.min_val_label, self.max_val_label, self.tag_label]

        super(Slider, self).__init__(tag, self.rects, self.texts, function)

        self.slider_event = pygame.event.Event(SLIDER_MOVED, tag=tag, slider_id=index)
        self.value = self.default
        self.colour = white

    # Moves the slider-ball to chosen position
    def move_rect(self, new_x):

        if 250 > new_x > 50:
            self.r.center = (new_x, self.r.centery)

            self.value = ((self.max_val - self.min_val) / 300) * self.r.centerx

        return self.r.center


class Button(Widget):
    def __init__(self, tag, rect: Rect, function):
        self.font = pygame.font.SysFont("Arial", 15)
        self.tag_label = text(self.font, tag, black, rect.center)
        super(Button, self).__init__(tag, [rect], [self.tag_label], function)


slider_info = {
    "amplitude x": SliderInfo(0.1, 5, 1),
    "frequency x": SliderInfo(1, 10, 3),
    "phase x": SliderInfo(0, round(math.pi * 2, 3), math.pi / 2),
    "damping x": SliderInfo(0, 2, 0),
    "amplitude y": SliderInfo(0.1, 5, 1),
    "frequency y": SliderInfo(1, 10, 2),
    "phase y": SliderInfo(0, round(math.pi * 2, 3), 0),
    "damping y": SliderInfo(0, 2, 0),
}

# List of sliders
sliders = []
keys = list(slider_info.keys())

# Creates a set of x names and y names for the sliders
# Also gives each slider an index number (to identify and position)
for i in range(0, 8):
    key = keys[i]
    value = slider_info[keys[i]]
    sliders.append(Slider(key, value.min_val, value.max_val, i + 1, value.default))


# container_size = sum(slider.container.height for slider in sliders) / 2, sum(slider.container.width for slider in sliders) / 2
# container_rect = Rect(sliders[len(sliders)-1].container.topleft, container_size)
# pygame.draw.rect(screen, (255, 255, 255), container_rect)


# Converts cartesian coordinates to pygame
def tp(coordinate, screen_size):
    return (
        (screen_size[0] // 2) + coordinate[0],
        (screen_size[1] // 2) - coordinate[1],
    )


def pause():
    global paused
    if not paused:
        paused = True
    else:
        paused = False


def fill_black():
    screen.fill(black)


def inc_speed():
    global speed
    if speed == 128:
        speed = 1
    else:
        speed *= 2


quit_btn = Button("Quit", Rect(10, 10, 60, 60), pygame.quit)
pause = Button("Pause", Rect(80, 10, 60, 60), pause)
cls = Button("Clear", Rect(150, 10, 60, 60), fill_black)
spd = Button("Speed", Rect(220, 10, 60, 60), inc_speed)

last_point = ()
running = True
while running:
    screen.fill((0, 0, 0), (0, 70, 300, h))

    # Event handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            quit_btn.on_click()
            pause.on_click()
            cls.on_click()
            spd.on_click()

    quit_btn.draw((255, 0, 0))
    x = Pendulum(sliders[0].value, sliders[1].value, sliders[2].value, sliders[3].value)
    y = Pendulum(sliders[4].value, sliders[5].value, sliders[6].value, sliders[7].value)

    for slider in sliders:
        slider.draw()
        # Triggers if the mouse is hovering over the slider-ball
        if slider.is_hover():
            slider.colour = darken(slider.colour)
            if pygame.mouse.get_pressed()[0]:
                slider.move_rect(pygame.mouse.get_pos()[0])
                pygame.event.post(slider.slider_event)

        else:
            slider.colour = white

    if not paused:

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
            pygame.draw.line(
                screen, (0, 255, 0), tp(last_point, size), tp(curr_values, size), 2
            )
        next_values = next_x, next_y = x.get_value(time + speed / fps), y.get_value(
            time + speed / fps
        )
        last_point = next_values

        point_distance = sqrt(((curr_x - next_x) ** 2) + ((curr_y - next_y) ** 2))

        step = 1
        points = [curr_values, next_values]

        while point_distance > 1:
            next_stamp = speed / fps / (2 ** step)
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
            pygame.draw.circle(screen, (0, 255, 0), tp(p, size), 1)

        time += speed / fps

    pause.draw((0, 255, 0))
    cls.draw((0, 0, 255))
    spd.draw((255, 255, 0))

    # Draws each slider

    clock.tick(fps)

    pygame.display.flip()  # Updates the display

pygame.quit()
