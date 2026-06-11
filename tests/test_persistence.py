"""Storage layer: database CRUD and settings validation/round-trips."""

from __future__ import annotations

from music_theory.storage import Database, Settings


def test_profile_defaults_and_xp(db):
    prof = db.get_profile()
    assert prof["name"] == "Learner"
    db.add_xp(50)
    assert db.get_profile()["total_xp"] == 50
    db.update_profile(name="Ada", streak_days=3)
    prof = db.get_profile()
    assert prof["name"] == "Ada" and prof["streak_days"] == 3


def test_mastery_upsert_roundtrip(db):
    db.upsert_mastery("skill.x", rating=1234.5, mastery_prob=0.6, unlocked=1)
    m = db.get_mastery("skill.x")
    assert abs(m["rating"] - 1234.5) < 1e-6 and m["unlocked"] == 1
    db.upsert_mastery("skill.x", mastery_prob=0.9)
    assert abs(db.get_mastery("skill.x")["mastery_prob"] - 0.9) < 1e-6
    assert abs(db.get_mastery("skill.x")["rating"] - 1234.5) < 1e-6


def test_attempts_and_counts(db):
    for i in range(5):
        db.log_attempt("skill.y", i % 2 == 0, domain="theory", difficulty=3.0)
    n, c = db.attempt_counts()
    assert n == 5 and c == 3


def test_placement_storage(db):
    db.save_placement("theory", 4.2, ci=0.6, level="Intermediate", n_items=9)
    latest = db.latest_placement()
    assert latest["theory"]["level"] == "Intermediate"


def test_kv_json(db):
    db.kv_set("foo", {"a": [1, 2, 3]})
    assert db.kv_get("foo") == {"a": [1, 2, 3]}
    assert db.kv_get("missing", 42) == 42


def test_sql_injection_safe(db):
    nasty = "x'); DROP TABLE mastery;--"
    db.upsert_mastery(nasty, rating=999)
    assert db.get_mastery(nasty)["rating"] == 999
    # table still present and usable
    db.upsert_mastery("ok", rating=1)
    assert db.get_mastery("ok") is not None


def test_settings_validation(settings):
    settings.set("master_volume", 0.5)
    assert settings.get("master_volume") == 0.5
    settings.set("master_volume", "loud")     # wrong type ignored
    assert settings.get("master_volume") == 0.5
    settings.set("unknown_key", 1)             # unknown key ignored
    assert settings.get("unknown_key") is None


def test_settings_persist(tmp_path):
    p = tmp_path / "s.json"
    s1 = Settings(p)
    s1.set("default_tempo", 132)
    s2 = Settings(p)
    assert s2.get("default_tempo") == 132


def test_settings_corrupt_file_degrades(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{ this is not valid json ", encoding="utf-8")
    s = Settings(p)
    assert s.get("default_tempo") == 90   # falls back to default
