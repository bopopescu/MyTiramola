#/bin/bash

for e in 1 2 3 4 5 6 7
do
    error=$(echo .1^$e | bc -l)
    sed -ri "s/split_error.*/split_error\" : 0$error,/" $1.json
    python $1.py >> $1$e.out
done

