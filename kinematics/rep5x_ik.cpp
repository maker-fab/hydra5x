#include "rep5x_ik.hpp"
#include <cmath>

// Compensation Fourier (M667/EEPROM) non reprise ici -- hors scope geometrie pure.

static inline double radians(double deg) { return deg * M_PI / 180.0; }

Vec5 native_to_joint(const Vec5 &native, const Rep5xParams &p, bool tool_centerpoint_control) {
  if (!tool_centerpoint_control) return native;

  Vec5 pos;
  pos.x = p.has_hotend_offset ? native.x - p.hotend_offset_x : native.x;
  pos.y = p.has_hotend_offset ? native.y - p.hotend_offset_y : native.y;
  pos.z = native.z;
  pos.i = native.i;
  pos.j = native.j;

  const double pivot_length = p.has_hotend_offset ? p.lb - p.hotend_offset_z : p.lb;

  // AXIS4_NAME == 'C' (I = yaw C), AXIS5_NAME == 'B' (J = tilt B)
  const double b_rad = radians(pos.j);
  const double c_rad = radians(pos.i);

  const double sin_b = std::sin(b_rad), cos_b = std::cos(b_rad);
  const double sin_c = std::sin(c_rad), cos_c = std::cos(c_rad);

  Vec5 joints_pos;
  joints_pos.x = pos.x - sin_c * p.lc + cos_c * sin_b * pivot_length;
  joints_pos.y = pos.y + (cos_c - 1.0) * p.lc + sin_c * sin_b * pivot_length;
  joints_pos.z = pos.z + (cos_b - 1.0) * pivot_length;
  joints_pos.i = pos.i;
  joints_pos.j = pos.j;

  return joints_pos;
}

// Fix: signe rz errone dans le firmware d'origine (cos(180-b) au lieu de
// cos(b)) casse l'inverse exacte de native_to_joint. cf 5axiskins.c.
Vec5 joint_to_native(const Vec5 &joints_pos, const Rep5xParams &p, bool tool_centerpoint_control) {
  if (!tool_centerpoint_control) return joints_pos;

  const double pivot_length = p.has_hotend_offset ? p.lb - p.hotend_offset_z : p.lb;

  // Meme convention que native_to_joint : AXIS4_NAME=='C' (I=yaw C), AXIS5_NAME=='B' (J=tilt B)
  const double b_rad = radians(joints_pos.j);
  const double c_rad = radians(joints_pos.i);

  const double sin_b = std::sin(b_rad), cos_b = std::cos(b_rad);
  const double sin_c = std::sin(c_rad), cos_c = std::cos(c_rad);

  Vec5 native_pos;
  native_pos.x = joints_pos.x + sin_c * p.lc - cos_c * sin_b * pivot_length;
  native_pos.y = joints_pos.y + (1.0 - cos_c) * p.lc - sin_c * sin_b * pivot_length;
  native_pos.z = joints_pos.z + (1.0 - cos_b) * pivot_length;
  native_pos.i = joints_pos.i;
  native_pos.j = joints_pos.j;

  return native_pos;
}
