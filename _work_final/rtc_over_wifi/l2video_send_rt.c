#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <net/if.h>
#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <arpa/inet.h>

#define MAGIC 0x52544331u
struct hdr { uint32_t magic; uint32_t seq; uint16_t len; uint16_t flags; uint32_t rsv; };

static int mac_pton(const char *s, unsigned char *m){return sscanf(s,"%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",&m[0],&m[1],&m[2],&m[3],&m[4],&m[5])==6;}
static long now_ms(void){struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);return ts.tv_sec*1000+ts.tv_nsec/1000000;}

int main(int argc,char**argv){
 if(argc<4){fprintf(stderr,"usage: %s iface dst_mac file [fps]\n",argv[0]);return 1;}
 const char*ifname=argv[1]; unsigned char dst[6]; if(!mac_pton(argv[2],dst)){fprintf(stderr,"bad mac\n");return 1;}
 const char*path=argv[3]; int fps=argc>4?atoi(argv[4]):30; if(fps<1||fps>120)fps=30;
 FILE*f=fopen(path,"rb"); if(!f){perror("fopen");return 1;}
 fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET);
 unsigned char *buf=malloc(sz); if(!buf||fread(buf,1,sz,f)!=(size_t)sz){perror("read");return 1;} fclose(f);
 int fd=socket(AF_PACKET,SOCK_RAW,htons(ETH_P_ALL)); if(fd<0){perror("socket");return 1;}
 struct ifreq ifr; memset(&ifr,0,sizeof(ifr)); strncpy(ifr.ifr_name,ifname,IFNAMSIZ-1);
 if(ioctl(fd,SIOCGIFINDEX,&ifr)<0){perror("ifindex");return 1;} int ifindex=ifr.ifr_ifindex;
 if(ioctl(fd,SIOCGIFHWADDR,&ifr)<0){perror("hwaddr");return 1;} unsigned char src[6]; memcpy(src,ifr.ifr_hwaddr.sa_data,6);
 struct sockaddr_ll sll; memset(&sll,0,sizeof(sll)); sll.sll_family=AF_PACKET; sll.sll_ifindex=ifindex; sll.sll_halen=6; memcpy(sll.sll_addr,dst,6);

  /* collect AUD (type 9) starts; fallback VCL (1,5) */
  long *starts=malloc(sizeof(long)*(sz/4+16)); int ns=0; int has_aud=0;
  for(long i=0;i+3<sz;i++){
    if(buf[i]==0&&buf[i+1]==0&&((buf[i+2]==1)||(buf[i+2]==0&&buf[i+3]==1))){
      long p=(buf[i+2]==1)?i+3:i+4;
      if(p<sz){int t=buf[p]&0x1f; if(t==9){ if(ns==0) starts[ns++]=0; else starts[ns++]=i; has_aud=1; i=p; }}
    }
  }
  if(!has_aud){
    ns=0;
    for(long i=0;i+3<sz;i++){
      if(buf[i]==0&&buf[i+1]==0&&((buf[i+2]==1)||(buf[i+2]==0&&buf[i+3]==1))){
        long p=(buf[i+2]==1)?i+3:i+4;
        if(p<sz){int t=buf[p]&0x1f; if(t==1||t==5){starts[ns++]=i; i=p;}}
      }
    }
  }
  if(ns==0){fprintf(stderr,"no frame boundary\n");return 1;}
 int frames=ns; long t0=now_ms(); uint32_t seq=0;
 for(int fi=0;fi<frames;fi++){
   long s=starts[fi], e=(fi+1<frames)?starts[fi+1]:sz;
   long off=s;
   while(off<e){
     int n=(int)((e-off)>1200?1200:(e-off));
     unsigned char frame[1600]; memset(frame,0,sizeof(frame));
     memcpy(frame,dst,6); memcpy(frame+6,src,6); frame[12]=0x88;frame[13]=0xB5;
     struct hdr*h=(struct hdr*)(frame+14); h->magic=htonl(MAGIC); h->seq=htonl(seq++); h->len=htons(n); h->flags=0; h->rsv=0;
     memcpy(frame+14+sizeof(struct hdr),buf+off,n);
     size_t flen=14+sizeof(struct hdr)+n; if(flen<60)flen=60;
     if(sendto(fd,frame,flen,0,(struct sockaddr*)&sll,sizeof(sll))<0)perror("sendto");
     off+=n;
   }
   struct timespec ts={0, 1000000000L/fps}; nanosleep(&ts,NULL);
 }
 printf("sent %d frames %u chunks in %ld ms fps=%d\n",frames,seq,now_ms()-t0,fps);
 free(starts); free(buf); close(fd); return 0;
}
