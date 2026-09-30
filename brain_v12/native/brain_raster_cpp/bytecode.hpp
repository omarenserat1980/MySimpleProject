#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace brain {
enum Op : uint8_t { RECT=1, LINE=2, CIRCLE=3, END=255 };
struct Cmd { Op op; int32_t a,b,c,d,e; uint32_t rgba; };
std::vector<uint8_t> encode(const std::vector<Cmd>& cmds);
std::vector<Cmd> decode(const std::vector<uint8_t>& bytes);
}
