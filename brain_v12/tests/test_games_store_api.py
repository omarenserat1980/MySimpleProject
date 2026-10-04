from brain_v12.brain.games_store_api import GAMES

def test_three_brain_originals():
    assert set(GAMES) == {"neon-rift","last-light","drift-circuit"}
    assert all(g["price_usd"] > 0 for g in GAMES.values())
    assert all(g["delivery_path"].startswith("/games/") for g in GAMES.values())
