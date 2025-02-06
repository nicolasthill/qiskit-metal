from qiskit_metal import QComponent
from qiskit_metal import draw, Dict


class Launcher(QComponent):
    """A launcher component for wirebond connections to on-chip coplanar waveguides."""

    default_options = Dict(
        pad_width='680um',          # Width of the launcher pad
        pad_length='540um',         # Length of the launcher pad

        ground_gap='240um',         # Ground gap surrounding the launcher pad
        adapter_length='560um',     # Length of the adapter from the pad to the CPW pin

        cpw_width='32um',           # Width of the CPW track at the pin
        cpw_gap='4um',              # Gap of the CPW track at the pin
    )

    component_metadata = Dict(
        short_name='launcher',
    )

    def make(self):
        """Generate the geometry for the wirebond launcher."""
        p = self.parse_options()

        # Create launcher pad
        pad_width = p.pad_width
        pad_length = p.pad_length
        pad = draw.rectangle(pad_width, pad_length, 0, 0)

        pad_gap_width = p.pad_width + 2 * p.ground_gap
        pad_gap_length = p.pad_length + p.ground_gap
        pad_gap = draw.rectangle(pad_gap_width, pad_gap_length, 0, - p.ground_gap / 2)

        # Create launcher pad to CPW adapter
        adapter = draw.Polygon([
            (pad_width/2, pad_length/2),
            (-pad_width/2, pad_length/2),
            (-p.cpw_width/2, pad_length/2 + p.adapter_length),
            (p.cpw_width/2, pad_length/2 + p.adapter_length)
        ])
        adapter_gap = draw.Polygon([
            (pad_gap_width/2, p.pad_length/2),
            (-pad_gap_width/2, p.pad_length/2),
            (-p.cpw_width/2 - p.cpw_gap, p.pad_length/2 + p.adapter_length),
            (p.cpw_width/2 + p.cpw_gap, p.pad_length/2 + p.adapter_length)
        ])

        self.add_qgeometry('poly', {"pad": pad, "adapter": adapter})
        self.add_qgeometry('poly', {"pad_gap": pad_gap, "adapter_gap": adapter_gap}, subtract=True)

        # Add pin for CPW connection
        pin_start = (0, p.pad_length/2 + p.adapter_length - p.cpw_width)
        pin_end = (0, p.pad_length/2 + p.adapter_length)
        pin_points = [pin_start, pin_end]
        self.add_pin(
            self.name,
            pin_points,
            input_as_norm=True,
            width=p.cpw_width,
            gap=p.cpw_gap,
        )


if __name__ == "__main__":
    import qiskit_metal as metal

    from quantrolib.component import Launcher

    design = metal.designs.DesignPlanar()
    gui = metal.MetalGUI(design)

    launcher = Launcher(design=design, name="example_launcher")
    gui.rebuild()
    gui.autoscale()
