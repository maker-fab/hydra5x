#include "rep5x_ik.hpp"
#include <cstdio>
#include <cmath>

static bool close(double a, double b, double tol=1e-9){ return std::fabs(a-b)<tol; }

int main(){
  Rep5xParams p; p.lc = 5.0; p.lb = 47.9;
  int fails = 0;

  // Cas 1: outil vertical (b=c=0) -> joint == native (aucun deport)
  {
    Vec5 n{10,20,30,0,0};
    Vec5 j = native_to_joint(n, p, true);
    if(!(close(j.x,10)&&close(j.y,20)&&close(j.z,30))){ printf("FAIL cas1 vertical: %f %f %f\n", j.x,j.y,j.z); fails++; }
  }

  // Cas 2: TCP desactive -> passthrough identite
  {
    Vec5 n{1,2,3,45,30};
    Vec5 j = native_to_joint(n, p, false);
    if(!(close(j.x,1)&&close(j.y,2)&&close(j.z,3)&&close(j.i,45)&&close(j.j,30))){ printf("FAIL cas2 passthrough\n"); fails++; }
  }

  // Cas 3: aller-retour inverse puis directe doit redonner le point de depart (a angles i,j fixes)
  {
    Vec5 n{15,-7,40,33,62};
    Vec5 j = native_to_joint(n, p, true);
    Vec5 back = joint_to_native(j, p, true);
    if(!(close(back.x,n.x,1e-6)&&close(back.y,n.y,1e-6)&&close(back.z,n.z,1e-6))){
      printf("FAIL cas3 roundtrip: got (%f,%f,%f) want (%f,%f,%f)\n", back.x,back.y,back.z,n.x,n.y,n.z);
      fails++;
    }
  }

  // Cas 4: rotation C pure (yaw), B=0 -> deplacement dans plan XY seulement, Z inchange
  {
    Vec5 n{0,0,20,90,0}; // C=90deg, B=0
    Vec5 j = native_to_joint(n, p, true);
    if(!close(j.z,20)){ printf("FAIL cas4 z devrait rester 20, got %f\n", j.z); fails++; }
  }

  printf(fails==0 ? "OK: 4/4 cas passent\n" : "ECHEC: %d cas en erreur\n", fails);
  return fails;
}
