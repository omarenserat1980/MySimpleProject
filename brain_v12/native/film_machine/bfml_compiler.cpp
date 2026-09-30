#include "../brain_raster_cpp/bytecode.hpp"
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <cstdint>
#include <stdexcept>

static uint32_t color(const std::string& s){
    std::string x=s; if(!x.empty()&&x[0]=='#')x.erase(0,1);
    if(x.size()!=8) throw std::runtime_error("BAD_COLOR");
    return static_cast<uint32_t>(std::stoul(x,nullptr,16));
}
static std::vector<std::string> tok(const std::string& s){
    std::istringstream in(s); std::vector<std::string> v; std::string x;
    while(in>>x)v.push_back(x); return v;
}
int main(int argc,char**argv){
    if(argc<3)return 2;
    std::ifstream in(argv[1]); if(!in)return 3;
    std::ofstream out(argv[2],std::ios::binary); if(!out)return 4;
    std::vector<brain::Cmd> cmds; std::string line;
    while(std::getline(in,line)){
        auto t=tok(line); if(t.empty()||t[0][0]=='#')continue;
        if(t[0]=="RECT"&&t.size()==6) cmds.push_back({brain::RECT,std::stoi(t[1]),std::stoi(t[2]),std::stoi(t[3]),std::stoi(t[4]),0,color(t[5])});
        else if(t[0]=="LINE"&&t.size()==6) cmds.push_back({brain::LINE,std::stoi(t[1]),std::stoi(t[2]),std::stoi(t[3]),std::stoi(t[4]),1,color(t[5])});
        else if(t[0]=="CIRCLE"&&t.size()==5) cmds.push_back({brain::CIRCLE,std::stoi(t[1]),std::stoi(t[2]),std::stoi(t[3]),0,0,color(t[4])});
    }
    auto b=brain::encode(cmds); out.write(reinterpret_cast<const char*>(b.data()),b.size());
    return out.good()?0:5;
}
