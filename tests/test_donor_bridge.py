
from core.donor_bridge import donor_catalog, execute_attack_campaigns, execute_multi_turn, load_attack_campaigns, load_domain_packs, load_multi_turn_chains
from models.model_adapter import ModelAdapter, ModelConfig


def _model():
    return ModelAdapter(ModelConfig(provider='policy_harness', model_name='policy_harness'))


def test_donor_catalog_has_depth():
    catalog = donor_catalog()
    assert catalog['asset_collections'] >= 20
    assert catalog['total_items'] >= 200


def test_named_collections_load():
    assert len(load_multi_turn_chains()) >= 5
    assert len(load_attack_campaigns()) >= 5
    packs = load_domain_packs()
    assert len(packs['healthcare']) >= 10
    assert len(packs['finance']) >= 5


def test_execute_multi_turn_runs():
    result = execute_multi_turn(_model(), limit=3)
    assert result['count'] == 3
    assert 'results' in result and len(result['results']) == 3


def test_execute_attack_campaigns_runs():
    result = execute_attack_campaigns(_model(), limit=2)
    assert result['count'] == 2
    assert all('phases' in row for row in result['results'])
