"""TubeAmp TUI widgets."""

from tubeamp.widgets.controls import ControlsWidget
from tubeamp.widgets.playlist import PlaylistWidget
from tubeamp.widgets.spectrum import SpectrumWidget
from tubeamp.widgets.track_info import TrackInfoWidget
from tubeamp.widgets.volume import VolumeWidget

__all__ = [
    "SpectrumWidget",
    "TrackInfoWidget",
    "ControlsWidget",
    "PlaylistWidget",
    "VolumeWidget",
]
