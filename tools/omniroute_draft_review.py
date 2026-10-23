#!/usr/bin/env python3
"""Read-only private OmniRoute draft receipt review gate.

Checks source freshness and receipt integrity before a human/ChatGPT reviewer
uses draft findings. Does NOT judge truth, approve code, control Mac, execute
scripts, run models, publish private content or mutate the job queue.
No model response content or secrets are displayed.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import stat
import sys

import omniroute_workpack_runner as worker

MAX_RECEIPT = 60000
SUCCESS = 'draft_completed_needs_review'
STATES = frozenset((SUCCESS,'reserved_no_retry','needs_review_no_auto_retry'))
BASE = frozenset(('schema_version','id','model','status','created_at',
                  'provenance','external_effects_allowed','source_edits',
                  'mac_control_verified','user_review_required'))
SUCCESS_FIELDS = frozenset(('answer','usage_reported','elapsed_seconds'))
ERROR_FIELDS = frozenset(('error_class','elapsed_seconds'))
# High-confidence markers, not a complete sensitive-data classifier.
SECRET_MARKERS = (
    re.compile(r'-----BEGIN [A-Z ]{0,35}PRIVATE KEY-----'),
    re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
    re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
)
EXECUTION_CLAIMS = re.compile(
    r'\b(?:I|we) (?:have )?(?:ran|executed|verified|installed|deployed|'
    r'connected|tested|opened|created|modified|launched) (?:the |a |your )?'
    r'(?:Mac|Final Cut|OmniRoute|terminal|command|runner|bridge|app|workflow|'
    r'production|system|code|source|repository|GitHub|test)',
    re.IGNORECASE,
)


# The client in PR #51 limits responses to 2400 completion tokens but does
# not save finish_reason. This threshold indicates *possible* truncation.
NEAR_COMPLETION_CAP = 2390
REPORT_DATE_HEADER = re.compile(
    r'(?im)^[ \t]*(?:#{1,4}[ \t]*)?(?:\*{1,2})?'
    r'(?:analysis[ \t]+date|document[ \t]+date|date)'
    r'(?:\*{1,2})?[ \t]*:[ \t]*(?:\*{1,2})?'
    r'(\d{4})[-/](\d{2}|XX)[-/](\d{2}|XX)(?![0-9A-Za-z])'
)


def _safe_directory(path):
    # Never create directories or modify permissions during inspection.
    if path.is_symlink() or not path.is_dir():
        return False
    if any(ancestor.is_symlink() for ancestor in path.parents):
        return False
    return True


def _read_receipt(path):
    if path.is_symlink() or not path.is_file():
        return None
    with path.open('rb') as f:
        blob=f.read(MAX_RECEIPT+1)
    if len(blob)>MAX_RECEIPT:
        return None
    try:
        item=json.loads(blob)
    except (UnicodeError,ValueError):
        return None
    return item if isinstance(item,dict) else None


def _valid_time(value):
    if not isinstance(value,str) or len(value)>64:
        return False
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def _valid_usage(u):
    return (u is None or
            (isinstance(u,dict) and len(u)<=3 and all(
                name in {'prompt_tokens','completion_tokens','total_tokens'}
                and type(count) is int and 0<=count<=100000000
                for name,count in u.items())))


def check_receipt(obj,expected_id,expected_provenance):
    """Return compact verdict; never return or log untrusted model text."""
    if not isinstance(obj,dict):
        return 'invalid_receipt', ['missing_or_unreadable'], False, False
    state=obj.get('status')
    if state not in STATES:
        return 'invalid_receipt', ['unknown_state'], False, False
    keys=BASE | (SUCCESS_FIELDS if state==SUCCESS
                   else ERROR_FIELDS if state=='needs_review_no_auto_retry'
                   else frozenset())
    if set(obj)!=keys:
        return 'invalid_receipt', ['schema_fields_mismatch'], False, False
    if (obj.get('schema_version')!=1
            or obj.get('id')!=expected_id
            or not isinstance(obj.get('model'),str)
            or not worker.MODEL.fullmatch(obj['model'])
            or not _valid_time(obj.get('created_at'))
            or obj.get('external_effects_allowed') is not False
            or obj.get('source_edits') is not False
            or obj.get('mac_control_verified') is not False
            or obj.get('user_review_required') is not True):
        return 'invalid_receipt', ['identity_or_permission_inconsistent'],False,False
    if obj.get('provenance')!=expected_provenance:
        return 'stale_source', ['source_digest_mismatch'],False,False
    if state=='reserved_no_retry':
        return 'incomplete_needs_review', ['model_job_reserved_or_interrupted'], True, False
    if state=='needs_review_no_auto_retry':
        if (not isinstance(obj.get('error_class'),str)
                or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,79}',
                                    obj['error_class'])
                or type(obj.get('elapsed_seconds')) not in (int,float)
                or not 0<=obj['elapsed_seconds']<=3600):
            return 'invalid_receipt',['invalid_error_metadata'],True,False
        return 'failed_needs_review',['inference_failure_no_retry'],True,False
    text=obj.get('answer')
    if (not isinstance(text,str) or not text.strip()
            or len(text)>worker.MAX_OUTPUT
            or type(obj.get('elapsed_seconds')) not in (int,float)
            or not 0<=obj['elapsed_seconds']<=3600
            or not _valid_usage(obj.get('usage_reported'))):
        return 'invalid_receipt',['invalid_answer_or_usage'],True,False
    if any(marker.search(text) for marker in SECRET_MARKERS):
        return 'sensitive_draft_blocked', ['possible_secret_in_private_answer'],True,True
    if EXECUTION_CLAIMS.search(text):
        return 'execution_claim_needs_review', ['unsupported_execution_claim'],True,True
    # Inspect only header metadata. Dates inside the analysis body may describe
    # historical evidence and must not be treated as the report date.
    concerns=[]
    usage=obj.get('usage_reported')
    if isinstance(usage,dict):
        count=usage.get('completion_tokens')
        if type(count) is int and count >= NEAR_COMPLETION_CAP:
            concerns.append('near_completion_token_cap_truncation_unknown')
    report_date=REPORT_DATE_HEADER.search(text[:1800])
    if report_date:
        if 'XX' in report_date.group(0).upper():
            concerns.append('report_date_placeholder')
        elif int(report_date.group(1)) != datetime.fromisoformat(obj['created_at']).year:
            concerns.append('report_header_year_mismatch')
    if concerns:
        return 'content_quality_needs_review', concerns, True, True
    return 'draft_ready_for_human_review', ['content_quality_not_automatically_verified'],True,True


def inspect(repo_root,receipt_root,slug):
    """Pure read-only: receipt output is explicitly content-free."""
    if slug not in worker.PACKETS:
        raise ValueError('Unrecognized curated packet')
    packet,_,provenance=worker.load_packet(repo_root,slug)
    result={
        'packet_id':packet['id'],
        'status':'missing_private_receipt',
        'source_fresh':False,
        'response_present':False,
        'approval_granted':False,
        'actual_mac_execution_verified':False,
        'evidence':'local_receipt_inspection_only',
        'reasons':[],
    }
    if not _safe_directory(receipt_root):
        result['status']='private_receipt_root_unavailable'
        result['reasons']=['missing_or_redirected_private_folder']
        return result
    path=receipt_root/(slug+'.receipt.json')
    obj=_read_receipt(path)
    status,reasons,fresh,responded=check_receipt(obj,packet['id'],provenance)
    result.update(status=status,source_fresh=fresh,
                  response_present=responded,reasons=reasons)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path.cwd())
    parser.add_argument('--receipts',type=Path,
        default=Path.home()/'Documents'/'Rovor'/'OmniRoute-Draft-Receipts')
    choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--packet',choices=worker.PACKETS)
    choice.add_argument('--all',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.repo.expanduser().absolute()
        receipts=args.receipts.expanduser().absolute()
        if root.is_symlink() or not (root/'WORK.md').is_file():
            raise ValueError('Expected trusted repo checkout')
        if root==receipts or root in receipts.parents:
            raise ValueError('Private receipts cannot be under Git checkout')
        slugs=worker.PACKETS if args.all else (args.packet,)
        outcomes=[inspect(root,receipts,slug) for slug in slugs]
        print(json.dumps({'status':'private_draft_review_only',
                          'results':outcomes,
                          'external_effects_performed':False,
                          'automatic_task_approval':False},indent=2,sort_keys=True))
        return 0 if all(t['status']=='draft_ready_for_human_review'
                        for t in outcomes) else 2
    except (ValueError,OSError,UnicodeError) as exc:
        print(json.dumps({'status':'review_refused',
                          'reason':type(exc).__name__,
                          'automatic_task_approval':False,
                          'external_effects_performed':False}),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
