"""Base classes to interface with Qiskit Metal.

Classes
-------
Design
    A base class for designing quantum circuits.

"""

from typing import Optional, List
from pathlib import Path


from qiskit_metal import draw

from qiskit_metal import MetalGUI, QComponent
from qiskit_metal.designs import DesignPlanar

from quantrolib.port import Ports

GDS_DIRECTORY = Path.cwd() / "gds_files"
GDS_DIRECTORY.mkdir(exist_ok=True)


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
        self._design.overwrite_enabled = True
        self._gui = gui if gui is not None else MetalGUI(self._design)

        self.gds_renderer = self._design.renderers.gds

    def generate_gds(self, file_name: str = "") -> None:
        """Generate a GDS file for the design.

        Parameters
        ----------
        file_name : str
            The name of the GDS file to generate.
        """
        file = file_name + ".gds"
        self.gds_renderer.export_to_gds(GDS_DIRECTORY / file)

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


class Geometry:

    def __init__(self, name: str, polygon: draw.Polygon, options: dict = None):
        if options is None:
            options = {}
        self.name = name
        self.polygon = polygon
        self.options = options

    def move(self, pos_x: float, pos_y: float, orientation: float) -> None:
        # rotate
        rotated_polyon = draw.rotate(self.polygon, angle=orientation, origin=[0, 0])
        # translate
        self.polygon = draw.translate(rotated_polyon, xoff=pos_x, yoff=pos_y)

    def add_to_(self, component: QComponent) -> None:
        component.add_qgeometry("poly", {self.name: self.polygon}, **self.options)


class Component(QComponent):

    def __init__(self, design: Design, *args, **kwargs):
        super().__init__(design=design._design, *args, make=False, **kwargs)

        self.ports: Ports = Ports()

    def make(self):
        p = self.parse_options()

        # GEOMETRY

        geometries = self.generate_geometries(**p)

        for geometry in geometries:

            # rotate and translate
            geometry.move(pos_x=p.pos_x, pos_y=p.pos_y, orientation=p.orientation)

            # add to qgeometry
            geometry.add_to_(component=self)

        # PORTS

        # rotate and translate
        self.ports.transform(position=[p.pos_x, p.pos_y], rotation=p.orientation)

        # add ports as pins
        self.ports.add_as_pins(self)

    def move(
        self, geometry: Geometry, pos_x: float, pos_y: float, orientation: float
    ) -> Geometry:
        return Geometry(
            name=geometry.name,
            polygon=draw.translate(
                draw.rotate(geometry.polygon, angle=orientation, origin=[0, 0]),
                xoff=pos_x,
                yoff=pos_y,
            ),
        )

    def generate_geometries(self, **kwargs) -> List[Geometry]:
        raise NotImplementedError(
            "generate_geometries must be implemented in subclass."
        )
