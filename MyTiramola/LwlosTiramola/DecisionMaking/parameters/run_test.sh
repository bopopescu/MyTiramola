#/usr/bin/env bash

for p in {0..3}
do
    python $1.py $p >> $1$p.out
done

paplay ~/Dropbox/install/files/ttardy00.wav

