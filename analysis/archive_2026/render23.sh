cd /c/SoftRobotEvolution
for n in stage1c_s2 stage1c_s3; do
  echo "=== $n ==="
  python render_champion.py results/$n/best_robot.pkl --sim-time 3 --amp 0.16 2>&1 | tail -3
done
