#pragma once

#include <cstddef>
#include <string>
#include <unordered_map>
#include <vector>

namespace brain::family {

struct Member {
    std::string id;
    std::string name;
    unsigned age = 0;
    std::vector<std::string> parents;
    std::string spouse;
    std::vector<std::string> friends;
    unsigned simulated_children = 0;
};

struct PartnerSuggestion {
    std::string member_id;
    std::string candidate_id;
    std::string reason;
};

class FamilySimulator {
public:
    static constexpr unsigned kAdultAge = 18;
    static constexpr unsigned kMaxChildrenPerRequest = 8;

    bool add_member(const Member& member, std::string* error = nullptr);
    bool add_friendship(const std::string& first, const std::string& second,
                        bool first_accepts, bool second_accepts,
                        std::string* error = nullptr);
    std::vector<PartnerSuggestion> suggest_adult_friends(const std::string& member_id) const;
    bool simulate_marriage(const std::string& first, const std::string& second,
                           bool first_consents, bool second_consents,
                           std::string* error = nullptr);
    std::vector<std::string> simulate_grandchildren(const std::string& first,
                           const std::string& second, unsigned count,
                           bool first_consents, bool second_consents,
                           std::string* error = nullptr);
    const Member* find(const std::string& id) const;
    std::size_t size() const noexcept { return members_.size(); }

private:
    std::unordered_map<std::string, Member> members_;

    bool related(const std::string& first, const std::string& second) const;
    void ancestors_of(const std::string& id, std::vector<std::string>& out) const;
    static void set_error(std::string* error, const std::string& value);
};

}  // namespace brain::family
