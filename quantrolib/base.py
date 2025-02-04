"""Base classes to interface with Qiskit Metal.

Classes
-------
Design
    A base class for designing quantum circuits.

"""

from typing import Optional

from qiskit_metal import MetalGUI
from qiskit_metal.designs import DesignPlanar


class Design:
    """A base class for designing quantum circuits.

    Handles the qiskit-metal GUI and design.

    Methods
    -------
    draw
        Draw and show the design it in the GUI.
    close
        Close the GUI.
    show
        Show the design in the GUI.
    """
    def __init__(
        self,
        design: Optional[DesignPlanar] = None,
        gui: Optional[MetalGUI] = None,
    ):
        """Initializes the Design class.

        Parameters
        ----------
        design : qiskit_metal.designs.DesignPlanar, optional
            The design to draw.
            Defaults to creating a new DesignPlanar object.
        gui : qiskit_metal.MetalGUI, optional
            The GUI to use.
            Defaults to creating a new GUI for the design.
        """
        self._design = design if design is not None else DesignPlanar()
        self._gui = gui if gui is not None else MetalGUI(self._design)

    def __del__(self):

        self._gui.main_window.force_close = True
        self._gui.main_window.close()

    def draw(self):
        self._gui.rebuild()
        self.show()

    def close(self):
        self._gui.main_window.force_close = True
        self._gui.main_window.close()

    def show(self):
        self._gui.autoscale()
        self._gui.show()
