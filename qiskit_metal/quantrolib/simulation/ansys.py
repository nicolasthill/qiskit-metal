from typing import Any, Dict, List
from pathlib import Path

import pyEPR as epr
from pyEPR.ansys import HfssApp

from qiskit_metal.renderers.renderer_ansys.hfss_renderer import QHFSSRenderer
from qiskit_metal.quantrolib.simulation import Config, RenderConfig, ReportConfig, EMSetup

# Configure logging
import logging
from qiskit_metal.quantrolib.logger import logger as log

log.setLevel(logging.DEBUG)

class ANSYS:
    def __init__(
        self,
        configs: list[Config],
        run_upon_init: bool = False
    ):
        # Tools
        self.renderer: QHFSSRenderer = None

        # Configurations
        self.render_configs: Dict[str, RenderConfig] = {}
        self.simulation_configs: Dict[str, SimulationConfig] = {}
        self.report_configs: Dict[str, ReportConfig] = {}

        self._configs: Dict[str, Dict[str, str | Config]] = {
            "render": {"configs": {}, "current": None},
            "simulation": {"configs": {}, "current": None},
            "report": {"configs": {}, "current": None},
        }

        self.add_configs(configs, select_afterwards=True)

        if run_upon_init:
            self.run()

    # -------------------------------------------------------------------------
    # Generic methods to add/select/get configurations.
    # -------------------------------------------------------------------------
    def add_config(self, config: Config, select_afterwards: bool = True) -> None:

        if self._configs[config._type]["configs"].get(config.name, False):
            log.warning(
                f"{config._type.capitalize()} config '{config.name}' already exists. "
                "Updating."
            )
            result_word = "updated"
        else:
            result_word = "added"

        self._configs[config._type]["configs"][config.name] = config
        log.debug(f"{config._type.capitalize()} config '{config.name}' {result_word}.")

        if select_afterwards:
            self.select_config(config)

    def add_configs(
        self, configs: List[Config], select_afterwards: bool = True
    ) -> None:
        for config in configs:
            self.add_config(config, select_afterwards=select_afterwards)

    def select_config(self, config: Config) -> None:

        if config.name not in self._configs[config._type]["configs"]:
            raise ValueError(
                f"{config._type.capitalize()} config '{config.name}' does not exist."
            )

        self._configs[config._type]["current"] = config.name
        log.debug(f"{config._type.capitalize()} config '{config.name}' selected.")

    def _get_current_config(self, config_type: str) -> Any:
        current = self._configs[config_type]["current"]
        if current is None:
            raise ValueError(f"No {config_type} configuration selected.")
        return self._configs[config_type]["configs"][current]

    # -------------------------------------------------------------------------
    # Methods to run actions based on the current configurations
    # -------------------------------------------------------------------------
    def run_render(self) -> None:
        config: RenderConfig = self._get_current_config("render")

        self.renderer = self.initiate_renderer(config)

        # Configure meshing
        if config.max_mesh_length_jj is not None:
            self.renderer.options["max_mesh_length_jj"] = config.max_mesh_length_jj
        if config.max_mesh_length_port is not None:
            self.renderer.options["max_mesh_length_port"] = config.max_mesh_length_port

        # Clean the design and render it.
        self.renderer.clean_active_design()
        try:
            self.renderer.render_design(
                open_pins=config.open_pins, port_list=config.port_list,
            )
        except Exception as e:
            log.error(f"Qiskit-Metal encountered an error while rendering the design: {e}")
            raise e
        log.info("##### RENDER SUCCESSFULL #####")

    def run_simulation(self) -> None:
        config: SimulationConfig = self._get_current_config("simulation")

        if self.renderer is None:
            raise ValueError("No renderer found. Please run the render step first.")

        # Initialize simulation parameters.
        self.renderer.initialize_eigenmode(
            name=config.name,
            min_freq_ghz=config.min_freq_ghz,
            n_modes=config.n_modes,
            max_delta_f=config.max_delta_f,
            max_passes=config.max_passes,
        )
        self.renderer.activate_ansys_setup(config.name)
        self.renderer.analyze_setup(config.name)
        log.info("##### SIMULATION SUCCESSFULL #####")

    def run_report(self) -> None:
        config: ReportConfig = self._get_current_config("report")

        for field_config in config.field_configs:
            self.renderer.plot_fields(**field_config)
        log.info("##### REPORT SUCCESSFULL #####")

    def run(self) -> None:
        self.run_render()
        self.run_simulation()
        self.run_report()

    def initiate_renderer(self, config: RenderConfig) -> QHFSSRenderer:
        # Rebuild the design and get the renderer.
        design = config.design
        design.rebuild()

        renderer: QHFSSRenderer = config.design.renderers.hfss

        # Connect to Ansys
        renderer.rapp = HfssApp()
        renderer.rdesktop = renderer.rapp.get_app_desktop()

        # Set the project directory
        if config.project_dir is None:
            config.project_dir = renderer.rdesktop.project_directory
        else:
            if not Path(config.project_dir).exists():
                raise ValueError(f"Project directory '{config.project_dir}' does not exist.")
            renderer.rdesktop.project_directory = config.project_dir            
        
        # Open the project
        if config.project_name is None:
            log.info("No project name provided. Creating new project.")
            project = renderer.rdesktop.new_project()
            config.project_name = project.name
            project.save(path=config.project_path)
        else:
            if config.project_name in renderer.rdesktop.get_project_names():
                renderer.rdesktop.set_active_project(config.project_name)
                project = renderer.rdesktop.get_active_project()
            else:
                if Path(config.project_path).exists():
                    project = renderer.rdesktop.open_project(config.project_path)
                else:
                    raise ValueError(f"Project's path {config.project_path}' does not exist.")

        # Open the design
        if config.design_name in project.get_design_names():
            design = project.get_design(config.design_name)
        else:
            if config.design_name not in project.get_design_names():
                message = f"Design '{config.design_name}' does not exist."
            else:
                message = "No design name provided."
            log.info(f"{message} Creating new design.")
            design = project.new_design(
                design_name=config.design_name,
                solution_type=config.mode,
            )
        
        # Open the setup
        if not config.setups:
            config.setups = [EMSetup()]

        for setup in config.setups:
            setup_names = design.get_setup_names()

            if setup.name not in setup_names:
                design.create_em_setup(**setup.__dict__)

        # Inform the renderer about the project and design.
        try:
            renderer._pinfo = epr.ProjectInfo(
                do_connect=True,
                project_path=config.project_dir,
                project_name=config.project_name,
                design_name=config.design_name,
                setup_name=config.design_name,
            )
        except Exception as e:
            if "Valid directory, but invalid project filename. 😭 Not found!" in str(e):
                project.save(path=config.project_path)
                renderer._pinfo = epr.ProjectInfo(
                    do_connect=True,
                    project_path=config.project_dir,
                    project_name=config.project_name,
                    design_name=config.design_name
                )
            else:
                raise e        

        renderer.initiated = True

        return renderer
