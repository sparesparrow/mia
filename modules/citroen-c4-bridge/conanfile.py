from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake


class CitroenC4Bridge(ConanFile):
    """Conan package for Citroën C4 Vehicle Bridge"""

    name = "citroen-c4-bridge"
    version = "1.0.0"
    description = "Hexagonal adapter for Citroën C4 vehicle integration with Android USB-OTG"
    license = "MIT"
    author = "MIA Universal"
    topics = ("automotive", "citroen", "obd", "android", "psa")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tests": [True, False],
        "enable_simulation": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tests": False,
        "enable_simulation": True  # Enable simulation mode for development
    }

    exports_sources = "CMakeLists.txt", "src/*", "include/*", "test/*"

    def configure(self):
        if self.settings.os == "Android":
            # Android-specific configurations
            self.options["zeromq"].shared = False

    def requirements(self):
        # Core dependencies
        self.requires("zeromq/4.3.5")
        self.requires("flatbuffers/23.5.26")

        # OBD transport agent
        self.requires("obd-transport-agent/1.0.0")

        # MIA core
        self.requires("mia-core/1.2.0")

        # Android NDK for native compilation
        if self.settings.os == "Android":
            self.requires("android-ndk/r26b")

    def build_requirements(self):
        self.tool_requires("cmake/3.27.0")

    def layout(self):
        self.folders.generators = "build"

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = self.options.with_tests
        tc.variables["ENABLE_SIMULATION"] = self.options.enable_simulation
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
        self.cpp_info.libs = ["citroen_c4_bridge"]

        # Python module information
        self.cpp_info.set_property("cmake_file_name", "CitroenC4Bridge")
        self.cpp_info.set_property("cmake_target_name", "CitroenC4Bridge::CitroenC4Bridge")

        # Add Python path for MIA bootstrap
        if self.settings.os == "Android":
            self.env_info.PYTHONPATH.append(self.package_folder)
            self.env_info.LD_LIBRARY_PATH.append(self.package_folder / "lib")
