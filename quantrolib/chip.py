"""This module contains chips for different sample holders.

Includes a generic Chip class upon which the specific chips build.

Chip types
----------
- JAWS: comes in two varieties:
- SMASH: comes in two varieties:
    - SMASH2
    - SMASH12
"""

from pathlib import Path
from typing import Optional, Tuple

from quantrolib.base import Design
from quantrolib.component import Launcher
from quantrolib.utilities import load_yaml

from logger import logger as log

from qiskit_metal.qlibrary.core import QComponent




class Chip(Design):
    """Generic chip class.

    To access attributes the chip must first be drawn.

    Attributes
    ----------
    config : dict
        The configuration of the chip.
    rf_ports: list[QComponent]
        The RF ports of the chip.
    dc_ports: list[QComponent]
        The DC ports of the chip.

    Methods
    -------
    draw
        Draw the chip and it in the GUI.
    close
        Close the GUI.
    show
        Show the design in the GUI.
    """

    _config_path = Path(__file__).parent / "packaging_configs"

    def __init__(self, **kwargs) -> None:
        """Initializes the Chip class."""
        super().__init__(**kwargs)

        self._config = self._load_config()

        ########################
        # Implement the design #
        ########################

        # chip characteristics
        self._design.chips.main = {
            "material": "silicon",
            "layer_start": "0",
            "layer_end": "2048",
            "size": {
                "center_x": "0.0mm",
                "center_y": "0.0mm",
                "center_z": "0.0mm",
                "size_x": self._config["width"],
                "size_y": self._config["length"],
                "size_z": "-750um",
                "sample_holder_top": "890um",
                "sample_holder_bottom": "1650um",
            },
        }

        # add RF ports
        if "RF" in self._config["ports"]:
            self._rf_ports = []
            self._add_rf_ports()

        # add DC ports
        if "DC" in self._config["ports"]:
            self._dc_ports = []
            self._add_dc_ports()

    @property
    def config(self) -> dict:
        """The configuration of the chip."""
        log.warning(
            "Modifications to the chip config do not have an effect on the design."
            " For this some `__post_init__`-like method should be implemented that"
            " generates the design from the config and can be called gain after"
            " the config is modified."
        )
        return self._config

    @property
    def _config_filename(self) -> str:
        """The name of the configuration file for the chip."""
        raise NotImplementedError("Child classes of `Chip` must have this attribute.")

    def _load_config(self) -> dict:
        """Loads the configuration of the chip from the configuration file."""
        return load_yaml(self._config_path / self._config_filename)

    @property
    def rf_ports(self) -> list[QComponent]:
        """The RF ports of the chip."""
        try:
            return self._rf_ports
        except AttributeError:
            raise AttributeError("This chip does not have rf ports.")

    def _add_rf_port(
        self,
        position: Tuple[str | float] = [0.0, 0.0],
        orientation: float = 0.0,
        lead_length: Optional[str] = "0um",
        cpw_gap: Optional[str] = "9um",
        cpw_width: Optional[str] = "15um",
    ) -> None:
        """Adds an RF port on the chip at the specified position and orientation.

        Also appends the port to the list of RF ports.

        Parameters
        ----------
        position : Tuple[str | int], optional
            The position of the RF port on the chip.
            Defaults to [0, 0].
        orientation : float, optional
            The orientation of the RF port on the chip.
            Defaults to 0.
        lead_length : float, optional
            The length of the bond.
            Defaults to 0um.
        cpw_gap : float, optional
            The gap between cpw tracks.
            Defaults to 9um.
        cpw_width : float, optional
            The width of the cpw track.
            Defaults to 15um.
        """
        self._rf_ports.append(
            Launcher(
                design=self,
                name=f"rf_port_{len(self._rf_ports)}",
                options=dict(
                    pos_x=position[0],
                    pos_y=position[1],
                    orientation=orientation,
                    lead_length=lead_length,
                    cpw_gap=cpw_gap,
                    cpw_width=cpw_width,
                ),
            )
        )

    def _add_rf_ports(self) -> list[QComponent]:
        """Add the RF ports on the chip."""

        rf_config = self._config["ports"]["RF"]

        for position, orientation in rf_config["locations"]:
            self._add_rf_port(
                position=position,
                orientation=orientation,
                cpw_width=rf_config["cpw_width"],
                cpw_gap=rf_config["cpw_gap"],
            )

        return self.rf_ports

    @property
    def dc_ports(self) -> list[QComponent]:
        """The RF ports of the chip."""
        try:
            return self._dc_ports
        except AttributeError:
            raise AttributeError("This chip does not have dc ports.")

    def _add_dc_ports(self) -> list[QComponent]:
        raise NotImplementedError("DC ports are not yet implemented.")


class JAWS(Chip):
    """The JAWS chip.

    #TODO add DC ports

    Attributes
    ----------
    config : dict
        The configuration of the chip.
    rf_ports: list[QComponent]
        The RF ports of the chip.

    Methods
    -------
    draw
        Draw the chip and it in the GUI.
    close
        Close the GUI.
    show
        Show the design in the GUI.
    """

    _config_filename = "JAWS.yaml"


class SMASH2(Chip):
    """The SMASH2 chip.

    Attributes
    ----------
    config : dict
        The configuration of the chip.
    rf_ports: list[QComponent]
        The RF ports of the chip.

    Methods
    -------
    draw
        Draw the chip and it in the GUI.
    close
        Close the GUI.
    show
        Show the design in the GUI.
    """

    _config_filename = "SMASH2.yaml"


class SMASH12(Chip):
    """The SMASH12 chip.

    Attributes
    ----------
    config : dict
        The configuration of the chip.
    rf_ports: list[QComponent]
        The RF ports of the chip.

    Methods
    -------
    draw
        Draw the chip and it in the GUI.
    close
        Close the GUI.
    show
        Show the design in the GUI.
    """

    _config_filename = "SMASH12.yaml"


if __name__ == "__main__":
    from quantrolib.chip import JAWS, SMASH2, SMASH12

    jaws_chip = JAWS()
    jaws_chip.draw()

    jaws_chip = SMASH2()
    jaws_chip.draw()

    jaws_chip = SMASH12()
    jaws_chip.draw()
