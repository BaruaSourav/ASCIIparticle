"""ASCIIparticle: a small terminal game engine built around particles and sprites."""
from .canvas import Canvas
from .color import DEFAULT, gradient, hex_color, rgb
from .engine import Engine, Entity, Scene, overlaps
from .forces import Attractor, FlowField, HomeSpring, Vortex, WindField
from .grass import GrassField
from .noise import Noise
from .particles import Emitter, Particle, ParticleSystem
from .sprite import Animation, Frame, Sprite

__version__ = "0.1.0"

__all__ = [
    "Canvas", "DEFAULT", "gradient", "hex_color", "rgb",
    "Engine", "Entity", "Scene", "overlaps",
    "Attractor", "FlowField", "HomeSpring", "Vortex", "WindField",
    "GrassField", "Noise", "Emitter", "Particle", "ParticleSystem",
    "Animation", "Frame", "Sprite",
]
