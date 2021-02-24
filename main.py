import colorsys
import math
from collections import namedtuple
from tkinter import colorchooser, Tk
from typing import Optional, Callable

import pygame
import pygame.gfxdraw
import sympy
from pygame import Rect, Surface
from pygame.sprite import Group, Sprite

pygame.init()  # Initialises Pygame
Tk().withdraw()  # Stops the tkinter window from opening

# Common colours
BLACK = 0, 0, 0
WHITE = 255, 255, 255

# Display settings
SCREEN_SIZE = SCREEN_WIDTH, SCREEN_HEIGHT = 1440, 900
SCREEN = pygame.display.set_mode(SCREEN_SIZE)

# Manage frame rate
CLOCK = pygame.time.Clock()
FPS = 1200
time = 0
speed = 1

A, F, P, D, T = sympy.symbols("a, f, p, d, t")
PENDULUM_EXPR = 50 * A * sympy.sin(T * F + P) * sympy.exp(-D * T)
point = namedtuple("Point", ["x", "y"])

font = pygame.font.Font("arial-unicode-ms.ttf", 15)
curve_colour = (0, 255, 0)


def create_text(text: str, colour: tuple, center: tuple, display=True):
    """
    Creates text and displays it at the given center

    :param text: any text string
    :param colour: r, g, b colours
    :param center: location to display text
    :param display: do screen.blit immediately
    :return: the text Rect object
    """

    t = font.render(text, True, colour)
    t_r = t.get_rect(center=center)
    if display:
        SCREEN.blit(t, t_r)
    return t, t_r


def darken(colour: tuple, percent=0):
    """
    This darkens any colour by converting rgb co-ordinates to its hsv equivalent,
    then it reduces the value by 20%

    :param colour:
    :param percent:
    :return: new darkened colour in rgb values
    """

    r, g, b = colour
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    v = (v - (0.2 if percent == 0 else percent)) if (v >= 0.2 and percent) else 0
    return tuple(map(lambda x: x * 255, list(colorsys.hsv_to_rgb(SCREEN_HEIGHT, s, v))))


def pretty_print(string):
    """
    This is used for printing expressions nicely

    :param string: expressions string
    :return: new pretty printed string
    """

    return string.replace("exp(", "e^(").replace("*", "")


def round_expr(expr):
    """
    In SymPy, an expression is a tree of operations, this method uses the
    pre-order traversal algorithm to access each Float in the tree and then
    rounds it appropriately to 3 decimal places

    :param expr:
    :return:
    """

    new_expr = expr
    for node in sympy.preorder_traversal(expr):
        if isinstance(node, sympy.Float):
            new_expr = new_expr.subs(node, round(node, 3))
    return new_expr


SLIDER_MOVED = pygame.USEREVENT + 1
SPRITE_HOVER = pygame.USEREVENT + 2
TAB_CREATED = pygame.USEREVENT + 3

all_sprites = Group()
widget_group = Group()


class ModifiedSprite(Sprite):
    def __init__(self, tooltip: Optional[str] = None):
        """
        Modified Sprite object with click and drag functions. Also contains a tooltip
        function for all Sprites.

        :param tooltip: string that displays information about to the sprite
        """

        super(ModifiedSprite, self).__init__()

        all_sprites.add(self)

        self.active = True
        self.tooltip = tooltip

        if self.tooltip:
            self.tooltip = tooltip.split(" ")
            self.tooltip = [
                " ".join(self.tooltip[i: i + 7])
                for i in range(0, len(self.tooltip), 7)
            ]

    def on_click(self, *args, **kwargs) -> None:
        pass

    def on_drag(self, *args, **kwargs) -> None:
        pass

    def show_tooltip(self, mouse_position) -> None:
        if self.tooltip:

            objects = []
            for i, group in enumerate(self.tooltip):
                tooltip_surf, tooltip_rect = create_text(
                    group,
                    BLACK,
                    (mouse_position[0] + 100, mouse_position[1] + 10 + (15 * i)),
                    False,
                )
                objects.append((tooltip_surf, tooltip_rect))

            box = objects[0][1].unionall([i[1] for i in objects])
            if box.colliderect(canvas.rect):
                return
            pygame.gfxdraw.box(SCREEN, box, WHITE)
            for obj in objects:
                SCREEN.blit(*obj)


class Slider(ModifiedSprite):
    def __init__(
            self,
            tag: str,
            index: int,
            min_val: float,
            max_val: float,
            default: float,
            tooltip: Optional[str] = None,
    ):
        """
        Slider object with a bar and a ball. When the ball is moved,
        the values are updated in respect to its relative position.

        :param tag: the name of the slider
        :param index: identified used to position the slider
        :param min_val: the minimum value
        :param max_val: the maximum value
        :param default: the sliders default settings
        """

        super(Slider, self).__init__(tooltip)

        self.min_val = min_val
        self.max_val = max_val
        self.i = index
        self.tag = tag
        self.default = default

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

        pygame.gfxdraw.box(SCREEN, self.r, WHITE)
        pygame.gfxdraw.hline(SCREEN, 50, 250, self.r.centery, WHITE)

    def on_drag(self, mouse_position, **kwargs) -> None:
        """
        Updates the slider's position and reassigns a new value to it.

        :param mouse_position: the cursor location
        :param kwargs: show - runs the function if the slider is active
        """

        if kwargs["show"]:
            new_x = mouse_position[0]
            if 250 > new_x > 50:
                self.r.center = (new_x, self.r.centery)
                self.value = ((self.max_val - self.min_val) / 300) * self.r.centerx

            pygame.event.post(self.slider_event)


class Button(ModifiedSprite):
    def __init__(
            self,
            tag: str,
            dimensions: tuple,
            function: Callable[..., None],
            colour: Optional[tuple] = None,
            image: Optional[Surface] = None,
            toggle_periodicity: int = 2,
            tooltip: Optional[str] = None,
    ):
        """
        Main Button class for when things happen when its clicked, doesn't constantly
        do the function call, see ToggleButton for this functionality

        :param tag: the name of the Button
        :param dimensions: tuple(top, left, width, height)
        :param function: any procedure, should not return
        :param colour: the colour of the Button
        :param image: the surface object of the loaded image
        :param toggle_periodicity: how many clicks to turn off
        """

        super(Button, self).__init__(tooltip)
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
        SCREEN.blit(self.image, self.rect)
        create_text(self.tag, BLACK, self.rect.center)

    def on_click(self, *args, **kwargs) -> None:
        self.toggles = (self.toggles + 1) % self.toggle_periodicity
        if self.toggles != 0:
            self.toggled = True
        else:
            self.toggled = False
        self.function()


class ToggleButton(Button):
    def __init__(
            self,
            status: tuple,
            dimensions: tuple,
            function: Callable[..., None],
            colours: Optional[tuple] = None,
            image: Optional[Surface] = None,
            reverse: bool = False,
            tooltip: Optional[str] = None,
    ):
        """
        This is for buttons with a toggle periodicity of 2, used for when functions occur
        when toggled hence the name :)

        :param status: the name of the button followed by the toggled text
        :param dimensions: tuple(top, left, width, height)
        :param function: any procedure, should not return
        :param colours: the original colour followed by the toggled colour
        :param image: the surface object of the loaded image
        :param reverse: if reversed, the function will call will happen while off.
        """

        super(ToggleButton, self).__init__(
            status[0],
            dimensions,
            function,
            colour=colours[0] if colours else None,
            image=image,
            tooltip=tooltip,
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
        SCREEN.blit(self.image, self.rect)
        create_text(self.tag, BLACK, self.rect.center)

    def on_click(self, *args, **kwargs) -> None:
        self.toggled = not self.toggled


tabs = Group()


class Tab(ModifiedSprite):
    def __init__(self, tooltip: Optional[str] = None):
        """
        A single tab, that when clicked opens a bunch of sliders to play around with.
        """

        super(Tab, self).__init__(tooltip)

        self.sliders_x = pygame.sprite.Group(
            Slider(
                "amplitude x",
                1,
                0.1,
                5,
                1,
                tooltip="Changes the size of the curve in the x-direction.",
            ),
            Slider(
                "frequency x",
                2,
                1,
                10,
                3,
                tooltip="Changes the amount of oscillations the pendulum makes.",
            ),
            Slider(
                "phase x",
                3,
                0,
                round(sympy.pi * 2, 3),
                sympy.pi / 2,
                tooltip="Delays the start of the pendulum by the phase angle.",
            ),
            Slider(
                "damping x",
                4,
                0,
                0.01,
                0.005,
                tooltip="Causes the slider to move down to a halt.",
            ),
        )

        self.sliders_y = pygame.sprite.Group(
            Slider(
                "amplitude y",
                5,
                0.1,
                5,
                1,
                tooltip="Changes the size of the curve in the y-direction.",
            ),
            Slider(
                "frequency y",
                6,
                1,
                10,
                2,
                tooltip="Changes the amount of oscillations the pendulum makes.",
            ),
            Slider(
                "phase y",
                7,
                0,
                round(sympy.pi * 2, 3),
                0,
                tooltip="Delays the start of the pendulum by the phase angle.",
            ),
            Slider(
                "damping y",
                8,
                0,
                0.01,
                0.005,
                tooltip="Causes the pendulum to move down to a halt.",
            ),
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
        tab: Tab
        for tab in tabs.sprites():
            if tab != self:
                tab.panel.toggled = False

        pygame.gfxdraw.rectangle(SCREEN, self.rect, WHITE)

    def update(self, *args, **kwargs) -> None:
        for slider in self.all_sliders.sprites():
            slider.active = self.panel.toggled and menu_btn.toggled


class Menu(ModifiedSprite):
    def __init__(self, tooltip: Optional[str] = None):
        """
        The tab manager
        """

        super(Menu, self).__init__(tooltip)

        self.tab_button = Button(
            "+",
            (0, 275, 50, 50),
            self.create_tab,
            WHITE,
        )

        tab: Tab
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


def temp():
    pass


auto_clear_btn = ToggleButton(
    ("Auto Clear OFF", "Auto Clear ON"),
    (10, 80, 130, 60),
    temp,
    ((255, 0, 0), (0, 255, 0)),
    tooltip="Automatically clears the canvas when changes are made",
)


class Canvas(ModifiedSprite):
    def __init__(self, tooltip: Optional[str] = None):
        """
        This is where the harmonograph is drawn, the update function draws each point
        at each frame, and based on the distance between the point and if the sliders move,
        the pen will adjust and try to keep things neat :)
        """

        super(Canvas, self).__init__(tooltip)

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

        tab: Tab
        for tab in tabs.sprites():
            sl_x: Slider
            x_values = [sl_x.value for sl_x in tab.sliders_x.sprites()]
            self.x_expr += PENDULUM_EXPR.xreplace(dict(zip(self.SUBS_CONSTS, x_values)))

            sl_y: Slider
            y_values = [sl_y.value for sl_y in tab.sliders_y.sprites()]
            self.y_expr += PENDULUM_EXPR.xreplace(dict(zip(self.SUBS_CONSTS, y_values)))

        self.x = sympy.lambdify(T, self.x_expr)
        self.y = sympy.lambdify(T, self.y_expr)

        if auto_clear_btn.toggled:
            SCREEN.fill(BLACK)

    def coords_at_time(self, t):
        p = point(self.x(t), self.y(t))
        return p

    def update(self, *args, **kwargs) -> None:

        create_text(
            f"x(t) = {pretty_print(str(round_expr(self.x_expr / 50)))}",
            WHITE,
            (SCREEN_WIDTH / 2, 25),
        )
        create_text(
            f"y(t) = {pretty_print(str(round_expr(self.y_expr / 50)))}",
            WHITE,
            (SCREEN_WIDTH / 2, 50),
        )

        create_text(
            f"Time (t) elapsed: {round(time)}", WHITE, (SCREEN_WIDTH / 2 + 500, 25)
        )

        create_text(
            f"Speed: {speed}x",
            WHITE,
            (SCREEN_WIDTH / 2 + 500, 50),
        )

        pygame.gfxdraw.rectangle(
            SCREEN,
            (470, 200, 500, 500),
            WHITE,
        )

        curr_point = curr_x, curr_y = self.coords_at_time(time)

        if self.last_point:
            x1, y1 = to_pygame(self.last_point)
            x2, y2 = to_pygame(curr_point)
            pygame.gfxdraw.line(SCREEN, x1, y1, x2, y2, curve_colour)

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
            p_x, p_y = to_pygame(p)
            pygame.gfxdraw.pixel(SCREEN, p_x, p_y, curve_colour)


menu = Menu(tooltip="This is the panel for the sliders")
canvas = Canvas()


def to_pygame(coordinate):
    """
    Converts cartesian co-ordinates to its Pygame equivalent

    :param coordinate: the cartesian co-ordinate
    :return: Pygame co-ordinates
    """

    return (
        (SCREEN_WIDTH // 2) + int(coordinate[0]),
        (SCREEN_HEIGHT // 2) - int(coordinate[1]),
    )


def fill_black():
    SCREEN.fill(BLACK)


def inc_speed():
    global speed
    if speed == 128:
        speed = 1
    else:
        speed *= 2


def reset_time():
    global time
    time = 0
    canvas.update_coords()


def choose_colour():
    global curve_colour
    temp_colour = colorchooser.askcolor(title="Colour")
    curve_colour = tuple(map(math.floor, temp_colour[0]))
    canvas.update_coords()


quit_btn = Button(
    "Quit", (80, 10, 60, 60), pygame.quit, (255, 0, 0), tooltip="Click to exit"
)

cls_btn = Button(
    "Clear",
    (220, 10, 60, 60),
    fill_black,
    (0, 0, 255),
    toggle_periodicity=1,
    tooltip="Clears the canvas",
)

spd_btn = Button(
    "Speed",
    (290, 10, 60, 60),
    inc_speed,
    (255, 255, 0),
    toggle_periodicity=7,
    tooltip="Increases the speed of the pen",
)

menu_btn = ToggleButton(
    ("Menu", "Close"),
    (10, 10, 60, 60),
    menu.update,
    image=pygame.image.load("home_icon.png"),
    tooltip="Opens the slider menu, where you can change the properties of the harmonograph",
)

pause_btn = ToggleButton(
    ("Pause", "Paused"),
    (150, 10, 60, 60),
    canvas.update,
    ((0, 255, 0), (255, 0, 0)),
    reverse=True,
    tooltip="Pauses/Unpauses the system",
)

reset_time_btn = Button(
    "Reset time to 0",
    (150, 80, 130, 60),
    reset_time,
    (255, 0, 255),
    tooltip="Resets the time to 0, used for investigating damping",
)

colour_button = Button(
    "Colour",
    (290, 80, 60, 60),
    choose_colour,
    (200, 255, 150),
    tooltip="Changes the colour of the pen",
)

tooltip_button = ToggleButton(
    ("Enable tooltips", "Disable tooltips"),
    (360, 10, 130, 60),
    temp,
    ((210, 180, 255), (255, 180, 210)),
    tooltip="Enable/Disable tooltips",
)

running = True
while running:

    widget: ModifiedSprite
    sprite: ModifiedSprite
    tab: Tab

    SCREEN.fill(BLACK, (0, 0, 470, 900))
    SCREEN.fill(BLACK, (970, 0, 470, 900))
    SCREEN.fill(BLACK, (470, 0, 500, 200))
    SCREEN.fill(BLACK, (470, 700, 500, 200))

    mouse_pos = pygame.mouse.get_pos()

    menu.active = menu_btn.toggled
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
        if event.type == SLIDER_MOVED or event.type == TAB_CREATED:
            canvas.update_coords()

    if pygame.mouse.get_pressed(3)[0]:
        for widget in widget_group.sprites():
            if widget.rect.collidepoint(mouse_pos) and widget.active:
                widget.on_drag(mouse_pos, show=menu_btn.toggled)

    for widget in widget_group.sprites():
        if widget.active:
            widget.update()

    tabs.update()

    for sprite in all_sprites.sprites():
        if (
                sprite.rect.collidepoint(mouse_pos)
                and sprite.active
                and not tooltip_button.toggled
        ):
            sprite.show_tooltip(mouse_pos)

    if not pause_btn.toggled:
        time += speed / FPS
    CLOCK.tick(FPS)
    pygame.display.flip()

pygame.quit()
