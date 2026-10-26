#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <arpa/inet.h>

static int mac_pton(const char *s, unsigned char *m) {
    return sscanf(s, "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
                  &m[0],&m[1],&m[2],&m[3],&m[4],&m[5]) == 6;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s iface dst_mac [payload]\n", argv[0]);
        return 1;
    }
    const char *ifname = argv[1];
    unsigned char dst[6];
    if (!mac_pton(argv[2], dst)) { fprintf(stderr,"bad mac\n"); return 1; }
    const char *payload = argc > 3 ? argv[3] : "HELLO_RTC_OVER_WIFI";

    int fd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (fd < 0) { perror("socket"); return 1; }

    struct ifreq ifr;
    memset(&ifr,0,sizeof(ifr));
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ-1);
    if (ioctl(fd, SIOCGIFINDEX, &ifr) < 0) { perror("SIOCGIFINDEX"); return 1; }
    int ifindex = ifr.ifr_ifindex;
    if (ioctl(fd, SIOCGIFHWADDR, &ifr) < 0) { perror("SIOCGIFHWADDR"); return 1; }
    unsigned char src[6];
    memcpy(src, ifr.ifr_hwaddr.sa_data, 6);

    unsigned char frame[1600];
    memset(frame,0,sizeof(frame));
    memcpy(frame, dst, 6);
    memcpy(frame+6, src, 6);
    frame[12] = 0x88; frame[13] = 0xB5;
    size_t plen = strlen(payload);
    if (plen > sizeof(frame)-14) plen = sizeof(frame)-14;
    memcpy(frame+14, payload, plen);
    size_t flen = 14 + plen;
    if (flen < 60) flen = 60;

    struct sockaddr_ll sll;
    memset(&sll,0,sizeof(sll));
    sll.sll_family = AF_PACKET;
    sll.sll_ifindex = ifindex;
    sll.sll_halen = 6;
    memcpy(sll.sll_addr, dst, 6);

    printf("iface=%s src=%02x:%02x:%02x:%02x:%02x:%02x dst=%02x:%02x:%02x:%02x:%02x:%02x len=%zu\n",
        ifname, src[0],src[1],src[2],src[3],src[4],src[5],
        dst[0],dst[1],dst[2],dst[3],dst[4],dst[5], flen);
    for (int i=0;i<5;i++) {
        ssize_t n = sendto(fd, frame, flen, 0, (struct sockaddr*)&sll, sizeof(sll));
        printf("send %zd: %s\n", n, n<0?strerror(errno):"ok");
        usleep(200000);
    }
    close(fd);
    return 0;
}
