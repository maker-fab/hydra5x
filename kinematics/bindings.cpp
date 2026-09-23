#include <pybind11/pybind11.h>
#include "rep5x_ik.hpp"

namespace py = pybind11;

PYBIND11_MODULE(rep5x_ik, m) {
  m.doc() = "Arbitre de reference: extraction fidele de la cinematique PENTA_AXIS_HH "
            "(dennisklappe/rep5x-marlin, penta_axis_head_head.cpp). Angles en degres, longueurs en mm.";

  py::class_<Vec5>(m, "Vec5")
      .def(py::init<>())
      .def(py::init<double, double, double, double, double>(),
           py::arg("x") = 0, py::arg("y") = 0, py::arg("z") = 0,
           py::arg("i") = 0, py::arg("j") = 0)
      .def_readwrite("x", &Vec5::x)
      .def_readwrite("y", &Vec5::y)
      .def_readwrite("z", &Vec5::z)
      .def_readwrite("i", &Vec5::i, "C (yaw, deg)")
      .def_readwrite("j", &Vec5::j, "B (tilt, deg)")
      .def("__repr__", [](const Vec5 &v) {
        return "Vec5(x=" + std::to_string(v.x) + ", y=" + std::to_string(v.y) +
               ", z=" + std::to_string(v.z) + ", i=" + std::to_string(v.i) +
               ", j=" + std::to_string(v.j) + ")";
      });

  py::class_<Rep5xParams>(m, "Rep5xParams")
      .def(py::init<>())
      .def_readwrite("lc", &Rep5xParams::lc, "LC (mm) - offset Y pivot C -> pivot B")
      .def_readwrite("lb", &Rep5xParams::lb, "LB (mm) - offset Z pointe -> pivot B, outil vertical")
      .def_readwrite("hotend_offset_x", &Rep5xParams::hotend_offset_x)
      .def_readwrite("hotend_offset_y", &Rep5xParams::hotend_offset_y)
      .def_readwrite("hotend_offset_z", &Rep5xParams::hotend_offset_z)
      .def_readwrite("has_hotend_offset", &Rep5xParams::has_hotend_offset);

  m.def("native_to_joint", &native_to_joint,
        py::arg("native"), py::arg("params"), py::arg("tool_centerpoint_control") = true,
        "TCP (pointe outil) -> coordonnees machine. Cinematique inverse.");

  m.def("joint_to_native", &joint_to_native,
        py::arg("joints_pos"), py::arg("params"), py::arg("tool_centerpoint_control") = true,
        "Coordonnees machine -> TCP. Cinematique directe.");
}
