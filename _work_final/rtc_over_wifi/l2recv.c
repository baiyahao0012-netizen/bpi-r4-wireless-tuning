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

#define ETH_P_RTC 0x88B5
int main(int argc,char**argv){
 if(argc<2){fprintf(stderr,"usage: %s iface [ack]\n",argv[0]);return 1;}
 const char*ifname=argv[1]; int ack=argc>2;
 int fd=socket(AF_PACKET,SOCK_RAW,htons(ETH_P_ALL)); if(fd<0){perror("socket");return 1;}
 struct ifreq ifr; memset(&ifr,0,sizeof(ifr)); strncpy(ifr.ifr_name,ifname,IFNAMSIZ-1);
 if(ioctl(fd,SIOCGIFINDEX,&ifr)<0){perror("ifindex");return 1;} int ifindex=ifr.ifr_ifindex;
 if(ioctl(fd,SIOCGIFHWADDR,&ifr)<0){perror("hwaddr");return 1;} unsigned char mymac[6]; memcpy(mymac,ifr.ifr_hwaddr.sa_data,6);
 struct sockaddr_ll sll; memset(&sll,0,sizeof(sll)); sll.sll_family=AF_PACKET; sll.sll_ifindex=ifindex; sll.sll_protocol=htons(ETH_P_ALL);
 if(bind(fd,(struct sockaddr*)&sll,sizeof(sll))<0){perror("bind");return 1;}
 printf("listening iface=%s ack=%d\n",ifname,ack); fflush(stdout);
 unsigned char buf[2048]; int n=0;
 while(n<20){
   ssize_t len=recv(fd,buf,sizeof(buf),0); if(len<14)continue;
   unsigned short et=ntohs(*(unsigned short*)(buf+12)); if(et!=ETH_P_RTC)continue;
   unsigned char *src=buf+6; unsigned char *dst=buf;
   printf("rx src=%02x:%02x:%02x:%02x:%02x:%02x len=%zd payload=%s\n",src[0],src[1],src[2],src[3],src[4],src[5],len-14,buf+14); fflush(stdout);
   if(ack){
     unsigned char out[64]; memset(out,0,sizeof(out));
     memcpy(out,src,6); memcpy(out+6,mymac,6); out[12]=0x88;out[13]=0xB5;
     const char*msg="ACK_FROM_AP"; memcpy(out+14,msg,strlen(msg));
     struct sockaddr_ll d; memset(&d,0,sizeof(d)); d.sll_family=AF_PACKET; d.sll_ifindex=ifindex; d.sll_halen=6; memcpy(d.sll_addr,src,6);
     sendto(fd,out,14+strlen(msg),0,(struct sockaddr*)&d,sizeof(d));
   }
   n++;
 }
 close(fd); return 0;
}
