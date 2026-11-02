#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>
#include <net/if.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static volatile int running = 1;
static double finish;
static uint8_t srcmac[6];
static int ifindex;
static uint64_t now_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ULL + t.tv_nsec;
}
static void mac(const char *s, uint8_t *out) {
    unsigned x[6];
    if (sscanf(s, "%x:%x:%x:%x:%x:%x", x, x+1, x+2, x+3, x+4, x+5) != 6)
        exit(2);
    for (int i=0; i<6; i++) out[i]=x[i];
}
struct flow {
    const char *ip, *mac;
    int port, priority, size;
    double mbps;
    unsigned long sent, errors;
};
static void *sender(void *arg) {
    struct flow *f=arg;
    int s=socket(AF_PACKET, SOCK_RAW | SOCK_NONBLOCK, htons(ETH_P_IP));
    if (s < 0 || setsockopt(s,SOL_SOCKET,SO_PRIORITY,&f->priority,sizeof(int))) {
        perror("raw socket/priority"); exit(3);
    }
    uint8_t frame[1514]={0}, dm[6];
    mac(f->mac,dm);
    memcpy(frame,dm,6); memcpy(frame+6,srcmac,6);
    frame[12]=8;
    uint8_t *ip=frame+14, *udp=ip+20, *p=udp+8;
    int len=20+8+f->size;
    ip[0]=0x45; ip[1]=(f->priority==262)?0xb8:0;
    ip[2]=len>>8; ip[3]=len; ip[8]=64; ip[9]=17;
    inet_pton(AF_INET,"192.168.240.1",ip+12);
    inet_pton(AF_INET,f->ip,ip+16);
    unsigned sum=0;
    for(int i=0;i<20;i+=2) sum+=(ip[i]<<8)|ip[i+1];
    while(sum>>16)sum=(sum&65535)+(sum>>16);
    sum=~sum; ip[10]=sum>>8; ip[11]=sum;
    udp[0]=6203>>8; udp[1]=6203&255;
    udp[2]=f->port>>8; udp[3]=f->port;
    udp[4]=(f->size+8)>>8; udp[5]=f->size+8;
    memcpy(p,"EDP1",4);
    struct sockaddr_ll dst={.sll_family=AF_PACKET,.sll_ifindex=ifindex,
        .sll_halen=6,.sll_protocol=htons(ETH_P_IP)};
    memcpy(dst.sll_addr,dm,6);
    double interval=f->mbps>0 ? f->size*8000.0/f->mbps : 10000000.0;
    double next=now_ns();
    while(running && now_ns()/1e9 < finish) {
        uint64_t t=now_ns();
        if(t < next) {
            double wait=next-t;
            struct timespec ts={0,(long)(wait>1000000?1000000:wait)};
            nanosleep(&ts,NULL); continue;
        }
        uint64_t seq=f->sent;
        memcpy(p+4,&seq,8); memcpy(p+12,&t,8);
        if(sendto(s,frame,len+14,0,(void*)&dst,sizeof(dst))>=0)f->sent++;
        else f->errors++;
        /* Never catch up late sends with a growing, unbounded burst. */
        next+=interval;
        if(next<t-2000000)next=t;
    }
    close(s); return NULL;
}
int main(int argc,char **argv) {
    if(argc!=9) {
        fprintf(stderr,"usage: iface probe_ip probe_mac bg_ip bg_mac seconds mbps_each priority\n");
        return 2;
    }
    int s=socket(AF_INET,SOCK_DGRAM,0);
    struct ifreq req={0};
    snprintf(req.ifr_name,IFNAMSIZ,"%s",argv[1]);
    if(ioctl(s,SIOCGIFINDEX,&req))return 3;
    ifindex=req.ifr_ifindex;
    if(ioctl(s,SIOCGIFHWADDR,&req))return 3;
    memcpy(srcmac,req.ifr_hwaddr.sa_data,6);
    struct sockaddr_in local={.sin_family=AF_INET,.sin_port=htons(6203)};
    if(bind(s,(void*)&local,sizeof(local))){perror("bind");return 3;}
    struct timeval timeout={0,100000};
    setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
    double start=now_ns()/1e9;
    finish=start+atof(argv[6]);
    double rate=atof(argv[7]);
    struct flow f[3]={
        {argv[2],argv[3],6201,atoi(argv[8]),128,0,0,0},
        {argv[2],argv[3],6202,256,1400,rate,0,0},
        {argv[4],argv[5],6204,256,1400,rate,0,0}};
    pthread_t threads[3];
    int n=rate>0?3:1;
    for(int i=0;i<n;i++)pthread_create(threads+i,NULL,sender,f+i);
    printf("elapsed_s,seq,rtt_ms\n");
    while(now_ns()/1e9<finish+1) {
        uint8_t buf[1500];
        ssize_t count=recv(s,buf,sizeof(buf),0);
        if(count<20 || memcmp(buf,"EDP1",4))continue;
        uint64_t seq,t; memcpy(&seq,buf+4,8);memcpy(&t,buf+12,8);
        uint64_t current=now_ns();
        printf("%.6f,%llu,%.6f\n",current/1e9-start,
            (unsigned long long)seq,(current-t)/1e6);
    }
    running=0;
    for(int i=0;i<n;i++)pthread_join(threads[i],NULL);
    for(int i=0;i<n;i++)
        fprintf(stderr,"flow=%d priority=%d sent=%lu errors=%lu\n",
            i,f[i].priority,f[i].sent,f[i].errors);
    close(s);
    return 0;
}
