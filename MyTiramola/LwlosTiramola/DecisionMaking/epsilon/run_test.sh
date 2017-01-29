#!/bin/bash

for e in 4
do
    python $1.py $e >> $1$e.out
done

paplay ~/Dropbox/install/files/ttardy00.wav

