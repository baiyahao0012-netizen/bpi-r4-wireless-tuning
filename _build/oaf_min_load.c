#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <linux/netlink.h>

#define FWX_NETLINK_ID 29
#define FWX_MAGIC 0xa0b0c0d0
#define MAX_MSG 1024

struct af_msg_hdr { int magic; int len; };
struct af_msg_t { int action; };

static int send_msg(int fd, int action, const char *feature)
{
    char buf[NLMSG_SPACE(MAX_MSG)];
    struct nlmsghdr *nlh = (struct nlmsghdr *)buf;
    struct sockaddr_nl dst;
    struct af_msg_hdr *h;
    struct af_msg_t *m;
    int flen = feature ? (int)strlen(feature) + 1 : 0;
    int len = (int)sizeof(struct af_msg_t) + flen;

    memset(buf, 0, sizeof(buf));
    nlh->nlmsg_len = NLMSG_SPACE(MAX_MSG);
    nlh->nlmsg_type = 0;
    nlh->nlmsg_pid = 999;
    nlh->nlmsg_seq = 0;
    nlh->nlmsg_flags = 0;

    h = (struct af_msg_hdr *)NLMSG_DATA(nlh);
    h->magic = FWX_MAGIC;
    h->len = len;
    m = (struct af_msg_t *)((char *)h + sizeof(*h));
    m->action = action;
    if (feature)
        memcpy((char *)m + sizeof(*m), feature, flen);

    memset(&dst, 0, sizeof(dst));
    dst.nl_family = AF_NETLINK;
    dst.nl_pid = 0;
    return sendto(fd, buf, nlh->nlmsg_len, 0, (struct sockaddr *)&dst, sizeof(dst));
}

int main(int argc, char **argv)
{
    int fd;
    FILE *fp;
    char line[1024];
    struct sockaddr_nl src;

    if (argc < 2) {
        fprintf(stderr, "usage: %s feature.txt\n", argv[0]);
        return 1;
    }

    fd = socket(AF_NETLINK, SOCK_RAW, FWX_NETLINK_ID);
    if (fd < 0) { perror("socket"); return 1; }
    memset(&src, 0, sizeof(src));
    src.nl_family = AF_NETLINK;
    src.nl_pid = 999;
    if (bind(fd, (struct sockaddr *)&src, sizeof(src)) < 0)
        perror("bind");

    if (send_msg(fd, 2, NULL) < 0) perror("clean");

    fp = fopen(argv[1], "r");
    if (!fp) { perror("fopen"); return 1; }
    while (fgets(line, sizeof(line), fp)) {
        size_t n = strlen(line);
        while (n && (line[n-1] == '\n' || line[n-1] == '\r'))
            line[--n] = 0;
        if (!n)
            continue;
        if (send_msg(fd, 1, line) < 0)
            perror("add");
        usleep(1000);
    }
    fclose(fp);

    if (send_msg(fd, 3, NULL) < 0) perror("done");
    printf("loaded\n");
    close(fd);
    return 0;
}
