#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <net/if.h>
#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <arpa/inet.h>

#define ETH_P_RTC 0x88B5
#define MAGIC 0x52544331u
#define CHUNK 1200
struct hdr { uint32_t magic; uint32_t seq; uint16_t len; uint16_t flags; uint32_t rsv; };

static int mac_pton(const char *s, unsigned char *m){return sscanf(s,"%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",&m[0],&m[1],&m[2],&m[3],&m[4],&m[5])==6;}

int main(int argc,char**argv){
 if(argc<4){fprintf(stderr,"usage: %s iface dst_mac file [chunk]\n",argv[0]);return 1;}
 const char*ifname=argv[1]; unsigned char dst[6]; if(!mac_pton(argv[2],dst)){fprintf(stderr,"bad mac\n");return 1;}
 const char*path=argv[3]; int chunk=argc>4?atoi(argv[4]):CHUNK; if(chunk<64||chunk>1400)chunk=CHUNK;
 FILE*f=fopen(path,"rb"); if(!f){perror("fopen");return 1;}
 int fd=socket(AF_PACKET,SOCK_RAW,htons(ETH_P_ALL)); if(fd<0){perror("socket");return 1;}
 struct ifreq ifr; memset(&ifr,0,sizeof(ifr)); strncpy(ifr.ifr_name,ifname,IFNAMSIZ-1);
 if(ioctl(fd,SIOCGIFINDEX,&ifr)<0){perror("SIOCGIFINDEX");return 1;} int ifindex=ifr.ifr_ifindex;
 if(ioctl(fd,SIOCGIFHWADDR,&ifr)<0){perror("SIOCGIFHWADDR");return 1;} unsigned char src[6]; memcpy(src,ifr.ifr_hwaddr.sa_data,6);
 struct sockaddr_ll sll; memset(&sll,0,sizeof(sll)); sll.sll_family=AF_PACKET; sll.sll_ifindex=ifindex; sll.sll_halen=6; memcpy(sll.sll_addr,dst,6);
 unsigned char frame[1600]; unsigned char buf[CHUNK]; uint32_t seq=0; size_t n;
 while((n=fread(buf,1,chunk,f))>0){
   memset(frame,0,sizeof(frame)); memcpy(frame,dst,6); memcpy(frame+6,src,6); frame[12]=0x88;frame[13]=0xB5;
   struct hdr*h=(struct hdr*)(frame+14); h->magic=htonl(MAGIC); h->seq=htonl(seq); h->len=htons((uint16_t)n); h->flags=0; h->rsv=0;
   memcpy(frame+14+sizeof(struct hdr),buf,n);
   size_t flen=14+sizeof(struct hdr)+n; if(flen<60)flen=60;
   ssize_t s=sendto(fd,frame,flen,0,(struct sockaddr*)&sll,sizeof(sll));
   if(s<0)perror("sendto");
   seq++;
   usleep(1000);
 }
 printf("sent %u chunks, iface=%s\n",seq,ifname);
 fclose(f); close(fd); return 0;
}
