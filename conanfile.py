"""
Root conanfile for MIA C++ platform builds.

This file exists at the repo root so that the CI step
  cd platforms/cpp && conan install ../.. --build=missing
can locate the dependency manifest. The full project conanfile
with advanced options lives at infra/conan/conanfile.py.
"""
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps


class MIACppPlatform(ConanFile):
    name = "mia-cpp-platform"
    version = "2.0.0"
    description = "MIA C++ platform layer (FlatBuffers serialization, embedded bridge)"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires("flatbuffers/23.5.26")
        self.requires("jsoncpp/1.9.5")
        self.requires("openssl/3.0.8")
        self.requires("zlib/1.2.13")

    def build_requirements(self):
        self.tool_requires("flatbuffers/23.5.26")
