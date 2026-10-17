#include "family_simulator.hpp"

#include <algorithm>
#include <utility>

namespace brain::family {

void FamilySimulator::set_error(std::string* error, const std::string& value) {
    if (error) *error = value;
}

bool FamilySimulator::add_member(const Member& member, std::string* error) {
    if (member.id.empty() || member.name.empty()) {
        set_error(error, "MEMBER_ID_AND_NAME_REQUIRED");
        return false;
    }
    if (members_.count(member.id)) {
        set_error(error, "MEMBER_ID_ALREADY_EXISTS");
        return false;
    }
    for (const auto& parent : member.parents) {
        if (!members_.count(parent)) {
            set_error(error, "PARENT_NOT_FOUND");
            return false;
        }
    }
    members_.emplace(member.id, member);
    return true;
}

const Member* FamilySimulator::find(const std::string& id) const {
    const auto it = members_.find(id);
    return it == members_.end() ? nullptr : &it->second;
}

void FamilySimulator::ancestors_of(const std::string& id, std::vector<std::string>& out) const {
    const auto* member = find(id);
    if (!member) return;
    for (const auto& parent : member->parents) {
        if (std::find(out.begin(), out.end(), parent) == out.end()) {
            out.push_back(parent);
            ancestors_of(parent, out);
        }
    }
}

bool FamilySimulator::related(const std::string& first, const std::string& second) const {
    std::vector<std::string> first_ancestors;
    std::vector<std::string> second_ancestors;
    ancestors_of(first, first_ancestors);
    ancestors_of(second, second_ancestors);
    if (std::find(first_ancestors.begin(), first_ancestors.end(), second) != first_ancestors.end() ||
        std::find(second_ancestors.begin(), second_ancestors.end(), first) != second_ancestors.end()) {
        return true;
    }
    for (const auto& ancestor : first_ancestors) {
        if (std::find(second_ancestors.begin(), second_ancestors.end(), ancestor) != second_ancestors.end()) {
            return true;
        }
    }
    return false;
}

bool FamilySimulator::add_friendship(const std::string& first, const std::string& second,
                                     bool first_accepts, bool second_accepts,
                                     std::string* error) {
    auto a = members_.find(first);
    auto b = members_.find(second);
    if (a == members_.end() || b == members_.end()) {
        set_error(error, "MEMBER_NOT_FOUND");
        return false;
    }
    if (first == second) {
        set_error(error, "SELF_FRIENDSHIP_NOT_ALLOWED");
        return false;
    }
    if (!first_accepts || !second_accepts) {
        set_error(error, "MUTUAL_FRIENDSHIP_CONSENT_REQUIRED");
        return false;
    }
    if (a->second.age < kAdultAge || b->second.age < kAdultAge) {
        set_error(error, "ADULT_MEMBERS_ONLY");
        return false;
    }
    if (std::find(a->second.friends.begin(), a->second.friends.end(), second) == a->second.friends.end())
        a->second.friends.push_back(second);
    if (std::find(b->second.friends.begin(), b->second.friends.end(), first) == b->second.friends.end())
        b->second.friends.push_back(first);
    return true;
}

std::vector<PartnerSuggestion> FamilySimulator::suggest_adult_friends(const std::string& member_id) const {
    std::vector<PartnerSuggestion> suggestions;
    const auto* member = find(member_id);
    if (!member || member->age < kAdultAge || !member->spouse.empty()) return suggestions;

    for (const auto& [candidate_id, candidate] : members_) {
        if (candidate_id == member_id || candidate.age < kAdultAge || !candidate.spouse.empty()) continue;
        if (related(member_id, candidate_id)) continue;
        const bool already_friends =
            std::find(member->friends.begin(), member->friends.end(), candidate_id) != member->friends.end();
        if (!already_friends) {
            suggestions.push_back({member_id, candidate_id,
                "UNRELATED_ADULT_SINGLE_CANDIDATE; friendship requires mutual consent"});
        }
    }
    std::sort(suggestions.begin(), suggestions.end(),
        [](const PartnerSuggestion& a, const PartnerSuggestion& b) {
            return a.candidate_id < b.candidate_id;
        });
    return suggestions;
}

bool FamilySimulator::simulate_marriage(const std::string& first, const std::string& second,
                                        bool first_consents, bool second_consents,
                                        std::string* error) {
    auto a = members_.find(first);
    auto b = members_.find(second);
    if (a == members_.end() || b == members_.end()) {
        set_error(error, "MEMBER_NOT_FOUND");
        return false;
    }
    if (first == second) {
        set_error(error, "SELF_MARRIAGE_NOT_ALLOWED");
        return false;
    }
    if (!first_consents || !second_consents) {
        set_error(error, "MUTUAL_MARRIAGE_CONSENT_REQUIRED");
        return false;
    }
    if (a->second.age < kAdultAge || b->second.age < kAdultAge) {
        set_error(error, "ADULT_MEMBERS_ONLY");
        return false;
    }
    if (!a->second.spouse.empty() || !b->second.spouse.empty()) {
        set_error(error, "MEMBER_ALREADY_MARRIED");
        return false;
    }
    if (related(first, second)) {
        set_error(error, "CLOSE_FAMILY_RELATIONSHIP_BLOCKED");
        return false;
    }
    const bool mutual_friends =
        std::find(a->second.friends.begin(), a->second.friends.end(), second) != a->second.friends.end() &&
        std::find(b->second.friends.begin(), b->second.friends.end(), first) != b->second.friends.end();
    if (!mutual_friends) {
        set_error(error, "FRIENDSHIP_REQUIRED_BEFORE_MARRIAGE");
        return false;
    }
    a->second.spouse = second;
    b->second.spouse = first;
    return true;
}

std::vector<std::string> FamilySimulator::simulate_grandchildren(
    const std::string& first, const std::string& second, unsigned count,
    bool first_consents, bool second_consents, std::string* error) {
    std::vector<std::string> created;
    auto a = members_.find(first);
    auto b = members_.find(second);
    if (a == members_.end() || b == members_.end()) {
        set_error(error, "MEMBER_NOT_FOUND");
        return created;
    }
    if (!first_consents || !second_consents) {
        set_error(error, "MUTUAL_CHILD_SIMULATION_CONSENT_REQUIRED");
        return created;
    }
    if (a->second.spouse != second || b->second.spouse != first) {
        set_error(error, "MARRIED_PAIR_REQUIRED");
        return created;
    }
    if (count > kMaxChildrenPerRequest) {
        set_error(error, "CHILD_COUNT_LIMIT_EXCEEDED");
        return created;
    }
    for (unsigned i = 0; i < count; ++i) {
        const std::string id = "sim-child-" + std::to_string(members_.size() + 1);
        Member child;
        child.id = id;
        child.name = "Simulated descendant " + std::to_string(members_.size() + 1);
        child.age = 0;
        child.parents = {first, second};
        members_.emplace(id, child);
        created.push_back(id);
        ++members_.at(first).simulated_children;
        ++members_.at(second).simulated_children;
    }
    return created;
}

}  // namespace brain::family
