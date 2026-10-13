#pragma once

#include <cstdint>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace brain::family {

struct ChildMemory {
    std::string child_id;
    std::string name;
    std::string parent_a;
    std::string parent_b;
    std::uint64_t birth_cycle = 0;
};

// File-backed memory ledger for virtual descendants. The caller chooses a durable
// writable path appropriate to its runtime; this class never assumes cloud storage.
class FamilyMemoryStore {
public:
    explicit FamilyMemoryStore(std::string path);

    bool restore(std::string* error = nullptr);
    bool remember(const ChildMemory& memory, std::string* error = nullptr);
    std::vector<ChildMemory> children() const;
    std::size_t size() const;

private:
    static void set_error(std::string* error, const std::string& value);

    std::string path_;
    mutable std::mutex mutex_;
    std::vector<ChildMemory> entries_;
    std::unordered_map<std::string, bool> known_ids_;
};

}  // namespace brain::family
