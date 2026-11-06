#!/bin/sh
grep -E "192.168.240" /tmp/dhcp.leases | awk '{print $3, $4}'
