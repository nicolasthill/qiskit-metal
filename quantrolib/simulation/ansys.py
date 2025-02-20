from typing import Any, Dict, List

from qiskit_metal.renderers.renderer_ansys.hfss_renderer import QHFSSRenderer

from quantrolib.simulation import Config, RenderConfig, SimulationConfig, ReportConfig

# Configure logging
from logger import logger as log


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

        # Rebuild the design and get the renderer.
        design = config.design
        design.rebuild()

        self.renderer: QHFSSRenderer = config.design.renderers.hfss

        # Select project path, name and design
        self.renderer._options["project_path"] = config.project_path
        self.renderer._options["project_name"] = config.project_name
        self.renderer._options["design_name"] = config.design_name

        # Connect to the renderer
        self.renderer.start()

        # Check loaded project
        if config.project_name is None:
            project_name = self.renderer._pinfo.project_name
            project_path = self.renderer._pinfo.project_path
            log.info(
                "No project name provided. "
                f"Automatically connected to project {project_name} at {project_path}."
            )
        elif config.project_name == self.renderer._pinfo.project_name:
            log.info(f"Project '{config.project_name}' successfully loaded")
        else:
            project_name = self.renderer._pinfo.project_name
            raise ValueError(
                f"The loaded project '{project_name}' does not match the provided "
                f"project name '{config.project_name}'."
            ) 

        # Check loaded design
        if config.design_name is None:
            design_name = self.renderer._pinfo.design_name
            project_name = self.renderer._pinfo.project_name
            log.info(
                "No design name provided. "
                f"Automatically connected to {design_name} in {project_name}."
            )
            log.warning(
                "Always provide a design name to avoid overwriting designs."
            )
        elif config.design_name == self.renderer._pinfo.design_name:
            log.info(f"Design '{config.design_name}' successfully loaded")
        else:
            design_name = self.renderer._pinfo.design_name
            raise ValueError(
                f"The loaded design '{design_name}' does not match the provided "
                f"design name '{config.design_name}'."
            )

        # # Check if the design already exists and warn if so.
        # if (
        #     hasattr(self.renderer, 'active_design')
        #     and self.renderer.active_design == config.design_name
        # ):
        #     log.warning(
        #         f"ANSYS design '{config.design_name}' already exists. "
        #         "Using existing design."
        #     )
        # else:
        #     try:
        #         self.renderer.new_ansys_design(config.design_name, config.mode)
        #     except Exception as e:
        #         # Check if the error corresponds to "design already exists".
        #         # (This check may need to be adjusted to your COM error format.)
        #         try:
        #             hr = e.args[2][5]
        #         except Exception:
        #             hr = None
        #         if hr == -2147024885:
        #             log.warning(
        #                 f"ANSYS design '{config.design_name}' already exists. "
        #                 "Using existing design."
        #             )
        #         else:
        #             raise

        # # Configure meshing
        # if config.max_mesh_length_jj is not None:
        #     self.renderer.options["max_mesh_length_jj"] = config.max_mesh_length_jj
        # if config.max_mesh_length_port is not None:
        #     self.renderer.options["max_mesh_length_port"] = config.max_mesh_length_port

        # # Connect to the design and render it.
        # self.renderer.connect_ansys_design(config.design_name)
        # self.renderer.clean_active_design()
        # self.renderer.render_design(
        #     open_pins=config.open_pins, port_list=config.port_list,
        # )
        log.info("Render ran successfully.")

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
        log.info("Simulation ran successfully.")

    def run_report(self) -> None:
        config: ReportConfig = self._get_current_config("report")

        for field_config in config.field_configs:
            self.renderer.plot_fields(**field_config)

        pass

    def run(self) -> None:
        self.run_render()
        # self.run_simulation()
        # self.run_report()
