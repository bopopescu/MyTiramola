#!/bin/bash

#for s in start start_chain half half_chain end always
for s in always
do
    python $1.py $s >> $1_$s.out
done

paplay ~/Dropbox/install/files/ttardy00.wav

