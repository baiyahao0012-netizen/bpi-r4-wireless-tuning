export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq p7zip-full p7zip-rar unrar-free unar > /tmp/rar.log 2>&1 && echo APT_OK || (echo APT_PARTIAL; tail -5 /tmp/rar.log)
for t in 7z 7za unrar unar bsdtar; do printf "%s -> " $t; command -v $t || echo MISSING; done
mkdir -p /root/merge/incoming
cp "/mnt/c/Users/15732/.dsh/attachments/v1/files/38/38d0a35ecc14a691d48635310ca0b5606adcd08a1833552237aa9a814de10df5/backports-src.rar" /root/merge/incoming/ 2>&1 && echo COPY_OK
ls -la /root/merge/incoming/
echo "=== list rar ==="
(7z l /root/merge/incoming/backports-src.rar 2>&1 || unrar l /root/merge/incoming/backports-src.rar 2>&1 || unar -l /root/merge/incoming/backports-src.rar 2>&1) | head -80
echo DONE