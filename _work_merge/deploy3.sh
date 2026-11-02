#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- running cp procs ---"
ps | grep -c "[c]p -f"
cat > /tmp/copymods.sh <<"EOF"
#!/bin/sh
n=0
for f in /tmp/newmods/lib/modules/6.6.73/*.ko; do
  cp -f "$f" /lib/modules/6.6.73/ && n=$((n+1))
done
sync
echo "COPIED $n" > /tmp/copymods.done
EOF
chmod +x /tmp/copymods.sh
rm -f /tmp/copymods.done
nohup sh /tmp/copymods.sh > /tmp/copymods.log 2>&1 &
echo "started pid $!"
' 2>/dev/null
echo "--- poll ---"
for i in 1 2 3 4 5 6; do
  sleep 20
  R=$(ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cat /tmp/copymods.done 2>/dev/null; ps | grep -c "[c]opymods"' 2>/dev/null | tr "\n" " ")
  echo "poll $i: $R"
  case "$R" in *COPIED*) break;; esac
done
