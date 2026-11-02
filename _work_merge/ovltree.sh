cd /root/merge
echo "=== full overlay tree ==="
find ovl/upper -printf "%y %10s %TY-%Tm-%Td %TH:%TM  %p\n" | sed "s|ovl/upper||" | sort -k4 | head -200
echo "=== total count ==="
find ovl/upper -type f | wc -l; find ovl/upper -type d | wc -l
echo DONE