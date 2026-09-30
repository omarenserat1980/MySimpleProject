#include "bytecode.hpp"
#include <stdexcept>
namespace brain {
static void put(std::vector<uint8_t>& o,uint32_t x){for(int i=0;i<4;i++)o.push_back((x>>(i*8))&255);}
static uint32_t get(const std::vector<uint8_t>& b,size_t p){uint32_t x=0;for(int i=0;i<4;i++)x|=uint32_t(b[p+i])<<(i*8);return x;}
std::vector<uint8_t> encode(const std::vector<Cmd>& c){std::vector<uint8_t> o={'B','R','C','1'};put(o,c.size());for(auto&x:c){o.push_back(x.op);put(o,x.a);put(o,x.b);put(o,x.c);put(o,x.d);put(o,x.e);put(o,x.rgba);}return o;}
std::vector<Cmd> decode(const std::vector<uint8_t>& b){if(b.size()<8||std::string(b.begin(),b.begin()+4)!="BRC1")throw std::runtime_error("BAD_BRC");size_t p=8;uint32_t n=get(b,4);std::vector<Cmd> o;for(uint32_t i=0;i<n;i++){if(p+25>b.size())throw std::runtime_error("TRUNCATED_BRC");Cmd x; x.op=Op(b[p++]);x.a=get(b,p);p+=4;x.b=get(b,p);p+=4;x.c=get(b,p);p+=4;x.d=get(b,p);p+=4;x.e=get(b,p);p+=4;x.rgba=get(b,p);p+=4;o.push_back(x);}return o;}
}
