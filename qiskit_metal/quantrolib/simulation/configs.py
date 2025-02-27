from dataclasses import dataclass
from typing import Any, Dict, List, Optional


from qiskit_metal.designs import DesignPlanar


@dataclass
class Config:
    name: str

    @property
    def _type(self) -> str:
        raise NotImplementedError(
            "Config subclasses must implement a '_type' property."
        )


@dataclass
class RenderConfig(Config):
    design: DesignPlanar
    project_path: Optional[str] = None
    project_name: Optional[str] = None
    design_name: Optional[str] = None
    mode: str = "eigenmode"
    open_pins: Optional[List[Any]] = None
    port_list: Optional[List[Any]] = None
    max_mesh_length_jj: Optional[str] = None
    max_mesh_length_port: Optional[str] = None

    _type: str = "render"


@dataclass
class SimulationConfig(Config):
    min_freq_ghz: float
    n_modes: int
    max_delta_f: float
    max_passes: int

    _type: str = "simulation"


@dataclass
class ReportConfig(Config):
    field_configs: List[Dict[str, Any]] = None

    _type: str = "report"
