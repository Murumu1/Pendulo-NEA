from collections import namedtuple

import pygame

import sys
import math
from math import sin, pi, sqrt
from dataclasses import dataclass
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


def text(screen, font, text, colour, x, y):
    t = font.render(text, True, colour)
    t_r = t.get_rect(center=(x, y))
    screen.blit(t, t_r)


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
        return self.amplitude * 100 * sin(t * self.frequency + self.phase) * pow(math.e, -self.damping * t)


@dataclass
class SliderInfo:
    min_val: float
    max_val: float
    default: float


# Slider class to manage changing values (i is the index of the Slider)
SLIDER_MOVED = pygame.USEREVENT + 1
slider_event = pygame.event.Event(SLIDER_MOVED, name="SLIDER_MOVED")


class Widget:
    def __init__(self, tag, size):
        self.tag = tag
        self.size = size


class Slider:
    def __init__(self, name, min_val, max_val, i, default):
        self.min_val = min_val
        self.max_val = max_val
        self.i = i
        self.name = name
        self.default = default

        # x positions
        self.bar_start = 50
        self.bar_end = 250
        self.bar_length = self.bar_start + self.bar_end

        # Rect object which is the slider-ball
        self.r = pygame.Rect((0, 0), (30, 30))
        self.r.center = (
            ((self.default * self.bar_length) / (self.max_val - self.min_val)) + 50,
            h - (self.i * 70) + 30,
        )

        self.container = pygame.Rect((0, 0), (self.bar_length, 70))
        self.container.center = (self.bar_length / 2, self.r.centery)

        self.value = self.default
        self.colour = white
        self.font = pygame.font.SysFont("Arial", 15)

    def draw(self):

        # Draws the line for the slider-ball to follow
        l = pygame.draw.line(
            screen,
            white,
            (self.bar_start, self.r.centery),
            (self.bar_end, self.r.centery),
        )

        # Name of the slider
        text(screen, self.font, self.name, white, l.center[0], self.r.centery - 30)

        # Minimum value text
        text(
            screen,
            self.font,
            str(self.min_val),
            white,
            self.bar_start - 30,
            self.r.centery,
        )

        # Maximum value text
        text(
            screen,
            self.font,
            str(self.max_val),
            white,
            self.bar_end + 30,
            self.r.centery,
        )

        # Triggers if the mouse is hovering over the slider-ball
        if (
            self.r.left < pygame.mouse.get_pos()[0] < self.r.left + 30
            and self.r.top < pygame.mouse.get_pos()[1] < self.r.top + 30
        ):

            pygame.draw.rect(screen, darken(self.colour), self.r)

            if pygame.mouse.get_pressed()[0]:
                self.move_rect(pygame.mouse.get_pos()[0])

        else:

            pygame.draw.rect(screen, self.colour, self.r)

    # Moves the slider-ball to chosen position

    def move_rect(self, new_x):

        if self.bar_end > new_x > self.bar_start:
            self.r.center = (new_x, self.r.centery)

            self.value = (
                (self.max_val - self.min_val) / self.bar_length
            ) * self.r.centerx

        return self.r.center


class Button:
    def __init__(self, rect, func):
        self.rect = pygame.Rect(rect)
        self.func = func

    def draw(self, col):
        if (
            self.rect.left
            < pygame.mouse.get_pos()[0]
            < self.rect.left + self.rect.width
            and self.rect.top
            < pygame.mouse.get_pos()[1]
            < self.rect.top + self.rect.height
        ):
            pygame.draw.rect(screen, darken(col), self.rect)
        else:
            pygame.draw.rect(screen, col, self.rect)

    def call(self):
        if (
            self.rect.left
            < pygame.mouse.get_pos()[0]
            < self.rect.left + self.rect.width
            and self.rect.top
            < pygame.mouse.get_pos()[1]
            < self.rect.top + self.rect.height
        ):
            self.func()


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


container_size = sum(slider.container.height for slider in sliders) / 2, sum(slider.container.width for slider in sliders) / 2
container_rect = pygame.Rect(sliders[len(sliders)-1].container.topleft, container_size)
pygame.draw.rect(screen, (255, 255, 255), container_rect)


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


quit_btn = Button((10, 10, 60, 60), pygame.quit)
pause = Button((80, 10, 60, 60), pause)
cls = Button((150, 10, 60, 60), fill_black)
spd = Button((220, 10, 60, 60), inc_speed)

last_point = ()
while 1:
    screen.fill((0, 0, 0), (0, 70, 300, h))

    # Event handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            quit_btn.call()
            pause.call()
            cls.call()
            spd.call()

    quit_btn.draw((255, 0, 0))
    x = Pendulum(sliders[0].value, sliders[1].value, sliders[2].value, sliders[3].value)
    y = Pendulum(sliders[4].value, sliders[5].value, sliders[6].value, sliders[7].value)

    for slider in sliders:
        slider.draw()
        # Triggers if the mouse is hovering over the slider-ball

        if (
            slider.r.left < pygame.mouse.get_pos()[0] < slider.r.left + 30
            and slider.r.top < pygame.mouse.get_pos()[1] < slider.r.top + 30
        ):

            slider.colour = darken(slider.colour)
            if pygame.mouse.get_pressed()[0]:
                slider.move_rect(pygame.mouse.get_pos()[0])
                pygame.event.post(slider_event)

        else:
            slider.colour = white

    if not paused:

        # Draws each point of the Harmonograph
        if SLIDER_MOVED in (ev.type for ev in pygame.event.get()):
            x = Pendulum(sliders[0].value, sliders[1].value, sliders[2].value, sliders[3].value)
            y = Pendulum(sliders[4].value, sliders[5].value, sliders[6].value, sliders[7].value)

        curr_values = curr_x, curr_y = x.get_value(time), y.get_value(time)
        if last_point:
            pygame.draw.line(screen, (0, 255, 0), tp(last_point, size), tp(curr_values, size), 2)
        next_values = next_x, next_y = x.get_value(time + speed / fps), y.get_value(time + speed / fps)
        last_point = next_values

        point_distance = sqrt(((curr_x - next_x) ** 2) + ((curr_y - next_y) ** 2))

        step = 1
        points = [curr_values, next_values]

        while point_distance > 1:
            next_stamp = speed / fps / (2 ** step)
            general_point = x.get_value(time + next_stamp), y.get_value(time + next_stamp)

            for s in range(1, 2 ** step, 2):
                varying_point = time + s * next_stamp
                vertex = x.get_value(varying_point), y.get_value(varying_point)
                points.insert(1, vertex)

            point_distance = sqrt(((curr_x - general_point[0]) ** 2) + ((curr_y - general_point[1]) ** 2))
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
