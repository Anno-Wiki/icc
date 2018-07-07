#!/bin/bash
python book.$1.py $2.txt $2.01.icc $4 $5 $6
sed '/^$/d' $2.01.icc > $2.02.icc 
python book.$1.py $2.02.icc $2.03.icc 
sed '/^$/d' $2.03.icc > $2.04.icc 
python book.$1.py $2.04.icc $2.05.icc 
sed '/^$/d' $2.05.icc > $2.06.icc 
python book.$1.py $2.06.icc $2.07.icc 
sed '/^$/d' $2.07.icc > $2.08.icc 
sort $2.08.icc | sed 's/@[0-9]*//g' | uniq > $2.dict 
python pos.py $2.08.icc $2.09.icc $3
cp $2.09.icc $2.out.icc 
cp $2.09.icc $2.icc 
rm $2.0* 
