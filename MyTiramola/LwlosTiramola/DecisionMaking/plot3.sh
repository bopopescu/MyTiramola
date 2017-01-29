#/bin/bash

python3 $1 -p > $2.out
echo "set term png; set output \"$2.png\"; plot \"$2.out\" using 0:1 with lines, \"$2.out\" using 0:2 with lines, \"$2.out\" using 0:3 with lines" | gnuplot
gnome-open $2.png
