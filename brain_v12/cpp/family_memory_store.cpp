#include "family_memory_store.hpp"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <system_error>
#include <utility>

namespace brain::family {

FamilyMemoryStore::FamilyMemoryStore(std::string path) : path_(std::move(path)) {}

void FamilyMemoryStore::set_error(std::string* error, const std::string& value) {
    if (error) *error = value;
}

bool FamilyMemoryStore::restore(std::string* error) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::error_code filesystem_error;
    const bool file_exists = std::filesystem::exists(path_, filesystem_error);
    if (filesystem_error) {
        set_error(error, "MEMORY_FILE_STATUS_FAILED");
        return false;
    }
    if (!file_exists) {
        entries_.clear();
        known_ids_.clear();
        return true;
    }

    std::ifstream input(path_);
    if (!input) {
        set_error(error, "MEMORY_FILE_NOT_READABLE");
        return false;
    }

    std::vector<ChildMemory> restored;
    std::unordered_map<std::string, bool> restored_ids;
    std::string line;
    std::size_t line_number = 0;
    while (std::getline(input, line)) {
        ++line_number;
        if (line.empty()) continue;
        std::istringstream row(line);
        ChildMemory entry;
        if (!(row >> std::quoted(entry.child_id) >> std::quoted(entry.name)
                  >> std::quoted(entry.parent_a) >> std::quoted(entry.parent_b)
                  >> entry.birth_cycle)) {
            set_error(error, "MEMORY_RECORD_INVALID_AT_LINE_" + std::to_string(line_number));
            return false;
        }
        if (entry.child_id.empty() || entry.parent_a.empty() || entry.parent_b.empty()) {
            set_error(error, "MEMORY_RECORD_MISSING_REQUIRED_FIELD");
            return false;
        }
        if (restored_ids.count(entry.child_id)) {
            set_error(error, "DUPLICATE_CHILD_MEMORY_ID");
            return false;
        }
        restored_ids.emplace(entry.child_id, true);
        restored.push_back(std::move(entry));
    }
    if (input.bad()) {
        set_error(error, "MEMORY_FILE_READ_FAILED");
        return false;
    }
    entries_ = std::move(restored);
    known_ids_ = std::move(restored_ids);
    return true;
}

bool FamilyMemoryStore::remember(const ChildMemory& memory, std::string* error) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (memory.child_id.empty() || memory.name.empty() ||
        memory.parent_a.empty() || memory.parent_b.empty()) {
        set_error(error, "CHILD_MEMORY_REQUIRED_FIELDS_MISSING");
        return false;
    }
    if (memory.parent_a == memory.parent_b) {
        set_error(error, "CHILD_PARENTS_MUST_BE_DISTINCT");
        return false;
    }
    if (known_ids_.count(memory.child_id)) {
        set_error(error, "CHILD_MEMORY_ALREADY_EXISTS");
        return false;
    }

    std::ofstream output(path_, std::ios::out | std::ios::app);
    if (!output) {
        set_error(error, "MEMORY_FILE_NOT_WRITABLE");
        return false;
    }
    output << std::quoted(memory.child_id) << ' '
           << std::quoted(memory.name) << ' '
           << std::quoted(memory.parent_a) << ' '
           << std::quoted(memory.parent_b) << ' '
           << memory.birth_cycle << '\n';
    output.flush();
    if (!output) {
        set_error(error, "MEMORY_FILE_WRITE_FAILED");
        return false;
    }
    entries_.push_back(memory);
    known_ids_.emplace(memory.child_id, true);
    return true;
}

std::vector<ChildMemory> FamilyMemoryStore::children() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return entries_;
}

std::size_t FamilyMemoryStore::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return entries_.size();
}

}  // namespace brain::family
