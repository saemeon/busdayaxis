from matplotlib import scale as mscale

from ._locator import BusdayLocator
from ._scale import BusdayScale


def register_scale():
    mscale.register_scale(BusdayScale)


__all__ = ["BusdayScale", "BusdayLocator", "register_scale"]

__version__ = "0.1.0"
