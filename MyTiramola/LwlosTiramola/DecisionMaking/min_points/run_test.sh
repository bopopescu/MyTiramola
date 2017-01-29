#/bin/bash

#for min_points in 4 8 12 16 20 24 28 32 36 40 44 48 52 56 60 70 80 90 100
for min_points in 2 3 4 5 6 7 8 9 10
do
    sed -ri "s/min_measurements.*/min_measurements\" : $min_points/" $1.json
    python $1.py >> $1$min_points.out
done

paplay ~/Dropbox/install/files/ttardy00.wav

