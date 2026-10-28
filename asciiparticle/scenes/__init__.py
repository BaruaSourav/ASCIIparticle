"""Bundled scenes, in the order the number keys select them."""
from .banner import BannerScene
from .campfire import CampfireScene
from .fireworks import FireworksScene
from .flow import FlowScene
from .meadow import MeadowScene

SCENES = [MeadowScene, FlowScene, FireworksScene, CampfireScene, BannerScene]

__all__ = ["SCENES", "MeadowScene", "FlowScene", "FireworksScene", "CampfireScene", "BannerScene"]
