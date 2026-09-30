#include "bytecode.hpp"
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <vector>
#include <zlib.h>

struct Image {
    int w=1000,h=650; std::vector<uint8_t> p;
    Image():p(static_cast<size_t>(w)*h*4,0){ for(size_t i=0;i<p.size();i+=4)p[i+3]=255; }
    void px(int x,int y,uint32_t c){
        if(x<0||y<0||x>=w||y>=h)return;
        size_t i=(static_cast<size_t>(y)*w+x)*4;
        p[i]=c>>24;p[i+1]=c>>16;p[i+2]=c>>8;p[i+3]=c;
    }
    void rect(int x0,int y0,int x1,int y1,uint32_t c){
        if(x0>x1)std::swap(x0,x1); if(y0>y1)std::swap(y0,y1);
        for(int y=std::max(0,y0);y<=std::min(h-1,y1);++y)
            for(int x=std::max(0,x0);x<=std::min(w-1,x1);++x) px(x,y,c);
    }
    void circle(int cx,int cy,int r,uint32_t c){
        int rr=r*r;
        for(int y=cy-r;y<=cy+r;++y) for(int x=cx-r;x<=cx+r;++x)
            {int dx=x-cx,dy=y-cy;if(dx*dx+dy*dy<=rr)px(x,y,c);}
    }
    void line(int x0,int y0,int x1,int y1,uint32_t c){
        int dx=std::abs(x1-x0),sx=x0<x1?1:-1,dy=-std::abs(y1-y0),sy=y0<y1?1:-1,err=dx+dy;
        for(;;){px(x0,y0,c);if(x0==x1&&y0==y1)break;int e=2*err;if(e>=dy){err+=dy;x0+=sx;}if(e<=dx){err+=dx;y0+=sy;}}
    }
};
static void be32(std::vector<uint8_t>&o,uint32_t x){o.push_back(x>>24);o.push_back(x>>16);o.push_back(x>>8);o.push_back(x);}
static void chunk(std::vector<uint8_t>&o,const char*t,const std::vector<uint8_t>&d){
    be32(o,d.size());std::vector<uint8_t> c(4+d.size());for(int i=0;i<4;++i)c[i]=t[i];
    std::copy(d.begin(),d.end(),c.begin()+4);o.insert(o.end(),t,t+4);o.insert(o.end(),d.begin(),d.end());be32(o,crc32(0,c.data(),c.size()));
}
static bool png(const char*path,const Image&i){
    std::vector<uint8_t> raw;for(int y=0;y<i.h;++y){raw.push_back(0);raw.insert(raw.end(),i.p.begin()+static_cast<size_t>(y)*i.w*4,i.p.begin()+static_cast<size_t>(y+1)*i.w*4);}
    uLongf n=compressBound(raw.size());std::vector<uint8_t> z(n);if(compress2(z.data(),&n,raw.data(),raw.size(),9)!=Z_OK)return false;z.resize(n);
    std::vector<uint8_t> o={137,80,78,71,13,10,26,10};std::vector<uint8_t> h;be32(h,i.w);be32(h,i.h);h.insert(h.end(),{8,6,0,0,0});
    chunk(o,"IHDR",h);chunk(o,"IDAT",z);chunk(o,"IEND",{});std::ofstream f(path,std::ios::binary);f.write((char*)o.data(),o.size());return f.good();
}
int main(int argc,char**argv){
    if(argc<3)return 2;
    std::ifstream f(argv[1],std::ios::binary);if(!f)return 3;
    std::vector<uint8_t>b((std::istreambuf_iterator<char>(f)),{});
    auto cmds=brain::decode(b); Image im;
    for(const auto&c:cmds){
        switch(c.op){
            case brain::RECT: im.rect(c.a,c.b,c.c,c.d,c.rgba); break;
            case brain::LINE: im.line(c.a,c.b,c.c,c.d,c.rgba); break;
            case brain::CIRCLE: im.circle(c.a,c.b,c.c,c.rgba); break;
            default: break;
        }
    }
    if(!png(argv[2],im))return 4;
    std::cout<<"BRAIN_BRC_RENDER_VERIFIED commands="<<cmds.size()<<" output="<<argv[2]<<"\n";
    return 0;
}
