from qiskit_metal import draw, Dict
import numpy as np

from quantrolib.base import Component, Geometry
from quantrolib.port import Port


class Launcher(Component):
    """A launcher component for wirebond connections to on-chip coplanar waveguides."""

    default_options = Dict(
        pad_width="680um",  # Width of the launcher pad
        pad_length="540um",  # Length of the launcher pad
        ground_gap="240um",  # Ground gap surrounding the launcher pad
        adapter_length="560um",  # Length of the adapter from the pad to the CPW pin
        cpw_width="10um",  # Width of the CPW track at the pin
        cpw_gap="6um",  # Gap of the CPW track at the pin
    )

    component_metadata = Dict(
        short_name="launcher",
    )

    def __init__(self, design, *args, **kwargs):
        super().__init__(design, *args, **kwargs)

    def generate_geometries(
        self,
        pad_width,
        pad_length,
        ground_gap,
        adapter_length,
        cpw_width,
        cpw_gap,
        **kwargs,
    ):
        """Generate the geometry for the wirebond launcher."""

        # Create launcher pad
        pad = Geometry(
            name="pad",
            polygon=draw.rectangle(pad_length, pad_width, 0, 0),
        )

        pad_gap_width = pad_width + 2 * ground_gap
        pad_gap_length = pad_length + ground_gap
        pad_gap = Geometry(
            name="pad_gap",
            polygon=draw.rectangle(pad_gap_length, pad_gap_width, -ground_gap / 2, 0),
        )

        # Create launcher pad to CPW adapter
        adapter = Geometry(
            name="adapter",
            polygon=draw.Polygon(
                [
                    (pad_length / 2, pad_width / 2),
                    (pad_length / 2, -pad_width / 2),
                    (pad_length / 2 + adapter_length, -cpw_width / 2),
                    (pad_length / 2 + adapter_length, cpw_width / 2),
                ]
            ),
        )
        adapter_gap = Geometry(
            name="adapter_gap",
            polygon=draw.Polygon(
                [
                    (pad_length / 2, pad_gap_width / 2),
                    (
                        pad_length / 2,
                        -pad_gap_width / 2,
                    ),
                    (pad_length / 2 + adapter_length, -cpw_width / 2 - cpw_gap),
                    (pad_length / 2 + adapter_length, cpw_width / 2 + cpw_gap),
                ]
            ),
        )

        for negative in [pad_gap, adapter_gap]:
            negative.options = {"subtract": True}

        # Add port for CPW connection
        self.ports.add(
            port=Port(
                position=[pad_length / 2 + adapter_length, 0],
                direction=0,
                name='out',
                width=cpw_width,
                gap=cpw_gap,
            ),
        )

        # Add port to GND
        self.ports.add(
            port=Port(
                position=[-pad_length / 2, 0],
                direction=np.pi,
                name='in',
                width=pad_width,
                gap=ground_gap,
            ),
        )

        return [pad, pad_gap, adapter, adapter_gap]


if __name__ == "__main__":
    import time

    from quantrolib.chip import JAWS
    from quantrolib.component import Launcher  # noqa: F811

    chip = JAWS()

    launcher = Launcher(design=chip, name="example_launcher")

    chip.draw()
    time.sleep(1)  # such that the script waits until closing the GUI
