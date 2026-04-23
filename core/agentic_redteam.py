from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .evaluator import evaluate_probe_response
from .probes import Probe, get_all_probes
from .scenarios import get_scenarios


@dataclass
class AgenticTurnResult:
    step: str
    probe_id: str
    passed: bool
    indicators: List[str]
    response: str

    def to_dict(self) -> Dict[str, object]:
        return {
            'step': self.step,
            'probe_id': self.probe_id,
            'passed': self.passed,
            'indicators': list(self.indicators),
            'response': self.response,
        }


def _scenario_probe_bank(domain: str) -> Dict[str, List[Probe]]:
    probes = [p for p in get_all_probes() if p.domain in {'general', domain}]
    bank: Dict[str, List[Probe]] = {
        'user_input': [p for p in probes if any(tag in p.tags for tag in ['prompt_injection', 'attack_surface', 'tool_use'])],
        'retrieval_context': [p for p in probes if any(tag in p.tags for tag in ['rag_security', 'retrieval', 'citation_integrity', 'prompt_extraction'])],
        'tool_parameters': [p for p in probes if any(tag in p.tags for tag in ['tool_boundary', 'tool_misuse', 'filesystem', 'scope_violation'])],
        'export_or_render_step': [p for p in probes if any(tag in p.tags for tag in ['privacy', 'phi_exposure', 'secret_exposure', 'classified'])],
    }
    return bank


def run_agentic_redteam(model_adapter, domain: str = 'general', scenario_ids: Optional[Iterable[str]] = None, max_turns_per_scenario: int = 4) -> Dict[str, object]:
    scenarios = [s for s in get_scenarios(domain) if not scenario_ids or s['scenario_id'] in set(scenario_ids)]
    probe_bank = _scenario_probe_bank(domain)
    scenario_results: List[Dict[str, object]] = []
    failed_turns = 0
    total_turns = 0

    for scenario in scenarios:
        turns: List[AgenticTurnResult] = []
        for step in scenario.get('attack_injection_points', [])[:max_turns_per_scenario]:
            candidates = probe_bank.get(step, [])
            if not candidates:
                continue
            probe = candidates[total_turns % len(candidates)]
            response = model_adapter.generate(probe.prompt)
            evaluation = evaluate_probe_response(probe, response)
            turns.append(AgenticTurnResult(step, probe.probe_id, evaluation.passed, evaluation.indicators, evaluation.response))
            total_turns += 1
            if not evaluation.passed:
                failed_turns += 1
        scenario_results.append({
            'scenario_id': scenario['scenario_id'],
            'domain': scenario['domain'],
            'description': scenario['description'],
            'turns': [turn.to_dict() for turn in turns],
            'failed_turns': sum(1 for turn in turns if not turn.passed),
            'turn_count': len(turns),
        })

    pass_rate = round((total_turns - failed_turns) / max(total_turns, 1), 2)
    return {
        'scenario_count': len(scenario_results),
        'turn_count': total_turns,
        'failed_turns': failed_turns,
        'pass_rate': pass_rate,
        'scenario_results': scenario_results,
    }
