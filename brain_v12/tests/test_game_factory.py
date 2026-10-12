from brain_v12.business.game_factory import GameFactory, GameGenre

def test_game_factory_is_deterministic():
    a=GameFactory().create("Brain Runner", GameGenre.ARCADE, "WEB", 2)
    b=GameFactory().create("Brain Runner", GameGenre.ARCADE, "WEB", 2)
    assert a.game_id == b.game_id
    assert a.fingerprint == b.fingerprint

def test_negative_price_rejected():
    try: GameFactory().create("Bad", price_jod=-1)
    except ValueError: return
    assert False
