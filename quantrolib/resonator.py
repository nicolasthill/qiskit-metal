from typing import Tuple, List

import numpy as np

from quantrolib.base import Component, Geometry
from quantrolib.port import Port
from qiskit_metal import draw, Dict


class Resonator(Component):
    """A resonator component for wirebond connections to on-chip coplanar waveguides."""

    default_options = Dict(
        pad_width="680um",  # Width of the resonator pad
        pad_length="540um",  # Length of the resonator pad
        ground_gap="25um",  # Ground gap surrounding the resonator pad
        # adapter_length='560um',     # Length of the adapter from the pad to the CPW pin
        nanowire_width="2um",  # Width of the nano-wire
        nanowire_length="94um",  # Length of the nano-wire
        nanowire_gap_width="50um",  # ground gap from the nano-wire
        cpw_width='10um',           # Width of the CPW track at the pin
        cpw_gap='6um',              # Gap of the CPW track at the pin
    )

    component_metadata = Dict(
        short_name="resonator",
    )

    def generate_geometries(
        self,
        pad_width,
        pad_length,
        ground_gap,
        nanowire_width,
        nanowire_length,
        nanowire_gap_width,
        cpw_width,
        cpw_gap,
        **kwargs,
    ):
        """Generate the geometry for the wirebond resonator."""

        # Ground cutout
        ground_pad_width = pad_width + 2 * ground_gap
        ground_pad_length = pad_length + 2 * ground_gap
        ground_pad = Geometry(
            name="ground_pad",
            polygon=draw.rectangle(ground_pad_width, ground_pad_length, 0, 0),
            options=dict(subtract=True),
        )

        # Create nano-wire
        nanowire = Geometry(
            "nanowire",
            draw.LineString([
                (-nanowire_length / 2, pad_length / 2 - nanowire_width / 2),
                (nanowire_length / 2, pad_length / 2 - nanowire_width / 2)
            ]),
            type="junction",
            options=dict(width=nanowire_width),
        )

        # Create resonator pad
        pad = draw.rectangle(pad_width, pad_length, 0, 0)

        # Nanowire cutout
        nanowire_gap = draw.rectangle(
            nanowire_length,
            nanowire_gap_width,
            0,
            pad_length / 2 - nanowire_gap_width / 2,
        )
        pad = pad.difference(nanowire_gap)

        # Finger gaps
        gap_width = 20e-3

        reference_point = (0, +pad_length / 2 - nanowire_gap_width)

        previous_point = None
        for index, point in enumerate(
            self.generate_raw_points(
                n_pairs=9,
                gap_width=gap_width,
                x_tot=pad_width,
                y_tot=pad_length - nanowire_gap_width,
            )
        ):
            point = (point[0] + reference_point[0], -point[1] + reference_point[1])

            if previous_point is not None:
                rect_point = (
                    (point[0] + previous_point[0]) / 2,
                    (point[1] + previous_point[1]) / 2,
                )

                if index % 2 == 1:  # dy
                    gap = draw.rectangle(
                        gap_width, point[1] - previous_point[1] - gap_width, *rect_point
                    )
                elif index % 2 == 0:  # dx
                    gap = draw.rectangle(
                        point[0] - previous_point[0] + gap_width,
                        -gap_width,
                        *rect_point,
                    )
                else:
                    raise ValueError("This should not happen.")

                pad = pad.difference(gap)
            previous_point = point

        pad = Geometry("pad", pad)

        # Add port for CPW connection
        self.ports.add(
            port=Port(
                position=[0, pad_length / 2 + ground_gap],
                direction=np.pi/2,
                name="DC_probe",
                width=cpw_width,
                gap=cpw_gap,
            ),
        )

        return [pad, nanowire, ground_pad]

    def generate_raw_points(
        self,
        n_pairs,
        gap_width,
        x_tot: float,
        y_tot: float,
    ) -> List[Tuple[float, float]]:

        y_max = y_tot + gap_width / 2
        y_spacing = y_max / (n_pairs + 1)

        finger_width = y_spacing - gap_width
        x_max = x_tot - gap_width - finger_width * 2

        y_spacing = y_max / (n_pairs + 1)

        points = [(0, 0)]
        points.append((0, y_spacing))

        def f(y: float, index: int) -> float:
            return -((-1) ** index) / 2 * x_max * (y + y_spacing) / y_max

        for index in range(1, n_pairs + 1):
            y_pos = index * y_spacing
            x_pos = f(y=y_pos, index=index)
            points.extend(
                [
                    (x_pos, y_pos),
                    (x_pos, y_pos + y_spacing),
                ]
            )

        points.append((f(y=y_pos, index=index + 1), (y_pos + y_spacing)))

        return points


if __name__ == "__main__":
    import time

    from quantrolib.chip import JAWS
    from quantrolib.resonator import Resonator  # noqa: F811

    chip = JAWS()

    resonator = Resonator(design=chip, name="example_resonator")

    chip.draw()
    time.sleep(1)  # such that the script waits until closing the GUI
