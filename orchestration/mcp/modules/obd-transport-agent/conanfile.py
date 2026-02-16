from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake


class OBDTransportAgent(ConanFile):
    """Conan package for OBD Transport Agent MCP tool"""

    name = "obd-transport-agent"
    version = "1.0.0"
    description = "MCP tool for OBD-II communication with Android USB-OTG support"
    license = "MIT"
    author = "MIA Universal"
    topics = ("obd", "automotive", "mcp", "android", "citroen")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tests": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tests": False
    }

    exports_sources = "CMakeLists.txt", "src/*", "include/*", "test/*"

    def configure(self):
        if self.settings.os == "Android":
            # Android-specific configurations
            # Note: Options for dependencies are set in requirements() method
            pass

    def requirements(self):
        # Core dependencies
        self.requires("flatbuffers/23.5.26")
        self.requires("zeromq/4.3.5")

        # Android-specific configurations
        if self.settings.os == "Android":
            # Ensure static linking for Android
            self.options["flatbuffers"].shared = False
            self.options["zeromq"].shared = False

    def build_requirements(self):
        self.tool_requires("cmake/3.27.0")

    def layout(self):
        self.folders.generators = "build"

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = self.options.with_tests
        tc.variables["ANDROID_BUILD"] = self.settings.os == "Android"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if self.options.with_tests:
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["obd_transport_agent"]

        # Python module information
        self.cpp_info.set_property("cmake_file_name", "OBDTransportAgent")
        self.cpp_info.set_property("cmake_target_name", "OBDTransportAgent::OBDTransportAgent")

        # Add Python path for MIA bootstrap
        if self.settings.os == "Android":
            self.env_info.PYTHONPATH.append(self.package_folder)
            self.env_info.LD_LIBRARY_PATH.append(self.package_folder / "lib")
