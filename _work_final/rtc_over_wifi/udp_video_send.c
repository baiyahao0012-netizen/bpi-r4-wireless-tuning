#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <time.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#define MAGIC 0x52544331u
struct hdr { uint32_t magic; uint32_t seq; uint16_t len; uint16_t flags; uint32_t rsv; };
static long now_ms(void){struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);return ts.tv_sec*1000+ts.tv_nsec/1000000;}
int main(int argc,char**argv){
 if(argc<5){fprintf(stderr,"usage: %s dst_ip port file fps\n",argv[0]);return 1;}
 const char*ip=argv[1]; int port=atoi(argv[2]); const char*path=argv[3]; int fps=atoi(argv[4]); if(fps<1)fps=30;
 FILE*f=fopen(path,"rb"); if(!f){perror("fopen");return 1;}
 fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET);
 unsigned char *buf=malloc(sz); if(fread(buf,1,sz,f)!=(size_t)sz){perror("read");return 1;} fclose(f);
 int fd=socket(AF_INET,SOCK_DGRAM,0); if(fd<0){perror("socket");return 1;}
 struct sockaddr_in d; memset(&d,0,sizeof(d)); d.sin_family=AF_INET; d.sin_port=htons(port); inet_pton(AF_INET,ip,&d.sin_addr);
 long *starts=malloc(sizeof(long)*(sz/4+16)); int ns=0,has=0;
 for(long i=0;i+3<sz;i++){
  if(buf[i]==0&&buf[i+1]==0&&((buf[i+2]==1)||(buf[i+2]==0&&buf[i+3]==1))){
   long p=(buf[i+2]==1)?i+3:i+4;
   if(p<sz){int t=buf[p]&0x1f; if(t==9){ if(ns==0) starts[ns++]=0; else starts[ns++]=i; has=1; i=p; }}
  }
 }
 if(!has){ ns=0; for(long i=0;i+3<sz;i++){if(buf[i]==0&&buf[i+1]==0&&((buf[i+2]==1)||(buf[i+2]==0&&buf[i+3]==1))){long p=(buf[i+2]==1)?i+3:i+4; if(p<sz){int t=buf[p]&0x1f; if(t==1||t==5){starts[ns++]=i; i=p;}}}}
 }
 if(ns==0){fprintf(stderr,"no frames\n");return 1;}
 int frames=ns; uint32_t seq=0; long t0=now_ms();
 for(int fi=0;fi<frames;fi++){
  long s=starts[fi],e=(fi+1<frames)?starts[fi+1]:sz; long off=s;
  while(off<e){
   int n=(int)((e-off)>1200?1200:(e-off));
   unsigned char pkt[1600]; struct hdr*h=(struct hdr*)pkt; h->magic=htonl(MAGIC); h->seq=htonl(seq++); h->len=htons(n); h->flags=0; h->rsv=htonl((uint32_t)(now_ms()-t0));
   memcpy(pkt+sizeof(struct hdr),buf+off,n);
   sendto(fd,pkt,sizeof(struct hdr)+n,0,(struct sockaddr*)&d,sizeof(d));
   off+=n;
  }
  struct timespec ts={0,1000000000L/fps}; nanosleep(&ts,NULL);
 }
 printf("udp sent %d frames %u chunks in %ld ms fps=%d\n",frames,seq,now_ms()-t0,fps);
 close(fd); return 0;
}
