#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <zlib.h>

struct RGBA { uint8_t r,g,b,a; };
struct Image {
    int w,h; std::vector<uint8_t> p;
    Image(int W,int H,RGBA c):w(W),h(H),p(static_cast<size_t>(W)*H*4){
        for(size_t i=0;i<p.size();i+=4){p[i]=c.r;p[i+1]=c.g;p[i+2]=c.b;p[i+3]=c.a;}
    }
    void pixel(int x,int y,RGBA c){
        if(x<0||y<0||x>=w||y>=h)return;
        size_t i=(static_cast<size_t>(y)*w+x)*4;
        p[i]=c.r;p[i+1]=c.g;p[i+2]=c.b;p[i+3]=c.a;
    }
    void rect(int x0,int y0,int x1,int y1,RGBA c){
        if(x0>x1)std::swap(x0,x1); if(y0>y1)std::swap(y0,y1);
        x0=std::max(0,x0);y0=std::max(0,y0);x1=std::min(w-1,x1);y1=std::min(h-1,y1);
        for(int y=y0;y<=y1;y++) for(int x=x0;x<=x1;x++) pixel(x,y,c);
    }
    void circle(int cx,int cy,int r,RGBA c){
        int r2=r*r;
        for(int y=cy-r;y<=cy+r;y++) for(int x=cx-r;x<=cx+r;x++){
            int dx=x-cx,dy=y-cy;if(dx*dx+dy*dy<=r2)pixel(x,y,c);
        }
    }
    void line(int x0,int y0,int x1,int y1,RGBA c){
        int dx=std::abs(x1-x0),sx=x0<x1?1:-1,dy=-std::abs(y1-y0),sy=y0<y1?1:-1,err=dx+dy;
        for(;;){pixel(x0,y0,c);if(x0==x1&&y0==y1)break;int e=2*err;if(e>=dy){err+=dy;x0+=sx;}if(e<=dx){err+=dx;y0+=sy;}}
    }
};

static uint32_t crc32_png(const std::vector<uint8_t>& v){
    return static_cast<uint32_t>(crc32(0,v.data(),static_cast<uInt>(v.size())));
}
static void be32(std::vector<uint8_t>& o,uint32_t x){
    o.push_back(x>>24);o.push_back(x>>16);o.push_back(x>>8);o.push_back(x);
}
static void chunk(std::vector<uint8_t>& out,const char* type,const std::vector<uint8_t>& data){
    be32(out,static_cast<uint32_t>(data.size()));
    std::vector<uint8_t> crc(4+data.size());
    for(int i=0;i<4;i++)crc[i]=static_cast<uint8_t>(type[i]);
    std::copy(data.begin(),data.end(),crc.begin()+4);
    out.insert(out.end(),type,type+4);out.insert(out.end(),data.begin(),data.end());
    be32(out,crc32_png(crc));
}
static bool write_png(const std::string& path,const Image& im){
    std::vector<uint8_t> raw;raw.reserve(static_cast<size_t>(im.h)*(im.w*4+1));
    for(int y=0;y<im.h;y++){raw.push_back(0);raw.insert(raw.end(),im.p.begin()+static_cast<size_t>(y)*im.w*4,im.p.begin()+static_cast<size_t>(y+1)*im.w*4);}
    uLongf n=compressBound(raw.size());std::vector<uint8_t> z(n);
    if(compress2(z.data(),&n,raw.data(),raw.size(),9)!=Z_OK)return false;z.resize(n);
    std::vector<uint8_t> png={137,80,78,71,13,10,26,10};
    std::vector<uint8_t> ihdr;be32(ihdr,im.w);be32(ihdr,im.h);ihdr.insert(ihdr.end(),{8,6,0,0,0});
    chunk(png,"IHDR",ihdr);chunk(png,"IDAT",z);chunk(png,"IEND",{});
    std::ofstream f(path,std::ios::binary);f.write(reinterpret_cast<char*>(png.data()),png.size());return f.good();
}

int main(int argc,char**argv){
    const std::string out=argc>1?argv[1]:"brain-raster.png";
    Image im(1000,650,{14,27,43,255});
    im.rect(0,0,999,470,{72,130,176,255});
    im.rect(0,470,999,649,{50,90,70,255});
    im.circle(810,115,65,{255,216,77,255});
    im.circle(160,410,75,{38,91,50,255});
    im.rect(145,410,175,570,{107,66,38,255});
    im.line(0,520,999,520,{90,160,190,255});
    im.line(0,540,999,540,{70,140,180,255});
    if(!write_png(out,im)){std::cerr<<"PNG_WRITE_FAILED\n";return 2;}
    std::cout<<"BRAIN_CPP_RASTER_VERIFIED "<<out<<" 1000x650\n";
    return 0;
}
