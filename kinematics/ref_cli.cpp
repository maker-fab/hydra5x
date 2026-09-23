// CLI minimal pour exposer rep5x_ik sans binding Python (pas de python3-dev requis).
// Usage: ref_cli <inverse|forward> <LC> <LB> < points.txt
// points.txt: une ligne "x y z c_deg b_deg" par point, stdout: meme format transforme.
#include "rep5x_ik.hpp"
#include <iostream>
#include <sstream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 4) {
    std::cerr << "usage: ref_cli <inverse|forward> <LC> <LB>\n";
    return 2;
  }
  const std::string mode = argv[1];
  Rep5xParams p;
  p.lc = std::stod(argv[2]);
  p.lb = std::stod(argv[3]);

  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty()) continue;
    std::istringstream iss(line);
    Vec5 v;
    iss >> v.x >> v.y >> v.z >> v.i >> v.j;
    Vec5 out = (mode == "inverse") ? native_to_joint(v, p, true) : joint_to_native(v, p, true);
    std::cout << out.x << ' ' << out.y << ' ' << out.z << ' ' << out.i << ' ' << out.j << '\n';
  }
  return 0;
}
