from typing import List, Optional

from copy import deepcopy
import numpy as np

from qiskit_metal.qlibrary.core import QComponent

# from .design import Component, Device
# from .helper import Placement


def rotation_matrix(theta: float) -> np.ndarray:
    """Compute the standard rotation matrix.
    Computes the matrix which will rotate the coordinate system from
    the current values counter-clockwise.
    Parameters
    ----------
    theta : float
        Angle to rotate (in radians).
    Returns
    -------
    rot_mat : array-like[2][2] of float
        Two by two matrix containing the rotation matrix.
    """
    return np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])


class Port:
    """Representation of a port for connections.
    Ports contain a position and direction which helps to realize a
    connection between different objects.
    Attributes
    ----------
    position: array-like[2] of float
        Location of the port within the local coordinate system.
    direction: float
        Outward normal of the port (pointing away from the owner
        of the port) in radians.
    name: str
        Name of the port.
    """

    def __init__(
        self,
        position: List[float],
        direction: float,
        name: str = "",
        width: float = "32um",
        gap: float = "4um",
    ) -> None:
        """Create a port.
        Parameters
        ----------
        position: array-like[2] of float or int
            Location of the port within the local coordinate system.
        direction: float
            Outward normal of the port (pointing away from the owner
            of the port) in radians.
        name: str, optional
            Name of the port.
            Defaults to ""
        length_offset: float, optional
            Extra length that is added to the connections made to this port
            when calculating line lengths. Defaults to 0.
        """
        # Convert position from [x, y] or (x, y) to numpy array
        # Has no effect if position is already a numpy array
        self.position = np.asarray(position)
        self.direction = np.mod(direction, 2 * np.pi)
        self.name = name

        self.width = width
        self.gap = gap

    def __repr__(self) -> str:
        """Return a representation of this port."""
        return (
            f"Port(({self.position[0]}, {self.position[1]}), "
            f"{self.direction}, {self.name})"
        )

    def __str__(self) -> str:
        """Return a human-readable string representation of this port."""
        return (
            f"Port {self.name} at ({self.position[0]}, "
            f"{self.position[1]}), direction {self.direction}"
        )

    def get_opposite_direction(self) -> float:
        """Return the opposite direction of this port."""
        return np.mod(self.direction + np.pi, 2 * np.pi)

    def transform(
        self,
        translation: Optional[np.typing.ArrayLike] = None,
        rotation: float = 0.0,
        scale_factor: float = 1.0,
        reflect_x: bool = False,
    ) -> None:
        """Transform the port to match the behavior of `.place`.
        Uses the same order of operations as
        `qdl.helper.transform_poly`, i.e. rotation, scaling,
        reflection, and then translation.
        Parameters
        ----------
        translation : array-like [2], optional
            (x, y) translation to apply to the current coordinates of
            the port. Can be a list of two coordinates, a tuple of two
            coordinates, or a numpy array of shape (2).
            Defaults to (0, 0).
        rotation : float, optional
            Angle (in degrees) to rotate this port counterclockwise
            when placing it on the sample. Defaults to 0.
        scale_factor : float, optional
            Number by which to multiply the local port coordinates
            prior to performing other operations. Necessary when
            scaling a Feature during placement so that the port
            locations can match. A scale factor of 1 preserves all
            sizes as they are, while a scale factor > 1 magnifies
            the feature and a scale factor < 1 shrinks the feature.
            Defaults to 1.
        reflect_x : bool, optional
            Reflect the port coordinates across the x-axis while
            computing the updated coordinates.
            Defaults to False.
        """
        if translation is None:
            translation = np.array([0, 0])
        else:
            translation = np.asarray(translation)

        # Reflect x
        if reflect_x:
            self.position = np.multiply(self.position, np.array([1, -1]))
            self.direction = np.mod(2 * np.pi - self.direction, 2 * np.pi)

        # Rotate
        theta = np.deg2rad(rotation)  # radians
        rot_mat = rotation_matrix(theta)
        self.position = np.matmul(rot_mat, self.position)
        self.direction = np.mod(self.direction + theta, 2 * np.pi)

        # Scale
        self.position = scale_factor * self.position

        # Translate
        self.position = self.position + translation

    def copy(self) -> "Port":
        """Return a copy of the port."""
        return deepcopy(self)

    def pin_kwargs(self) -> dict:
        """Return a dictionary of pin kwargs."""
        port_point = self.position
        point_behind_port_point = port_point + 1e-6 * np.array([
            np.cos(self.direction), np.sin(self.direction)
        ])
        return dict(
            name=self.name,
            points=[port_point, point_behind_port_point],
            width=self.width,
            gap=self.gap,
            input_as_norm=True,
        )


class Ports:
    def __init__(
        self,  # TODO implement libqudev base class
        ports: list[Port] = None,
        aliases: dict[str, int] = None,
    ):
        aliases = {} if aliases is None else aliases
        if ports is None:
            ports = [Port([0, 0], 0, "blank")] * len(aliases.keys())
        self.ports = ports
        # ensure alias keys are strings and values integers
        self.aliases = {str(key): int(value) for key, value in aliases.items()}

    def __getitem__(self, key) -> Port:
        """Return the port as referenced by alias or idx"""
        if isinstance(key, int):  # key is port_idx
            return self.ports[key]
        elif isinstance(key, str):  # key is port_alias
            return self.ports[self.aliases[key]]
        else:
            raise KeyError(f"Key {key} does not lead to a port.")

    def add(self, port: Port, alias: str = None) -> None:
        """Add a port to the list of ports."""
        self.ports.append(port)
        if alias is not None:
            self.aliases[alias] = len(self.ports) - 1

    def add_as_pins(self, component: QComponent) -> None:
        """Add the ports to the component as pins."""
        for port in self.ports:
            component.add_pin(
                **port.pin_kwargs(),
            )

    def __str__(self):
        """Return a string describing all ports."""
        # store list of aliases indexed by port_idx
        aliases = [None] * len(self.ports)
        for alias, port_idx in self.aliases.items():
            if aliases[port_idx] is None:
                aliases[port_idx] = [alias]
            else:
                aliases[port_idx].append(alias)
        # generate output string
        string = "Ports for this component:\n"
        for port_idx, port in enumerate(self.ports):
            string += f"  Port {port_idx}"
            if aliases[port_idx]:
                string += " with alias(es) "
                for alias in aliases[port_idx][:-1]:
                    string += f"'{alias}'" + " and "
                string += f"'{aliases[port_idx][-1]}'"
            string += " is given by:\n"
            string += "    " + str(port) + "\n\n"
        string += "\n"
        return string

    def transform(
        self,
        position: np.ndarray = None,
        rotation: float = 0.0,
        scale_factor: float = 1.0,
        reflect_x: bool = False,
    ) -> None:
        """Transform each of the ports"""
        for port in self.ports:
            port.transform(
                translation=position,
                rotation=rotation,
                scale_factor=scale_factor,
                reflect_x=reflect_x,
            )

    def available_ports(self) -> list:
        """Returns a list of ports available for connections."""
        return [(i,) for i in range(len(self.ports))]

    def copy(self) -> "Ports":
        """Return a copy of Ports"""
        return deepcopy(self)
