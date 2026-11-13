#!/bin/bash
cd /tmp/l0
echo "=== recv.err: 链接/管道/pad 相关 ==="
grep -inE 'link|pad|not-linked|cannot|unable|refus|template|recv_rtp|recv_rtcp|send_rtp|send_rtcp|jitterbuffer|rtpbin' t7d.recv.err | grep -viE 'cannot get clock-rate' | head -50
echo
echo "=== send.err: 关键行 ==="
grep -inE 'error|fail|link|not-linked|cannot|unable|refus|missing|rtpbin' t7d.send.err | head -30
echo
echo "=== recv.err 头尾行数 ==="
wc -l t7d.recv.err t7d.send.err
