from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path


from qiskit_metal.designs import DesignPlanar

@dataclass
class EMSetup:
    name: str = "Setup"
    min_freq_ghz: float = 1
    n_modes: int = 1
    max_delta_f: float = 0.1
    max_passes: int = 10
    min_passes: int = 1
    min_converged: int = 1
    pct_refinement: int = 30
    basis_order: int = -1


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
    project_dir: Optional[str] = None
    project_name: Optional[str] = None
    design_name: Optional[str] = None
    mode: str = "Eigenmode"
    setups: Optional[List[EMSetup]] = None
    open_pins: Optional[List[Any]] = None
    port_list: Optional[List[Any]] = None
    max_mesh_length_jj: Optional[str] = None
    max_mesh_length_port: Optional[str] = None

    _type: str = "render"

    @property
    def project_path(self) -> str:
        return Path(self.project_dir) / (self.project_name + ".aedt")

@dataclass
class ReportConfig(Config):
    field_configs: List[Dict[str, Any]] = None

    _type: str = "report"
