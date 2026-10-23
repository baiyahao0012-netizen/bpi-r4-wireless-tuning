// edca_set.c - runtime AP downlink EDCA setter via nl80211 (no wifi reload)
// usage: edca_set <ifname> <ac 0=BE 1=BK 2=VI 3=VO> <aifs> <cwmin> <cwmax> <txop>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>
#include <linux/netlink.h>
#include <linux/genetlink.h>
#include <net/if.h>

#ifndef NLA_F_NESTED
#define NLA_F_NESTED (1 << 15)
#endif
#define NLA_ALIGNTO 4
#define NLA_ALIGN(len) (((len) + NLA_ALIGNTO - 1) & ~(NLA_ALIGNTO - 1))

#define NL80211_CMD_SET_WIPHY 2
#define NL80211_ATTR_WIPHY 1
#define NL80211_ATTR_IFINDEX 3
#define NL80211_ATTR_WIPHY_TXQ_PARAMS 37
#define NL80211_TXQ_ATTR_AC 1
#define NL80211_TXQ_ATTR_TXOP 2
#define NL80211_TXQ_ATTR_CWMIN 3
#define NL80211_TXQ_ATTR_CWMAX 4
#define NL80211_TXQ_ATTR_AIFS 5
#define TXQ_SUBBLOCK_TYPE 13

#define CTRL_CMD_GETFAMILY 3
#define CTRL_ATTR_FAMILY_ID 1
#define CTRL_ATTR_FAMILY_NAME 2

static const int user_to_nl80211[4] = { 2, 3, 1, 0 }; // BE BK VI VO

struct nlbuf {
    char buf[4096];
    int len;
};

static void put_attr(struct nlbuf *b, int type, const void *data, int len)
{
    struct nlattr *a = (struct nlattr *)(b->buf + b->len);
    a->nla_type = type;
    a->nla_len = sizeof(*a) + len;
    memcpy((char *)a + sizeof(*a), data, len);
    int total = NLA_ALIGN(a->nla_len);
    memset((char *)a + a->nla_len, 0, total - a->nla_len);
    b->len += total;
}

static int nest_start(struct nlbuf *b, int type)
{
    int off = b->len;
    struct nlattr *a = (struct nlattr *)(b->buf + b->len);
    a->nla_type = type | NLA_F_NESTED;
    a->nla_len = sizeof(*a);
    b->len += sizeof(*a);
    return off;
}

static void nest_end(struct nlbuf *b, int off)
{
    struct nlattr *a = (struct nlattr *)(b->buf + off);
    a->nla_len = b->len - off;
    int total = NLA_ALIGN(a->nla_len);
    memset(b->buf + b->len, 0, total - a->nla_len);
    b->len += total - a->nla_len;
}

static int nl_open(void)
{
    int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_GENERIC);
    if (fd < 0) { perror("socket"); exit(1); }
    struct sockaddr_nl sa = { .nl_family = AF_NETLINK };
    if (bind(fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) { perror("bind"); exit(1); }
    struct timeval tv = { .tv_sec = 3, .tv_usec = 0 };
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    return fd;
}

static int send_msg(int fd, struct nlbuf *b)
{
    struct nlmsghdr *nlh = (struct nlmsghdr *)b->buf;
    struct sockaddr_nl sa = { .nl_family = AF_NETLINK };
    if (sendto(fd, b->buf, b->len, 0, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        perror("sendto"); return -1;
    }
    return 0;
}

static int get_family_id(int fd)
{
    struct nlbuf b = { .len = NLMSG_HDRLEN + GENL_HDRLEN };
    struct nlmsghdr *nlh = (struct nlmsghdr *)b.buf;
    struct genlmsghdr *gh = (struct genlmsghdr *)(b.buf + NLMSG_HDRLEN);
    nlh->nlmsg_len = b.len;
    nlh->nlmsg_type = GENL_ID_CTRL;
    nlh->nlmsg_flags = NLM_F_REQUEST;
    nlh->nlmsg_seq = 1;
    nlh->nlmsg_pid = 0;
    gh->cmd = CTRL_CMD_GETFAMILY;
    gh->version = 1;
    put_attr(&b, CTRL_ATTR_FAMILY_NAME, "nl80211", sizeof("nl80211"));
    nlh->nlmsg_len = b.len;
    if (send_msg(fd, &b) < 0) return -1;

    char rbuf[4096];
    int n = recv(fd, rbuf, sizeof(rbuf), 0);
    if (n < 0) { perror("recv family"); return -1; }
    for (nlh = (struct nlmsghdr *)rbuf; NLMSG_OK(nlh, n); nlh = NLMSG_NEXT(nlh, n)) {
        if (nlh->nlmsg_type == NLMSG_ERROR) return -1;
        gh = (struct genlmsghdr *)NLMSG_DATA(nlh);
        int alen = nlh->nlmsg_len - NLMSG_HDRLEN - GENL_HDRLEN;
        struct nlattr *a = (struct nlattr *)((char *)gh + GENL_HDRLEN);
        while (alen >= (int)sizeof(*a) && a->nla_len >= sizeof(*a) && a->nla_len <= alen) {
            if ((a->nla_type & 0x3fff) == CTRL_ATTR_FAMILY_ID) {
                return *(uint16_t *)((char *)a + sizeof(*a));
            }
            int step = NLA_ALIGN(a->nla_len);
            alen -= step;
            a = (struct nlattr *)((char *)a + step);
        }
    }
    return -1;
}

int main(int argc, char **argv)
{
    if (argc != 7) {
        fprintf(stderr, "usage: %s <ifname> <ac 0=BE 1=BK 2=VI 3=VO> <aifs> <cwmin> <cwmax> <txop>\n", argv[0]);
        return 2;
    }
    const char *ifname = argv[1];
    int ac = atoi(argv[2]);
    int aifs = atoi(argv[3]);
    int cwmin = atoi(argv[4]);
    int cwmax = atoi(argv[5]);
    int txop = atoi(argv[6]);
    if (ac < 0 || ac > 3) { fprintf(stderr, "ac must be 0..3\n"); return 2; }

    unsigned ifindex = if_nametoindex(ifname);
    if (!ifindex) { fprintf(stderr, "no such interface: %s\n", ifname); return 1; }

    int fd = nl_open();
    int fam = get_family_id(fd);
    if (fam < 0) { fprintf(stderr, "cannot resolve nl80211 family\n"); return 1; }

    struct nlbuf b = { .len = NLMSG_HDRLEN + GENL_HDRLEN };
    struct nlmsghdr *nlh = (struct nlmsghdr *)b.buf;
    struct genlmsghdr *gh = (struct genlmsghdr *)(b.buf + NLMSG_HDRLEN);
    nlh->nlmsg_len = b.len;
    nlh->nlmsg_type = fam;
    nlh->nlmsg_flags = NLM_F_REQUEST | NLM_F_ACK;
    nlh->nlmsg_seq = 2;
    nlh->nlmsg_pid = 0;
    gh->cmd = NL80211_CMD_SET_WIPHY;
    gh->version = 1;

    uint32_t idx = ifindex;
    put_attr(&b, NL80211_ATTR_IFINDEX, &idx, sizeof(idx));

    int outer = nest_start(&b, NL80211_ATTR_WIPHY_TXQ_PARAMS);
    int sub = nest_start(&b, TXQ_SUBBLOCK_TYPE);
    uint8_t ac_nl = (uint8_t)user_to_nl80211[ac];
    uint16_t v16;
    uint8_t v8;
    put_attr(&b, NL80211_TXQ_ATTR_AC, &ac_nl, sizeof(ac_nl));
    v16 = (uint16_t)txop;  put_attr(&b, NL80211_TXQ_ATTR_TXOP, &v16, sizeof(v16));
    v16 = (uint16_t)cwmin; put_attr(&b, NL80211_TXQ_ATTR_CWMIN, &v16, sizeof(v16));
    v16 = (uint16_t)cwmax; put_attr(&b, NL80211_TXQ_ATTR_CWMAX, &v16, sizeof(v16));
    v8 = (uint8_t)aifs;    put_attr(&b, NL80211_TXQ_ATTR_AIFS, &v8, sizeof(v8));
    nest_end(&b, sub);
    nest_end(&b, outer);

    nlh->nlmsg_len = b.len;
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    if (send_msg(fd, &b) < 0) return 1;

    char rbuf[4096];
    int n = recv(fd, rbuf, sizeof(rbuf), 0);
    if (n < 0) { perror("recv ack"); return 1; }
    for (nlh = (struct nlmsghdr *)rbuf; NLMSG_OK(nlh, n); nlh = NLMSG_NEXT(nlh, n)) {
        if (nlh->nlmsg_type == NLMSG_ERROR) {
            struct nlmsgerr *e = (struct nlmsgerr *)NLMSG_DATA(nlh);
            if (e->error) {
                fprintf(stderr, "kernel error %d: %s\n", e->error, strerror(-e->error));
                return 1;
            }
            clock_gettime(CLOCK_MONOTONIC, &t1);
            double us = (t1.tv_sec - t0.tv_sec) * 1e6 +
                        (t1.tv_nsec - t0.tv_nsec) / 1e3;
            printf("OK: %s AC%d aifs=%d cwmin=%d cwmax=%d txop=%d latency_us=%.1f\n",
                   ifname, ac, aifs, cwmin, cwmax, txop, us);
            return 0;
        }
    }
    fprintf(stderr, "no ACK\n");
    return 1;
}
