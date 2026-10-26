#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <net/if.h>
#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <arpa/inet.h>
#define MAGIC 0x52544331u
#define CHUNK 1200
struct hdr { uint32_t magic; uint32_t seq; uint16_t len; uint16_t flags; uint32_t rsv; };
static int mac_pton(const char*s,unsigned char*m){return sscanf(s,"%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",&m[0],&m[1],&m[2],&m[3],&m[4],&m[5])==6;}
static void send_chunk(int fd, struct sockaddr_ll *sll, unsigned char *src, unsigned char *dst, uint32_t seq, unsigned char *data, int n){
  unsigned char frame[1600]; memset(frame,0,sizeof(frame)); memcpy(frame,dst,6); memcpy(frame+6,src,6); frame[12]=0x88; frame[13]=0xB5;
  struct hdr*h=(struct hdr*)(frame+14); h->magic=htonl(MAGIC); h->seq=htonl(seq); h->len=htons(n); h->flags=0; h->rsv=0;
  memcpy(frame+14+sizeof(struct hdr),data,n); size_t flen=14+sizeof(struct hdr)+n; if(flen<60)flen=60;
  sendto(fd,frame,flen,0,(struct sockaddr*)sll,sizeof(*sll));
}
int main(int argc,char**argv){
 if(argc<4){fprintf(stderr,"usage: %s iface dst_mac file\n",argv[0]);return 1;}
 unsigned char dst[6]; if(!mac_pton(argv[2],dst)){fprintf(stderr,"bad mac\n");return 1;}
 FILE*f=fopen(argv[3],"rb"); if(!f){perror("fopen");return 1;}
 unsigned char **chunks=NULL; int *lens=NULL; int nchunks=0, cap=256;
 chunks=malloc(sizeof(void*)*cap); lens=malloc(sizeof(int)*cap);
 unsigned char buf[CHUNK]; int n;
 while((n=fread(buf,1,CHUNK,f))>0){
   if(nchunks==cap){cap*=2; chunks=realloc(chunks,sizeof(void*)*cap); lens=realloc(lens,sizeof(int)*cap);}
   chunks[nchunks]=malloc(n); memcpy(chunks[nchunks],buf,n); lens[nchunks]=n; nchunks++;
 }
 fclose(f); if(nchunks==0){fprintf(stderr,"empty\n");return 1;}
 int fd=socket(AF_PACKET,SOCK_RAW,htons(ETH_P_ALL)); if(fd<0){perror("socket");return 1;}
 struct ifreq ifr; memset(&ifr,0,sizeof(ifr)); strncpy(ifr.ifr_name,argv[1],IFNAMSIZ-1);
 ioctl(fd,SIOCGIFINDEX,&ifr); int ifindex=ifr.ifr_ifindex; ioctl(fd,SIOCGIFHWADDR,&ifr); unsigned char src[6]; memcpy(src,ifr.ifr_hwaddr.sa_data,6);
 struct sockaddr_ll sll; memset(&sll,0,sizeof(sll)); sll.sll_family=AF_PACKET; sll.sll_ifindex=ifindex; sll.sll_halen=6; memcpy(sll.sll_addr,dst,6);
 for(int i=0;i<nchunks;i++){ send_chunk(fd,&sll,src,dst,i,chunks[i],lens[i]); usleep(1000); }
 printf("sent %d chunks, waiting NACK 3s\n",nchunks); fflush(stdout);
 long deadline=3000; struct timeval tv; tv.tv_sec=0; tv.tv_usec=100000; int resent=0;
 for(int loops=0; loops<30; loops++){
   fd_set fs; FD_ZERO(&fs); FD_SET(fd,&fs);
   int r=select(fd+1,&fs,NULL,NULL,&tv);
   if(r>0){
     unsigned char rb[2048]; ssize_t len=recv(fd,rb,sizeof(rb),0);
     if(len>14 && rb[12]==0x88 && rb[13]==0xB5){
       char *p=(char*)(rb+14); int seq=-1;
       if(sscanf(p,"NACK:%d",&seq)==1 && seq>=0 && seq<nchunks){
         printf("NACK %d -> resend\n",seq); fflush(stdout);
         send_chunk(fd,&sll,src,dst,seq,chunks[seq],lens[seq]); resent++;
       }
     }
   }
   usleep(100000);
 }
 printf("done resent=%d\n",resent); close(fd); return 0;
}
