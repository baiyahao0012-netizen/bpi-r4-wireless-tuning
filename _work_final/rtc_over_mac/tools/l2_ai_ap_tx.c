// l2_ai_ap_tx: AP-side L2 AI responder + bulk generator.
// Runs on the AP (static aarch64 binary). Frames are AP-originated so they
// traverse the AP egress qdisc, where tc classifies them by EtherType.
//
// usage: l2_ai_ap_tx <iface> <dst_mac> <resp_bytes> <bulk_mbps> <seconds>
#include <arpa/inet.h>
#include <errno.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define ETH_AI 0x88B6
#define ETH_BULK 0x88B7
#define AIHDR_LEN 20
#define SHIM_LEN 12

static volatile int g_stop = 0;
static int g_ifindex = 0;
static unsigned char g_src[6];
static unsigned char g_dst[6];
static int g_sock_ai = -1;
static int g_sock_bulk = -1;

static unsigned short crc_hqx(const unsigned char *d, int n) {
    unsigned short crc = 0;
    for (int i = 0; i < n; i++) {
        crc ^= (unsigned short)d[i] << 8;
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x8000) ? (unsigned short)((crc << 1) ^ 0x1021)
                                 : (unsigned short)(crc << 1);
    }
    return crc;
}

static void put16(unsigned char *p, unsigned v) { p[0] = v >> 8; p[1] = v & 0xff; }
static void put32(unsigned char *p, unsigned v) {
    p[0] = v >> 24; p[1] = (v >> 16) & 0xff; p[2] = (v >> 8) & 0xff; p[3] = v & 0xff;
}
static void put64(unsigned char *p, unsigned long long v) {
    for (int i = 0; i < 8; i++) p[i] = (v >> (56 - 8 * i)) & 0xff;
}

// Build one frame into buf; returns total length.
static int build(unsigned char *buf, unsigned ethertype, unsigned flow,
                 unsigned msg_id, unsigned kind, unsigned long long t0_ns,
                 int payload, int frame_bytes) {
    memset(buf, 0, (size_t)frame_bytes);
    memcpy(buf, g_dst, 6);
    memcpy(buf + 6, g_src, 6);
    put16(buf + 12, ethertype);
    unsigned char *shim = buf + 14;
    int body_len = AIHDR_LEN + payload;
    shim[0] = 0x11; shim[1] = 0x00;
    put16(shim + 2, flow);
    put16(shim + 4, body_len);
    shim[6] = 8; shim[7] = SHIM_LEN;
    put16(shim + 8, 0);
    put16(shim + 10, 0);
    unsigned char *b = shim + SHIM_LEN;
    put32(b, msg_id);
    put16(b + 4, kind);
    put16(b + 6, payload);
    put64(b + 8, t0_ns);
    put32(b + 16, 0);
    unsigned short crc = crc_hqx(shim, SHIM_LEN + body_len);
    put16(shim + 8, crc);
    return 14 + SHIM_LEN + body_len;
}

static int send_frame(int sock, unsigned char *buf, int len) {
    struct sockaddr_ll sll;
    memset(&sll, 0, sizeof(sll));
    sll.sll_family = AF_PACKET;
    sll.sll_ifindex = g_ifindex;
    sll.sll_halen = 6;
    memcpy(sll.sll_addr, g_dst, 6);
    return sendto(sock, buf, (size_t)len, 0, (struct sockaddr *)&sll, sizeof(sll));
}

static void on_signal(int s) { (void)s; g_stop = 1; }

int main(int argc, char **argv) {
    if (argc < 6) {  /* ai_prio optional as argv[6] */
        fprintf(stderr, "usage: %s <iface> <dst_mac> <resp_bytes> <bulk_mbps> <seconds>\n", argv[0]);
        return 1;
    }
    const char *iface = argv[1];
    if (sscanf(argv[2], "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx", &g_dst[0], &g_dst[1],
               &g_dst[2], &g_dst[3], &g_dst[4], &g_dst[5]) != 6) {
        fprintf(stderr, "bad dst mac\n");
        return 1;
    }
    int resp_bytes = atoi(argv[3]);
    int ai_prio = (argc > 6) ? atoi(argv[6]) : 3;
    double bulk_mbps = atof(argv[4]);
    int seconds = atoi(argv[5]);

    g_ifindex = (int)if_nametoindex(iface);
    if (g_ifindex == 0) { perror("if_nametoindex"); return 1; }

    g_sock_ai = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    g_sock_bulk = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (g_sock_ai < 0 || g_sock_bulk < 0) { perror("socket"); return 1; }
    int prio_ai = 3, prio_bulk = 0;  // overridden by argv[6]
    setsockopt(g_sock_ai, SOL_SOCKET, SO_PRIORITY, &ai_prio, sizeof(ai_prio));
    setsockopt(g_sock_bulk, SOL_SOCKET, SO_PRIORITY, &prio_bulk, sizeof(prio_bulk));
    struct sockaddr_ll bind_sll;
    memset(&bind_sll, 0, sizeof(bind_sll));
    bind_sll.sll_family = AF_PACKET;
    bind_sll.sll_protocol = htons(ETH_P_ALL);
    bind_sll.sll_ifindex = g_ifindex;
    if (bind(g_sock_ai, (struct sockaddr *)&bind_sll, sizeof(bind_sll)) < 0 ||
        bind(g_sock_bulk, (struct sockaddr *)&bind_sll, sizeof(bind_sll)) < 0) {
        perror("bind"); return 1;
    }
    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    strncpy(ifr.ifr_name, iface, IFNAMSIZ - 1);
    if (ioctl(g_sock_ai, SIOCGIFHWADDR, &ifr) < 0) { perror("SIOCGIFHWADDR"); return 1; }
    memcpy(g_src, ifr.ifr_hwaddr.sa_data, 6);

    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    fprintf(stderr, "iface=%s src=%02x:%02x:%02x:%02x:%02x:%02x dst=%02x:%02x:%02x:%02x:%02x:%02x resp=%d bulk=%.1fMbps %ds\n",
            iface, g_src[0], g_src[1], g_src[2], g_src[3], g_src[4], g_src[5],
            g_dst[0], g_dst[1], g_dst[2], g_dst[3], g_dst[4], g_dst[5],
            resp_bytes, bulk_mbps, seconds);

    unsigned char buf[2048];
    int resp_frame = 14 + SHIM_LEN + AIHDR_LEN + resp_bytes;
    int bulk_payload = 1400 - 14 - SHIM_LEN - AIHDR_LEN;   // 1354 -> 1400 bytes on wire
    int bulk_frame = 1400;
    double bulk_bps = bulk_mbps * 1e6 / 8.0;
    double ai_tokens = 0;
    unsigned long long sent_ai = 0, sent_bulk = 0, got_req = 0;
    struct timespec t0, now;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    double last = 0;
    char recvbuf[4096];

    while (!g_stop) {
        clock_gettime(CLOCK_MONOTONIC, &now);
        double elapsed = (now.tv_sec - t0.tv_sec) + (now.tv_nsec - t0.tv_nsec) / 1e9;
        if (elapsed >= seconds) break;

        // drain incoming requests (non-blocking)
        for (;;) {
            ssize_t n = recv(g_sock_ai, recvbuf, sizeof(recvbuf), MSG_DONTWAIT);
            if (n <= 0) break;
            if (n < 14 + SHIM_LEN + AIHDR_LEN) continue;
            unsigned et = ((unsigned char)recvbuf[12] << 8) | (unsigned char)recvbuf[13];
            if (et != ETH_AI) continue;
            const unsigned char *b = (const unsigned char *)recvbuf + 14 + SHIM_LEN;
            unsigned kind = ((unsigned)b[4] << 8) | b[5];
            if (kind != 0) continue;   // only requests
            unsigned msg_id = ((unsigned)b[0] << 24) | ((unsigned)b[1] << 16) |
                              ((unsigned)b[2] << 8) | b[3];
            unsigned long long rt0 = 0;
            for (int i = 0; i < 8; i++) rt0 = (rt0 << 8) | b[8 + i];
            int len = build(buf, ETH_AI, 0, msg_id, 1, rt0, resp_bytes, resp_frame);
            send_frame(g_sock_ai, buf, len);
            sent_ai++;
            got_req++;
        }

        // bulk token bucket
        ai_tokens += bulk_bps * (elapsed - last);
        last = elapsed;
        if (ai_tokens > 4000) ai_tokens = 4000;
        while (ai_tokens >= bulk_frame) {
            int len = build(buf, ETH_BULK, 1, 0, 2, 0, bulk_payload, bulk_frame);
            send_frame(g_sock_bulk, buf, len);
            sent_bulk++;
            ai_tokens -= bulk_frame;
        }
        struct timespec ts = {0, 200000};   // 0.2 ms
        nanosleep(&ts, NULL);
    }

    fprintf(stderr, "done req=%llu ai=%llu bulk=%llu\n", got_req, sent_ai, sent_bulk);
    return 0;
}



