cd /root/merge
export DEBIAN_FRONTEND=noninteractive
echo "=== try apt install u-boot-tools dtc ==="
(apt-get update -qq && apt-get install -y -qq u-boot-tools device-tree-compiler) > /tmp/apt.log 2>&1 && echo APT_OK || (echo APT_FAIL; tail -5 /tmp/apt.log)
command -v dumpimage && dumpimage -l p7.bin 2>&1 | head -80
echo DONE