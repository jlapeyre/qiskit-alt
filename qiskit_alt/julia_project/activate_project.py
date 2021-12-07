import logging
import os
from os.path import dirname
import julia

class JuliaProject:
    """
    A class to manage a Julia project with a Python front end.

    The Julia project exists within a python module.

    This class manages
    1) Setting up the julia module provided by pyjulia, including building PyCall.jl
    2) Downloading and installing Julia packages (and a registry)
    3) Setting up the Julia module, including loading a custom system image
    4) Loading Julia modules
    5) Compiling a system image for the Julia Project
    """

    def __init__(self, name,
                 registry_url=None,
                 sys_image_dir="sys_image",
                 sys_image_file=None,
                 logging_level=None
                 ):

        self.name = name
        self.toplevel = dirname(dirname(dirname(__file__)))
        self.sys_image_dir = sys_image_dir
        if sys_image_file is None:
            sys_image_file = "sys_" + name + ".so"
        self.sys_image_file = sys_image_file
        self.registry_url = registry_url
        self.setup_logging(level=logging_level)
        self.logger.info("Initing JuliaProject")
        self.find_julia()
        self.init_julia_module()
        self.start_julia()
        self.diagnostics_after_init()
        self.check_and_install_julia_packages()

    def setup_logging(self, console=False, level=None): # logging.WARNING
        if level is None:
            logging_level = logging.INFO
        else:
            logging_level = level

        logger = logging.getLogger(self.name)
        logger.setLevel(logging_level)
        fh = logging.FileHandler(self.name + '.log')
        fh.setLevel(logging_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        if console:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(formatter)
            logger.addHandler(ch)

        self.logger = logger

    def find_julia(self):
        logger = self.logger
        if os.path.exists(os.path.join(self.toplevel, self.name, "julia_path.py")):
            from ..julia_path import julia_path
            logger.info('julia_path.py exists')
            if julia_path == "":
                logger.info('julia_path.julia_path=="".')
            else:
                logger.info('Non-empty julia_path.julia_path=="%s".', julia_path)
        else:
            julia_path = ""
            logger.info('julia_path.py does not exist')

        # The canonical place to look for a Julia installation is ./julia/bin/julia

        julia_directory_in_toplevel = os.path.join(self.toplevel, "julia")
        julia_executable_under_toplevel = os.path.join(julia_directory_in_toplevel, "bin", "julia")
        if os.path.exists(julia_executable_under_toplevel) and julia_path == "":
            julia_path = julia_executable_under_toplevel
            logger.info("Using executable from julia installation in julia project toplevel '%s'.", julia_path)
        elif os.path.exists(julia_directory_in_toplevel):
            if os.path.isdir(julia_directory_in_toplevel):
                msg = "WARNING: directory ./julia/ found under toplevel, but ./julia/bin/julia not found."
                logger.info(msg)
                print(msg)
            else:
                msg = "WARNING: ./julia found under toplevel, but it is not a directory as expected."
                logger.warn(msg)
                print(msg)
        else:
            logger.info("No julia installation found at '%s'.", julia_directory_in_toplevel)

        self.julia_path = julia_path

    # If the binary does not exist, the standard search path will be used

    def init_julia_module(self):
        julia_path = self.julia_path
        logger = self.logger
        from julia.api import LibJulia, JuliaInfo

        def load_julia(julia_path, logger):
            if os.path.exists(julia_path):
                api = LibJulia.load(julia=julia_path)
                info = JuliaInfo.load(julia=julia_path)
            else:
                logger.info("Searching for julia in user's path")
                api = LibJulia.load()
                info = JuliaInfo.load()
            return api, info
        (api, info) = load_julia(julia_path, logger)
        logger.info("Loaded LibJulia and JuliaInfo.")

        if not info.is_pycall_built():
            logger.info("PyCall not built. Installing julia module.")
            if os.path.exists(julia_path):
                julia.install(julia=julia_path)
            else:
                julia.install()

        self.api = api
        self.info = info

    def start_julia(self):
        logger = self.logger
        # TODO: support mac and win here
        sys_image_path = os.path.join(self.toplevel, self.sys_image_dir, self.sys_image_file)
        self.sys_image_path = sys_image_path
        sys_image_path_exists = os.path.exists(sys_image_path)
        self.sys_image_path_exists = sys_image_path_exists

        if sys_image_path_exists:
            self.api.sysimage = sys_image_path
            logger.info("Loading system image %s", sys_image_path)
        else:
            logger.info("No custom system image found.")

            # Both the path and possibly the sysimage have been set. Now initialize Julia.
        logger.info("Initializing julia")
        self.api.init_julia()


    def diagnostics_after_init(self):
        # TODO replace several calls for info below using the JuliaInfo object
        # Import these to reexport
        logger = self.logger
        from julia import Main
        logger.info("Julia version %s", Main.string(Main.VERSION))

        loaded_sys_image_path = Main.eval('unsafe_string(Base.JLOptions().image_file)')
        logger.info("Probed system image path %s", loaded_sys_image_path)

        # Activate the Julia project

        # Maybe useful
        from julia import Base
        julia_cmd = julia.Base.julia_cmd()
        logger.info("Probed julia command: %s", julia_cmd)

        from julia import Pkg
        Pkg.activate(self.toplevel) # Use package data in Project.toml
        logger.info("Probed Project.toml path: %s", Pkg.project().path)

        from os.path import dirname
#        toplevel = dirname(dirname(__file__))
        julia_src_dir = os.path.join(self.toplevel, "julia_src")

        self.julia_src_dir = julia_src_dir
        self.loaded_sys_image_path = loaded_sys_image_path

    def check_and_install_julia_packages(self):
        logger = self.logger
        from julia import Pkg
        ### Instantiate Julia project, i.e. download packages, etc.
        julia_manifest_path = os.path.join(self.toplevel, "Manifest.toml")
        # Assume that if built system image exists, then Julia packages are installed.
        if self.sys_image_path_exists or os.path.exists(julia_manifest_path):
            logger.info("Julia project packages found.")
        else:
            print("Julia packages not installed, installing...")
            logger.info("Julia packages not installed or found.")
            if self.registry_url:
                logger.info(f"Installing registry from {self.registry_url}.")
                #            Pkg.Registry
                Pkg.Registry.add(Pkg.RegistrySpec(url = self.registry_url))
            else:
                logger.info(f"No registry installation requested.")
            logger.info("Pkg.resolve()")
            Pkg.resolve()
            logger.info("Pkg.instantiate()")
            Pkg.instantiate()

    def compile_julia_project(self):
        """
        Compile a Julia system image with all requirements for the julia project.
        """
        logger = self.logger
        from julia import Main, Pkg
        if self.loaded_sys_image_path == self.sys_image_path:
            msg = "WARNING: Compiling system image while compiled system image is loaded.\n" \
                + f"Consider deleting  {sys_image_path} and restarting python."
            print(msg)
            logger.warn(msg)
        from julia import Pkg
        syspath = os.path.join(self.toplevel, "sys_image")
        Main.eval('ENV["PYCALL_JL_RUNTIME_PYTHON"] = Sys.which("python")')
        Pkg.activate(syspath)
        logger.info("Compiling: probed Project.toml path: %s", Pkg.project().path)
        Main.cd(syspath)
        try:
            Pkg.resolve()
        except:
            msg = "Pkg.resolve() failed. Updating packages."
            print(msg)
            logger.info(msg)
            Pkg.update()
            Pkg.resolve()
        Pkg.instantiate()
        compile_script = "compile_" + self.name + ".jl"
        Main.include(compile_script)
