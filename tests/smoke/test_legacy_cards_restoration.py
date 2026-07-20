from pathlib import Path


def test_legacy_cards_are_restored_from_legal_entities() -> None:
    source = Path(
        "migrations/versions/"
        "20260720_03_restore_legacy_cards_as_organizations.py"
    ).read_text(encoding="utf-8")

    assert "FROM legal_entities AS legal_entity" in source
    assert "organization.inn = legal_entity.inn" in source
    assert "'legacy_card_restored'" in source
    assert "CREATE TABLE companies" not in source
