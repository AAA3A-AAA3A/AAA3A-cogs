from .cogsutils import CogsUtils, Captcha, Loop, Reactions, Menu  # isort:ignore

if CogsUtils().is_dpy2:
    from .cogsutils import Buttons, Dropdown, Select, Modal  # isort:ignore

__author__ = "AAA3A"