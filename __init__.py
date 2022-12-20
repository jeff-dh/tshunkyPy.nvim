from .nvimPlugin import NvimPlugin


# fix pynvim issue
import pynvim
import logging
for h in logging.root.handlers:
    if isinstance(h, pynvim.NullHandler):
        logging.root.removeHandler(h)

