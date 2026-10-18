#include "family_memory_store.hpp"

#include <cassert>
#include <cstdio>
#include <string>

using brain::family::ChildMemory;
using brain::family::FamilyMemoryStore;

int main() {
    const std::string path = "/tmp/brain-family-memory-test.log";
    std::remove(path.c_str());

    std::string error;
    {
        FamilyMemoryStore first_start(path);
        assert(first_start.restore(&error));
        assert(first_start.size() == 0);
    }
    {
        FamilyMemoryStore store(path);
        assert(store.remember(ChildMemory{"child-1", "Virtual child", "parent-a", "parent-b", 1}, &error));
        assert(store.size() == 1);
        assert(!store.remember(ChildMemory{"child-1", "Duplicate", "parent-a", "parent-b", 2}, &error));
        assert(error == "CHILD_MEMORY_ALREADY_EXISTS");
    }

    {
        FamilyMemoryStore restored(path);
        assert(restored.restore(&error));
        assert(restored.size() == 1);
        const auto entries = restored.children();
        assert(entries.front().child_id == "child-1");
        assert(entries.front().name == "Virtual child");
        assert(entries.front().parent_a == "parent-a");
        assert(entries.front().parent_b == "parent-b");
        assert(entries.front().birth_cycle == 1);
        assert(!restored.remember(ChildMemory{"child-1", "Duplicate", "parent-a", "parent-b", 2}, &error));
    }

    std::remove(path.c_str());
    return 0;
}
