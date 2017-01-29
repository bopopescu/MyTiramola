#/bin/bash

for i in {1..20}
do
    ./plot3.sh $1 data$i &
done

