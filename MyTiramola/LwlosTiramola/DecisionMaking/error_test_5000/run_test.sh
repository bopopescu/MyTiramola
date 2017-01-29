#/bin/bash

for e in {1..7}
do
    error=$(echo .1^$e | bc -l)
    sed -ri "s/split_error.*/split_error\" : 0$error,/" $1.json
    python $1.py >> $1$e.out
done

paplay ~/Dropbox/install/files/ttardy00.wav

