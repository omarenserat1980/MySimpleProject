#include "family_simulator.hpp"

#include <cassert>
#include <iostream>

using brain::family::FamilySimulator;
using brain::family::Member;

int main() {
    FamilySimulator family;
    assert(family.add_member(Member{"parent-a", "Parent A", 45}));
    assert(family.add_member(Member{"parent-b", "Parent B", 44}));
    assert(family.add_member(Member{"adult-child", "Adult Child", 22, {"parent-a", "parent-b"}}));
    assert(family.add_member(Member{"friend", "Adult Friend", 23}));
    assert(family.add_member(Member{"minor", "Minor", 16}));

    std::string error;
    assert(!family.add_friendship("adult-child", "minor", true, true, &error));
    assert(error == "ADULT_MEMBERS_ONLY");
    assert(!family.add_friendship("adult-child", "friend", true, false, &error));
    assert(error == "MUTUAL_FRIENDSHIP_CONSENT_REQUIRED");

    const auto suggestions = family.suggest_adult_friends("adult-child");
    assert(suggestions.size() == 1);
    assert(suggestions.front().candidate_id == "friend");

    assert(!family.simulate_marriage("adult-child", "friend", true, true, &error));
    assert(error == "FRIENDSHIP_REQUIRED_BEFORE_MARRIAGE");
    assert(family.add_friendship("adult-child", "friend", true, true, &error));
    assert(family.simulate_marriage("adult-child", "friend", true, true, &error));

    assert(!family.simulate_grandchildren("adult-child", "friend", 1, true, false, &error));
    assert(error == "MUTUAL_CHILD_SIMULATION_CONSENT_REQUIRED");
    const auto grandchildren = family.simulate_grandchildren("adult-child", "friend", 2, true, true, &error);
    assert(grandchildren.size() == 2);
    assert(family.size() == 7);

    assert(!family.simulate_marriage("parent-a", "adult-child", true, true, &error));
    assert(error == "MEMBER_ALREADY_MARRIED" || error == "CLOSE_FAMILY_RELATIONSHIP_BLOCKED");

    std::cout << "family simulator checks passed; descendants=" << grandchildren.size() << '\n';
    return 0;
}
