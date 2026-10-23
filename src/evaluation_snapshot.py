"""Build a portable, versioned snapshot from recorded evaluations. Never trains or runs the pipeline.

Run: python -m src.evaluation_snapshot [--reports-dir reports] [--output PATH] [--check]
Missing or invalid measurements stay null, including when other metrics in the report are usable.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / 'frontend/src/data/evaluation.v1.json'


def metric(obj, key, rate=False, integer=False):
    value = obj.get(key) if isinstance(obj, dict) else None
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0 or (rate and value > 1)
            or (integer and int(value) != value)):
        return None
    return int(value) if integer else value


def parse_per_intent(text):
    rows = []
    for line in text.splitlines():
        cells = line.split()
        if len(cells) != 5 or cells[0] in {'macro', 'weighted'}:
            continue
        try:
            values = dict(zip(('precision', 'recall', 'f1', 'support'), map(float, cells[1:])))
        except ValueError:
            continue
        values = {k: metric(values, k, rate=k != 'support', integer=k == 'support') for k in values}
        if all(v is not None for v in values.values()):
            rows.append({'intent': cells[0], **values})
    return rows


def parse_classifier(raw, per_intent=(), dataset=(), per_intent_text=''):
    benchmark = raw.get('bitext_test') or {}
    realistic = raw.get('realistic_test') or {}
    split = [r for r in dataset if r.get('split') == 'test']
    n = metric(realistic, 'n', integer=True)
    matched = bool(split) and len(split) == n and all(r.get('intent') for r in split)
    support = sum(r['support'] for r in per_intent) if per_intent else None
    aggregate = re.search(r'^\s*accuracy\s+[\d.]+\s+(\d+)\s*$', per_intent_text, re.M)
    if not aggregate or support != int(aggregate[1]):
        support = None
    return {
        'bitextAccuracy': metric(benchmark, 'accuracy', rate=True),
        'bitextF1': metric(benchmark, 'macro_f1', rate=True),
        'baselineAccuracy': metric(benchmark, 'baseline_accuracy', rate=True),
        'bitextN': support,
        'noisyAccuracy': metric(benchmark, 'accuracy_noisy_text', rate=True),
        'categoryAccuracy': metric(benchmark, 'category_accuracy', rate=True),
        'calibrationError': metric(benchmark, 'ece', rate=True),
        'realisticAccuracy': metric(realistic, 'in_scope_accuracy', rate=True),
        'realisticN': n,
        'realisticInScopeN': sum(r['intent'] != 'out_of_scope' for r in split) if matched else None,
        'realisticOosN': sum(r['intent'] == 'out_of_scope' for r in split) if matched else None,
        'realisticF1': metric(realistic, 'macro_f1', rate=True),
        'threshold': metric(raw, 'auto_threshold', rate=True),
        'autoAccuracy': metric(realistic, 'auto_accuracy', rate=True),
        'coverage': metric(realistic, 'auto_coverage_in_scope', rate=True),
    }


def parse_retrieval(text):
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != ['set', 'mode', 'recall@3', 'mrr', 'n']:
        raise ValueError('Unsupported retrieval CSV header')
    rows, seen = [], set()
    for r in reader:
        key = (r['set'], r['mode'])
        if not all(key) or key in seen:
            raise ValueError('Missing or duplicate retrieval configuration')
        seen.add(key)
        values = {}
        for field in ('recall@3', 'mrr', 'n'):
            try:
                values[field] = float(r[field])
            except (ValueError, TypeError):
                values[field] = None
        rows.append({'set': r['set'], 'mode': r['mode'],
                     'recall': metric(values, 'recall@3', rate=True),
                     'mrr': metric(values, 'mrr', rate=True),
                     'n': metric(values, 'n', integer=True)})
    return rows


def parse_predictions(text):
    reader = csv.DictReader(io.StringIO(text))
    required = {'true', 'pred', 'status', 'oos', 'guard_ok', 'has_reply', 'grounded', 'intent_ok'}
    if not required <= set(reader.fieldnames or []):
        raise ValueError('Missing recorded prediction columns')
    rows = list(reader)
    for r in rows:
        if not r['true'] or not r['pred'] or r['status'] not in {'auto_resolved', 'needs_review', 'escalated'}:
            raise ValueError('Invalid prediction row')
        for field in ('oos', 'guard_ok', 'has_reply', 'grounded', 'intent_ok'):
            if r[field] not in {'True', 'False'}:
                raise ValueError('Invalid recorded boolean')
            r[field] = r[field] == 'True'
        if r['oos'] != (r['true'] == 'out_of_scope') or r['intent_ok'] != (r['true'] == r['pred']):
            raise ValueError('Inconsistent recorded prediction')
    return rows


def confusion(rows):
    ins = [r for r in rows if not r['oos']]
    if not ins:
        return None
    labels = sorted({r[k] for r in ins for k in ('true', 'pred')})
    counts = Counter((r['true'], r['pred']) for r in ins)
    return {'labels': labels, 'matrix': [[counts[a, b] for b in labels] for a in labels],
            'n': len(ins), 'correct': sum(r['intent_ok'] for r in ins),
            'scope': 'Recorded pipeline predictions · realistic in-scope · development + test',
            'topConfusions': [{'actual': a, 'predicted': b, 'count': n} for (a, b), n in
                              sorted(counts.items(), key=lambda x: (-x[1], x[0])) if a != b]}


def parse_e2e(raw, predictions=()):
    rate_fields = {'autoPrecision': 'auto_resolve_precision', 'autoCoverage': 'auto_resolve_coverage_in_scope',
                   'guardrailPass': 'guardrail_pass_rate', 'groundedRate': 'grounded_citation_rate',
                   'oosNotAuto': 'out_of_scope_not_auto_resolved'}
    out = {k: metric(raw, v, rate=True) for k, v in rate_fields.items()}
    out.update({k: metric(raw, v) for k, v in {'p50': 'latency_ms_p50', 'p95': 'latency_ms_p95',
               'avgTokens': 'avg_tokens_per_ticket'}.items()})
    out.update(agent=raw.get('agent') if isinstance(raw.get('agent'), str) else None,
               tickets=metric(raw, 'tickets', integer=True),
               routing={k: value for k, v in (raw.get('routing') or {}).items()
                        if (value := metric({k: v}, k, rate=True)) is not None}, counts=None)
    if predictions and len(predictions) == out['tickets']:
        drafted = [r for r in predictions if r['has_reply']]
        grounded = [r for r in drafted if not r['oos']]
        auto = [r for r in predictions if r['status'] == 'auto_resolved']
        out['counts'] = {
            'inScope': sum(not r['oos'] for r in predictions), 'oos': sum(r['oos'] for r in predictions),
            'drafted': len(drafted), 'guardrailPassed': sum(r['guard_ok'] for r in drafted),
            'guardrailFailed': sum(not r['guard_ok'] for r in drafted),
            'groundedEligible': len(grounded), 'groundedPassed': sum(r['grounded'] for r in grounded),
            'autoResolved': len(auto), 'autoCorrect': sum(r['intent_ok'] for r in auto),
            'oosHeld': sum(r['oos'] and r['status'] != 'auto_resolved' for r in predictions),
            'routing': dict(Counter(r['status'] for r in predictions)),
        }
    return out


def build_snapshot(reports_dir=None, root=ROOT):
    root = Path(root)
    folder = Path(reports_dir) if reports_dir else root / 'reports'
    sources = []

    def read(file, base=folder, prefix='reports'):
        source = {'path': f'{prefix}/{file}', 'sha256': None, 'modified': None, 'error': None}
        sources.append(source)
        try:
            path = base / file
            data = path.read_bytes()
            source.update(sha256=hashlib.sha256(data).hexdigest(),
                          modified=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())
            return data.decode('utf-8')
        except (OSError, UnicodeError):
            source['error'] = 'Not measured: source missing or unreadable'
            return None

    def report(file, text, parser):
        result = {'source': f'reports/{file}', 'modified': next(s['modified'] for s in sources if s['path'] == f'reports/{file}'),
                  'data': None, 'error': None}
        try:
            if text is None:
                raise ValueError('Missing source')
            result['data'] = parser(text)
        except (ValueError, TypeError, KeyError, AttributeError):
            result['error'] = 'Not measured: source missing, malformed or incompatible'
        return result

    classifier_text = read('classifier_report.json')
    per_text = read('classifier_per_intent.txt')
    e2e_text = read('e2e_fallback.json')
    predictions_text = read('e2e_fallback.csv')
    retrieval_text = read('retrieval_eval.csv')
    dataset_text = read('realistic_tickets.csv', root / 'eval', 'eval')
    per = report('classifier_per_intent.txt', per_text, parse_per_intent)
    pred = report('e2e_fallback.csv', predictions_text, parse_predictions)
    dataset = list(csv.DictReader(io.StringIO(dataset_text))) if dataset_text else []
    c = report('classifier_report.json', classifier_text, lambda t: parse_classifier(
        json.loads(t), per['data'] or [], dataset, per_text or ''))
    e = report('e2e_fallback.json', e2e_text, lambda t: parse_e2e(json.loads(t), pred['data'] or []))
    matrix = {**pred, 'data': confusion(pred['data']) if pred['data'] else None}
    # Hash records what is present now, never claims the historical evaluation used this exact model.
    model = root / 'models/intent_clf.joblib'
    model_hash = hashlib.sha256(model.read_bytes()).hexdigest() if model.is_file() else None
    return {'schemaVersion': 1, 'generatedAt': datetime.now(timezone.utc).isoformat(),
            'sources': sources, 'modelArtifactSha256AtGeneration': model_hash,
            'classifier': c, 'perIntent': per, 'confusion': matrix, 'e2e': e,
            'retrieval': report('retrieval_eval.csv', retrieval_text, parse_retrieval)}


def canonical(value):
    """Compare data and content hashes, ignoring filesystem timestamps changed by checkout/copy."""
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items() if k not in {'generatedAt', 'modified'}}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports-dir', type=Path)
    p.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    snapshot = build_snapshot(args.reports_dir)
    if args.check:
        if not args.output.exists() or canonical(json.loads(args.output.read_text())) != canonical(snapshot):
            raise SystemExit('Evaluation snapshot is stale; regenerate with python -m src.evaluation_snapshot')
        print('Evaluation snapshot matches source artifacts')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(snapshot, indent=2, allow_nan=False) + '\n')
        print(f'Saved evaluation snapshot: {args.output}')


if __name__ == '__main__':
    main()
