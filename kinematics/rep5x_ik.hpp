#pragma once

// Extraction standalone de la cinematique PENTA_AXIS_HH de Marlin2ForPipetBot
// (dennisklappe/rep5x-marlin, Marlin/src/module/penta_axis_head_head.cpp).
// Meme algebre que le firmware. Convention figee via firmware-builder:
// AXIS4_NAME='C' (yaw, coordonnee I), AXIS5_NAME='B' (tilt, coordonnee J).
// Angles en degres, longueurs en mm -- identique au G-code envoye a la machine.

struct Vec5 {
  double x = 0, y = 0, z = 0, i = 0, j = 0; // i = C (yaw, deg), j = B (tilt, deg)
};

struct Rep5xParams {
  double lc = 0.0;   // DEFAULT_ROTATIONAL_JOINT_OFFSET_Y, offset Y du pivot C vers pivot B
  double lb = 47.9;  // DEFAULT_ROTATIONAL_JOINT_OFFSET_Z, offset Z pointe->pivot B, outil vertical
  double hotend_offset_x = 0.0;
  double hotend_offset_y = 0.0;
  double hotend_offset_z = 0.0;
  bool has_hotend_offset = false;
};

// native_to_joint: coordonnees TCP (pointe d'outil, G43.4 actif) -> coordonnees machine (delta[]).
// Correspond exactement a native_to_joint() dans penta_axis_head_head.cpp.
Vec5 native_to_joint(const Vec5 &native, const Rep5xParams &p, bool tool_centerpoint_control);

// joint_to_native: coordonnees machine -> coordonnees TCP. Inverse de native_to_joint.
// Correspond a joint_to_native() dans penta_axis_head_head.cpp.
Vec5 joint_to_native(const Vec5 &joints_pos, const Rep5xParams &p, bool tool_centerpoint_control);
