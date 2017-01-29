#/bin/bash

for d in {0..9}
do
    sed -ri "s/discount.*/discount\"         : 0.$d,/" $1.json
    python $1.py >> $1$d.out
done

paplay ~/Dropbox/install/files/ttardy00.wav

