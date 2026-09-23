# Chemin de build unique pour Linux / macOS / Windows.
# Sous Linux et macOS un simple g++/clang++ suffit aussi ; sous Windows
# CMake est la seule voie raisonnable (MSVC n'a pas de g++).
cmake_minimum_required(VERSION 3.15)
project(rep5x_ik LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Les binaires atterrissent a cote des sources : compare.py et sanity les
# cherchent la, quel que soit le generateur (Makefile, Ninja, MSVC).
foreach(cfg "" _DEBUG _RELEASE _RELWITHDEBINFO _MINSIZEREL)
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY${cfg} ${CMAKE_CURRENT_SOURCE_DIR})
endforeach()

add_executable(ref_cli rep5x_ik.cpp ref_cli.cpp)
add_executable(sanity_test rep5x_ik.cpp sanity.cpp)

# Module Python optionnel : absent de la chaine de validation de base,
# donc son absence ne doit pas casser le build des deux binaires.
find_package(pybind11 QUIET)
if(pybind11_FOUND)
  pybind11_add_module(rep5x_ik_py rep5x_ik.cpp bindings.cpp)
  set_target_properties(rep5x_ik_py PROPERTIES OUTPUT_NAME rep5x_ik)
else()
  message(STATUS "pybind11 absent : module Python non construit (facultatif)")
endif()
