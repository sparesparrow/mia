message(STATUS "Conan: Using CMakeDeps conandeps_legacy.cmake aggregator via include()")
message(STATUS "Conan: It is recommended to use explicit find_package() per dependency instead")

find_package(sparesparrow-protocols)
find_package(sparetools-embedded)

set(CONANDEPS_LEGACY  sparesparrow-protocols::sparesparrow-protocols  sparetools-embedded::sparetools-embedded )