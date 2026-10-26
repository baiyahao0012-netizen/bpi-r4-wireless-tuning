#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <arpa/inet.h>
#define MAGIC 0x52544331u
#define K 8
#define CHUNK 1200
struct hdr { uint32_t magic; uint32_t seq; uint16_t len; uint16_t flags; uint32_t rsv; };
static int mac_pton(const char*s,unsigned char*m){return sscanf(s,"%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",&m[0],&m[1],&m[2],&m[3],&m[4],&m[5])==6;}
int main(int argc,char**argv){
 if(argc<4){fprintf(stderr,"usage: %s iface dst file\n",argv[0]);return 1;}
 unsigned char dst[6]; if(!mac_pton(argv[2],dst)){fprintf(stderr,"bad mac\n");return 1;}
 FILE*f=fopen(argv[3],"rb"); if(!f){perror("fopen");return 1;}
 int fd=socket(AF_PACKET,SOCK_RAW,htons(ETH_P_ALL)); if(fd<0){perror("socket");return 1;}
 struct ifreq ifr; memset(&ifr,0,sizeof(ifr)); strncpy(ifr.ifr_name,argv[1],IFNAMSIZ-1);
 ioctl(fd,SIOCGIFINDEX,&ifr); int ifindex=ifr.ifr_ifindex; ioctl(fd,SIOCGIFHWADDR,&ifr); unsigned char src[6]; memcpy(src,ifr.ifr_hwaddr.sa_data,6);
 struct sockaddr_ll sll; memset(&sll,0,sizeof(sll)); sll.sll_family=AF_PACKET; sll.sll_ifindex=ifindex; sll.sll_halen=6; memcpy(sll.sll_addr,dst,6);
 unsigned char bufs[K][CHUNK]; int lens[K]; uint32_t seq=0; int group=0;
 while(1){
   int n=0; for(int i=0;i<K;i++){ lens[i]=fread(bufs[i],1,CHUNK,f); if(lens[i]<=0){lens[i]=0;} else n++; }
   if(n==0)break;
   size_t maxlen=0; for(int i=0;i<K;i++) if((size_t)lens[i]>maxlen)maxlen=lens[i];
   unsigned char par[CHUNK]; memset(par,0,CHUNK);
   for(int i=0;i<K;i++) for(size_t j=0;j<(size_t)lens[i];j++) par[j]^=bufs[i][j];
   for(int i=0;i<K;i++){
     if(lens[i]<=0)continue;
     unsigned char frame[1600]; memset(frame,0,sizeof(frame)); memcpy(frame,dst,6);memcpy(frame+6,src,6);frame[12]=0x88;frame[13]=0xB5;
     struct hdr*h=(struct hdr*)(frame+14); h->magic=htonl(MAGIC); h->seq=htonl(seq); h->len=htons(lens[i]); h->flags=0; h->rsv=htonl(group);
     memcpy(frame+14+sizeof(struct hdr),bufs[i],lens[i]); size_t flen=14+sizeof(struct hdr)+lens[i]; if(flen<60)flen=60;
     sendto(fd,frame,flen,0,(struct sockaddr*)&sll,sizeof(sll)); seq++; usleep(1000);
   }
   unsigned char frame[1600]; memset(frame,0,sizeof(frame)); memcpy(frame,dst,6);memcpy(frame+6,src,6);frame[12]=0x88;frame[13]=0xB5;
   struct hdr*h=(struct hdr*)(frame+14); h->magic=htonl(MAGIC); h->seq=htonl(seq); h->len=htons((uint16_t)maxlen); h->flags=htons(1); h->rsv=htonl(group);
   memcpy(frame+14+sizeof(struct hdr),par,maxlen); size_t flen=14+sizeof(struct hdr)+maxlen; if(flen<60)flen=60;
   sendto(fd,frame,flen,0,(struct sockaddr*)&sll,sizeof(sll)); seq++; group++; usleep(1000);
   if(feof(f))break;
 }
 printf("fec sent groups=%d frames=%u\n",group,seq); fclose(f);close(fd);return 0;
}
