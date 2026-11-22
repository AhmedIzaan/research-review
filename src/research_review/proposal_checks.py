"""Transparent bounded checks; heuristic findings are never experimental results."""
import re

GENERIC=re.compile(r'^(?:public\b.*datasets?|.*\b(?:runtime|logits|token.level masks|consumer gpu|instruction.tuned model|open.weight models?|language models?)\b.*)$',re.I)
MODEL=re.compile(r'\b(?:Llama|Qwen|Mistral|Gemma|Phi|DeepSeek)[A-Za-z0-9_.-]*\d[A-Za-z0-9_.-]*',re.I)
REPO=re.compile(r'(?<![\w/])([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?![\w/])')

def searchable_entity(entity):
    return bool(entity.strip()) and not GENERIC.fullmatch(entity.strip())

def named_model_mentions(idea):
    """Supplement model extraction for explicit versioned families; bounded, not exhaustive."""
    fields=[idea.methodology,idea.experimental_setup,*idea.feasibility_assumptions,idea.minimum_test or '']
    found={}
    for text in fields:
        for match in MODEL.finditer(text):found.setdefault(match.group(),match.group())
        for match in REPO.finditer(text):
            if MODEL.search(match.group()):found[match.group()]=match.group()
    # Prefer a qualified identifier over its same-name suffix.
    return [(name,excerpt) for name,excerpt in found.items()
            if '/' in name or not any(k.endswith('/'+name) for k in found if '/' in k)]

def experiment_checks(idea):
    text=' '.join([idea.methodology,idea.experimental_setup,idea.evaluation_strategy,*idea.feasibility_assumptions])
    issues=[]
    if re.search(r'\b(?:FP16|BF16)\b',text,re.I):
        sizes=[float(x) for x in re.findall(r'\b(\d+(?:\.\d+)?)\s*B\b',text,re.I)]
        capacities=[float(x) for x in re.findall(r'\b(\d+(?:\.\d+)?)\s*G[Bb]\b',text)]
        if sizes and capacities and max(sizes)*2>max(capacities):
            issues.append({'code':'precision_memory_plan','severity':'needs_resolution' if re.search(r'offload|shard|CPU.reference',text,re.I) else 'repair_required',
                'explanation':f'If all {max(sizes):g} billion parameters are resident at 16 bits, weights alone require about {max(sizes)*2:g} GB (decimal), exceeding the stated {max(capacities):g} GB. Offloading/sharding or another reference model requires an explicit plan.',
                'repair':'Specify each precision configuration, weight residency, memory pilot, and a feasible matched higher-precision reference. A 4-bit-only pilot does not validate FP16.'})
    minimum=idea.minimum_test or ''
    if re.search('quantiz',idea.research_problem,re.I) and re.search(r'4.bit|INT4',minimum,re.I) and not re.search(r'FP16|BF16|INT8|higher.precision|unquantized|reference',minimum,re.I):
        issues.append({'code':'missing_precision_control','severity':'repair_required',
            'explanation':'The minimum test mentions only low-bit inference; it cannot isolate quantization effects without a matched reference.',
            'repair':'Include a feasible higher-precision reference of the same model and inputs; otherwise label this a decoding-only smoke test.'})
    if not named_model_mentions(idea):
        issues.append({'code':'model_identity_unresolved','severity':'needs_resolution',
            'explanation':'No recognized versioned model identifier was recovered by the bounded name checker; this may be an extraction limitation.',
            'repair':'Specify the exact model/repository and runtime; do not erase a model name to avoid verification.'})
    for check in idea.assumption_checks:
        criterion = check.acceptance_criterion
        if re.search(r'statistically significant (?:increase|decrease|improvement|difference)|p\s*[<≤]\s*0?\.0[15]', criterion, re.I):
            issues.append({'code':'hypothesis_as_prerequisite','severity':'repair_required',
                'explanation':'A pilot acceptance criterion requires a significant research outcome: '+criterion,
                'repair':'Use pilot thresholds for data validity, annotation agreement, parseability or runtime. Keep effect direction/significance as outcomes; null results remain valid.'})
    evaluation = idea.evaluation_strategy
    claims = ' '.join([idea.research_problem, idea.expected_contribution, idea.core_hypothesis or ''])
    if re.search(r'explanation|faithful', claims, re.I) and re.search(r'token.overlap|keyword|exact match', evaluation, re.I):
        if not re.search(r'human|annotat|entailment|logical oracle|semantic adjudicat', evaluation, re.I):
            issues.append({'code':'explanation_measure_validation','severity':'repair_required',
                'explanation':'Explanation validity is assessed lexically without an explicit semantic or human validation procedure.',
                'repair':'Define output-level rule tracking; validate the metric against human labels or an explicit semantic/logical oracle. Include label-preserving paraphrases and irrelevant-rule controls. Embedding distance alone does not establish faithfulness.'})
    if re.search(r'persuasi(?:ve|on|veness)', claims, re.I) and not re.search(r'persuasi.*(?:rat|judg|annotat)|(?:rat|judg|annotat).*persuasi', evaluation, re.I):
        issues.append({'code':'persuasiveness_not_operationalized','severity':'needs_resolution',
            'explanation':'The proposal discusses persuasion without an explicit persuasiveness rating procedure.',
            'repair':'Remove the persuasion claim or define blinded ratings and their reliability. Do not infer persuasion from keyword overlap.'})
    return issues


def revision_changes(before, candidate):
    """Record literal edits, never infer scientific resolution from an edit alone."""
    old, new = before.model_dump(), candidate.model_dump()
    changed = [key for key in old if old[key] != new[key]]
    bibliography = {'references', 'prior_work_comparison', 'search_queries'}
    return {
        'changed_fields': changed,
        'literature_only': bool(changed) and set(changed) <= bibliography,
        'field_changes': {key: {'before': old[key], 'after': new[key]} for key in changed},
        'limitation': 'Literal edits are observable; resolving a criticism still requires scientific assessment.'}


def constructed_dataset_claim(claim, idea):
    """Conservative fallback for an unnamed dataset explicitly being constructed.

    Named synthetic benchmarks remain external dependencies. This rule only covers
    generic synthetic descriptions alongside an explicit construction plan.
    """
    entity = claim['entity'].casefold()
    plan = idea.methodology + ' ' + idea.experimental_setup
    return (claim['category'].startswith('dataset') and
            'synthetic' in entity and bool(re.search(r'\b(?:dataset|examples|instances|samples)\b', entity)) and
            bool(re.search(r'\b(?:we|will|to)\s+(?:will\s+)?(?:construct|generate|create)\b', plan, re.I)) and
            not re.search(r'https?://|\w/\w|[A-Z]{2,}', claim['entity']))
