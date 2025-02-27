from typing import Tuple, List

import numpy as np
from shapely.affinity import scale

from quantrolib.base import Component, Geometry
from quantrolib.port import Port
from qiskit_metal import draw, Dict


def generate_snaking_points(
    n_pairs: int,
    x_tot: float,
    y_tot: float,
    center_offset: float,
    wire_gap: float,
    teeth_gap: float,
) -> List[Tuple[float, float]]:
    """
    Generate raw snaking points for the finger (capacitor) gap.

    The algorithm uses the available extents (x_tot, y_tot) and parameters
    (wire_gap, teeth_gap, wire_length) to create a series of points that
    will later be smoothed (via filleting) into a continuous path.
    """
    y_max = y_tot / 2.0
    x_max = x_tot

    starting_y = wire_gap / 2 + 15e-3

    y_spacing = (y_max - starting_y) / (n_pairs)

    points = [(0, 0), (0, starting_y + teeth_gap/2)]

    def f(y: float, index: int) -> float:
        return - (center_offset + (-1) ** index) / 2.0 * x_max / y_max * (y + y_spacing)

    for index in range(0, n_pairs):
        y_pos = index * y_spacing + starting_y + teeth_gap/2
        x_pos = f(y_pos, index)
        points.append((x_pos, y_pos))
        points.append((x_pos, y_pos + y_spacing))

    return points


def generate_finger_gap(
    n_pairs,
    points,
    reference_point,
    x_reference,
    flip=False,
    teeth_gap=None,
    R=1.0,
):
    # 2) Transform positions relative to symmetry reference
    points = np.array(points) + [x_reference, 0]

    if flip:
        points[:, 1] *= -1

    if n_pairs % 2 != 0:  # ensures line is always on the right
        points[:, 0] *= -1

    points = points.tolist()

    previous_point = None
    joint_gap = None
    for index, point in enumerate(points):
        point = (point[0] + reference_point[0], -point[1] + reference_point[1])

        if previous_point is not None:
            rect_point = (
                (point[0] + previous_point[0]) / 2,
                (point[1] + previous_point[1]) / 2,
            )

            if index % 2 == 1:  # dy
                gap = draw.rectangle(
                    teeth_gap, point[1] - previous_point[1] - teeth_gap, *rect_point
                )
            elif index % 2 == 0:  # dx
                gap = draw.rectangle(
                    point[0] - previous_point[0] + teeth_gap,
                    -teeth_gap,
                    *rect_point,
                )
            else:
                raise ValueError("This should not happen.")

            if joint_gap is None:
                joint_gap = gap
            else:
                joint_gap = joint_gap.union(gap)
        previous_point = point

    # Remove from last tooth
    if R != 1.0:
        gap = draw.rectangle(
            (1.0 - R) * np.abs(2 * points[-1][0]),
            2 * (points[-2][1] - points[-1][1]),
            xoff=-1 * R * points[-1][0],
            yoff=points[-1][1],
        )
        joint_gap = joint_gap.union(gap)

    return joint_gap


class EdgeInductanceResonator(Component):
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


class VariableIncaResonator(Component):
    default_options = dict(
        n_pairs=7,                              # Number of finger pairs
        nanowire_width="2um",                   # Width of the nano-wire
        nanowire_length="94um",                 # Length of the nano-wire
        nanowire_gap_width="100um",              # ground gap from the nano-wire
        teeth_dimensions=("10um", "40um", "10um"),          # (teeth_width, teeth_length, teeth_gap)
        # port_width="10um",                       # Width of the resonator port
        # fillet="0um",                            # Fillet radius (if any)
        # overdev="0um",                           # Overdevelopment margin
        # teeth_length_ext="70um",                  # Extra extension for the capacitor fingers
        ground_gap_width="50um",                 # Gap width between the resonator and incoming line
        center_offset=0,
        s_ground_size="1.1mm",
        n_ground_size="1.06mm",
    )

    component_metadata = dict(short_name="inca_resonator")

    def generate_geometries(
        self,
        n_pairs,
        nanowire_width,
        nanowire_length,
        nanowire_gap_width,
        teeth_dimensions,
        # port_width,
        # fillet,
        # overdev,
        # teeth_length_ext,
        ground_gap_width,
        center_offset,
        s_ground_size,
        n_ground_size,
        **kwargs,
    ) -> List[Geometry]:
        """
        Generate all geometries for the Inca resonator.

        The resonator consists of:
          1. An absolute bounding box (the resonator pad)
          2. A ground gap connecting to the incoming line
          3. Two meandering finger gap geometries (top and bottom)
          4. A gap surrounding the inductive nanowire (wire gap)
          5. The nanowire itself

        Ports are created and added to self.ports.
        """

        # 0) Prepare variables

        # Unpack the tuples (all dimensions in microns)
        _, _, teeth_gap = teeth_dimensions

        center_offset = (-1)**n_pairs * center_offset

        x_max = n_ground_size - ground_gap_width - nanowire_length

        x_reference = center_offset * x_max / 2

        central_position = [x_reference, 0.0]

        # 1) Ground cutout
        ground_pad = Geometry(
            name="ground_pad",
            polygon=draw.rectangle(s_ground_size, s_ground_size, 0, 0),
            options=dict(subtract=True),
        )

        # 2) Create nano-wire
        nanowire = Geometry(
            "nanowire",
            draw.LineString([
                (
                    -nanowire_length / 2 + central_position[0],
                    central_position[1],
                ),
                (
                    nanowire_length / 2 + central_position[0],
                    central_position[1],
                )
            ]),
            type="junction",
            options=dict(width=nanowire_width),
        )

        # 3) Resonator pad
        pad = draw.rectangle(n_ground_size, n_ground_size, 0, 0)

        nanowire_gap = draw.rectangle(
            nanowire_length, nanowire_gap_width, x_reference, 0,
        )

        pad = pad.difference(nanowire_gap)

        # 1) Create a long list of snaking `raw_points`
        raw_points = generate_snaking_points(
            n_pairs=n_pairs,
            x_tot=n_ground_size,
            y_tot=n_ground_size,
            center_offset=center_offset,
            wire_gap=nanowire_gap_width,
            teeth_gap=teeth_gap,
        )

        bottom_gap = generate_finger_gap(
            n_pairs,
            raw_points,
            (0, 0),
            x_reference,
            flip=False,
            teeth_gap=teeth_gap,
            R=1.0,  # TODO: otherwise the last tooth is removed falsely for odd n_pairs
        )
        top_gap = scale(bottom_gap, xfact=1.0, yfact=-1.0, origin=(0, 0))

        pad = pad.difference(bottom_gap)
        pad = pad.difference(top_gap)

        pad = Geometry("pad", pad)

        return [pad, nanowire, ground_pad]


class IncaResonator(Component):
    """An interdigitated resonator component with triangular finger pattern."""

    default_options = Dict(
        n_pairs=18,                              # Number of finger pairs
        wire_dimensions=("2um", "94um", "100um"),  # (width, length, gap)
        teeth_dimensions=("10um", "40um", "10um"),  # (width, length, gap)
        pad_height="850um",                  # Height of the resonator pad
        pad_width="1440um",                  # Width of the resonator pad
        fillet="10um",                       # Fillet radius for corners
        ratio=1.0,                           # Ratio for end finger lengths (0-1)
        teeth_length_ext="70um",             # Extra extension for fingers
        ground_gap_width="50um",             # Gap width between resonator and ground
        R=0.75,                              # Remove percetage of last tooth
    )

    component_metadata = Dict(
        short_name="inca_resonator",
    )

    def generate_geometries(
        self,
        n_pairs,
        wire_dimensions,
        teeth_dimensions,
        pad_height,
        pad_width,
        ratio,
        teeth_length_ext,
        ground_gap_width,
        R,
        **kwargs,
    ):
        """Generate the geometry for the Inca resonator."""

        # Unpack dimensions
        wire_width, wire_length, wire_gap = wire_dimensions
        teeth_width, teeth_length, teeth_gap = teeth_dimensions

        # 1) Ground cutout
        ground_pad = Geometry(
            name="ground_pad",
            polygon=draw.rectangle(
                pad_width + ground_gap_width, pad_height + ground_gap_width,
                0, 0,
            ),
            options=dict(subtract=True),
        )

        # Create base pad outline
        pad = draw.rectangle(pad_width, pad_height, 0, 0)

        # Create finger gaps
        raw_points = generate_snaking_points(
            n_pairs=n_pairs,
            x_tot=pad_height,
            y_tot=pad_height,
            center_offset=0.0,
            wire_gap=wire_gap,
            teeth_gap=teeth_gap,
        )

        bottom_gap = generate_finger_gap(
            n_pairs,
            raw_points,
            (0, 0),
            0,
            flip=False,
            teeth_gap=teeth_gap,
            R=R,
        )
        top_gap = scale(bottom_gap, xfact=-1.0, yfact=-1.0, origin=(0, 0))

        pad = pad.difference(bottom_gap)
        pad = pad.difference(top_gap)

        # Create wire gap
        wire_gap_geom = draw.rectangle(wire_length, wire_gap, 0, 0)
        pad = pad.difference(wire_gap_geom)

        # Create nanowire
        nanowire = Geometry(
            "nanowire",
            draw.LineString([
                (-wire_length/2, 0),
                (wire_length/2, 0)
            ]),
            type="junction",
            options=dict(width=wire_width),
        )

        # Create pad fingers
        finger_width = 20e-3
        finger_spacing = 20e-3

        top_right_fingers = None
        for i in range(int(n_pairs / 2) + 1):
            y_pos = i * (finger_width + finger_spacing)
            x_pos = i*pad_width/2/n_pairs
            finger = draw.rectangle(
                pad_width,
                finger_width,
                + (pad_width + wire_length + 3*finger_spacing)/2 + x_pos,
                y_pos + finger_spacing,
            )
            if top_right_fingers is None:
                top_right_fingers = finger
            else:
                top_right_fingers = top_right_fingers.union(finger)

        if top_right_fingers is None:
            raise ValueError("No fingers found")

        top_left_fingers = scale(
            top_right_fingers, xfact=-1.0, yfact=1.0, origin=(0, 0)
        )
        bot_right_fingers = scale(
            top_right_fingers, xfact=1.0, yfact=-1.0, origin=(0, 0)
        )
        bot_left_fingers = scale(
            top_right_fingers, xfact=-1.0, yfact=-1.0, origin=(0, 0)
        )
        pad = pad.difference(top_right_fingers)
        pad = pad.difference(top_left_fingers)
        pad = pad.difference(bot_right_fingers)
        pad = pad.difference(bot_left_fingers)

        pad = Geometry("pad", pad)

        return [pad, nanowire, ground_pad]


class BraggResonator(Component):
    default_options = dict(
        n_pairs=7,                              # Number of finger pairs
        nanowire_width="2um",                   # Width of the nano-wire
        nanowire_length="24um",                 # Length of the nano-wire
        nanowire_gap_width="50um",              # ground gap from the nano-wire
        teeth_dimensions=("10um", "40um", "10um"),  # (width, length, gap)
        ground_gap_width="50um",  # Gap width between the resonator and incoming line
        center_offset=0,
        pad_height="1.2mm",
        pad_width="0.94mm",
        incoming_line_width="4um",
    )

    component_metadata = dict(short_name="inca_resonator")

    def generate_geometries(
        self,
        n_pairs,
        nanowire_width,
        nanowire_length,
        nanowire_gap_width,
        teeth_dimensions,
        # port_width,
        # fillet,
        # overdev,
        # teeth_length_ext,
        ground_gap_width,
        center_offset,
        pad_height,
        pad_width,
        incoming_line_width,
        **kwargs,
    ) -> List[Geometry]:
        """
        Generate all geometries for the Inca resonator.

        The resonator consists of:
          1. An absolute bounding box (the resonator pad)
          2. A ground gap connecting to the incoming line
          3. Two meandering finger gap geometries (top and bottom)
          4. A gap surrounding the inductive nanowire (wire gap)
          5. The nanowire itself

        Ports are created and added to self.ports.
        """

        # 0) Prepare variables

        # Unpack the tuples (all dimensions in microns)
        _, _, teeth_gap = teeth_dimensions

        center_offset = (-1)**n_pairs * center_offset

        x_reference = center_offset * pad_width / 2

        central_position = [x_reference, 0.0]

        # 1) Ground cutout
        ground_cutout = draw.rectangle(
            pad_width + 2 * teeth_gap,
            pad_height + 2 * teeth_gap,
            0, 0,
        )
        incoming_line_ground_cutout = draw.rectangle(
            ground_gap_width,
            pad_height + 2 * teeth_gap,
            - pad_width/2 - ground_gap_width/2, 0
        )
        ground_cutout = ground_cutout.union(incoming_line_ground_cutout)

        ground_pad = Geometry(
            name="ground_pad",
            polygon=ground_cutout,
            options=dict(subtract=True),
        )

        # 2) Create nano-wire
        nanowire = Geometry(
            "nanowire",
            draw.LineString([
                (
                    -nanowire_length / 2 + central_position[0],
                    central_position[1],
                ),
                (
                    nanowire_length / 2 + central_position[0],
                    central_position[1],
                )
            ]),
            type="junction",
            options=dict(width=nanowire_width),
        )

        # 3) Resonator pad
        pad = draw.rectangle(pad_width, pad_height, 0, 0)

        nanowire_gap = draw.rectangle(
            nanowire_length, nanowire_gap_width, x_reference, 0,
        )

        incoming_line = draw.rectangle(
            ground_gap_width,
            incoming_line_width,
            - pad_width/2 - ground_gap_width/2, 0
        )

        pad = pad.difference(nanowire_gap)
        pad = pad.union(incoming_line)

        # 1) Create a long list of snaking `raw_points`
        raw_points = generate_snaking_points(
            n_pairs=n_pairs,
            x_tot=pad_width,
            y_tot=pad_height,
            center_offset=center_offset,
            wire_gap=nanowire_gap_width,
            teeth_gap=teeth_gap,
        )

        bottom_gap = generate_finger_gap(
            n_pairs,
            raw_points,
            (0, 0),
            x_reference,
            flip=False,
            teeth_gap=teeth_gap,
            R=1.0,  # TODO: otherwise the last tooth is removed falsely for odd n_pairs
        )
        top_gap = scale(bottom_gap, xfact=1.0, yfact=-1.0, origin=(0, 0))

        pad = pad.difference(bottom_gap)
        pad = pad.difference(top_gap)

        # Ground the pad
        metal_to_ground = draw.rectangle(
            teeth_gap,
            pad_height - (raw_points[-1][1] - raw_points[-2][1]) - 31.15e-3,
            +pad_width/2 + teeth_gap/2, 0
        )
        pad = pad.union(metal_to_ground)

        pad = Geometry("pad", pad)

        self.ports.add(
            port=Port(
                position=[-pad_width / 2 - ground_gap_width - teeth_gap, 0],
                direction=np.pi,
                name="drive",
                width=incoming_line_width,
            ),
        )

        return [pad, nanowire, ground_pad]


if __name__ == "__main__":
    import time

    from quantrolib.chip import JAWS
    from quantrolib.resonator import IncaResonator  # noqa: F811

    chip = JAWS()

    resonator = IncaResonator(design=chip, name="example_resonator")

    chip.draw()
    time.sleep(1)  # such that the script waits until closing the GUI
