#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <time.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <arpa/inet.h>
#define ETH_P_RTC 0x88B5
static int mac_pton(const char*s,unsigned char*m){return sscanf(s,"%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",&m[0],&m[1],&m[2],&m[3],&m[4],&m[5])==6;}
int main(int argc,char**argv){
 if(argc<4){fprintf(stderr,"usage: %s iface dst_mac count\n",argv[0]);return 1;}
 unsigned char dst[6]; if(!mac_pton(argv[2],dst)){fprintf(stderr,"bad mac\n");return 1;}
 int count=atoi(argv[3]); if(count<=0)count=1000;
 int fd=socket(AF_PACKET,SOCK_RAW,htons(ETH_P_ALL)); if(fd<0){perror("socket");return 1;}
 struct ifreq ifr; memset(&ifr,0,sizeof(ifr)); strncpy(ifr.ifr_name,argv[1],IFNAMSIZ-1);
 ioctl(fd,SIOCGIFINDEX,&ifr); int ifindex=ifr.ifr_ifindex; ioctl(fd,SIOCGIFHWADDR,&ifr); unsigned char src[6]; memcpy(src,ifr.ifr_hwaddr.sa_data,6);
 struct sockaddr_ll sll; memset(&sll,0,sizeof(sll)); sll.sll_family=AF_PACKET; sll.sll_ifindex=ifindex; sll.sll_halen=6; memcpy(sll.sll_addr,dst,6);
 unsigned char frame[1400]; memset(frame,0,sizeof(frame)); memcpy(frame,dst,6);memcpy(frame+6,src,6);frame[12]=0x88;frame[13]=0xB5;
 struct timespec t0; clock_gettime(CLOCK_MONOTONIC,&t0);
 for(int i=0;i<count;i++){
   int is_i = (i%2==0);
   int prio = is_i ? 6 : 0; /* 6=VO, 0=BE */
   setsockopt(fd,SOL_SOCKET,SO_PRIORITY,&prio,sizeof(prio));
   struct timespec now; clock_gettime(CLOCK_MONOTONIC,&now);
   uint32_t ts=(uint32_t)((now.tv_sec-t0.tv_sec)*1000+(now.tv_nsec-t0.tv_nsec)/1000000);
   uint32_t seq=(uint32_t)i;
   memcpy(frame+14,&seq,4); memcpy(frame+18,&ts,4); frame[22]=is_i?'I':'P';
   ssize_t n=sendto(fd,frame,60,0,(struct sockaddr*)&sll,sizeof(sll));
   if(n<0)perror("sendto");
   usleep(2000);
 }
 printf("sem sent count=%d I_prio=6 P_prio=0\n",count);
 close(fd); return 0;
}
