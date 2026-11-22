#!/usr/bin/env python3
"""Verify manuscript numbers, source integrity, XML packaging and rendered PDF text."""
import csv,json,re,hashlib,subprocess,sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'paper'
sys.path.insert(0,str(ROOT/'scripts'))
from build_ieee_paper import parse

def main():
    report=json.loads((P/'results/finalized_results.json').read_text());blocks=parse()
    tables=[b[1] for b in blocks if b[0]=='table']
    assert len(tables)==5
    assert report['independent_seeds']==2 and report['api_attempts']==141
    assert report['reported_tokens_lower_bound']==815568 and report['unique_accepted_judgments']==16
    for row,expected in zip(tables[1][1:],report['main_means']):
        assert [float(v) for v in row[1:]]==[expected[m] for m in ['novelty','feasibility','clarity','importance','evidence_grounding']]
    for row,expected in zip(tables[2][1:],report['progression_means']):
        assert [float(v) for v in row[1:]]==[expected[m] for m in ['novelty','feasibility','clarity','importance','evidence_grounding']]
    latest=json.loads((P/'results/v8_case_summary.json').read_text())
    assert hashlib.sha256((ROOT/latest['source_file']).read_bytes()).hexdigest()==latest['source_sha256']
    for row,expected in zip(tables[4][1:],latest['scores']):
        assert [float(v) for v in row[1:]]==[expected[m] for m in ['novelty','feasibility','clarity','importance','evidence_grounding']]
    assert len(tables[4][1:])==4 and latest['independent_topics']==1
    assert latest['attempts']==43 and latest['reported_tokens_lower_bound']==496679
    assert latest['shared_judge_context']['paper_count']==19
    raw=json.loads((P/'results/source_hashes.json').read_text())
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in raw.items())
    manuscript=(P/'manuscript.md').read_text();body=manuscript.split('## References')[0]
    assert set(map(int,re.findall(r'\[(\d+)\]',body)))==set(range(1,13))
    assert sum(report['reviews_with_off_role_scores'].values())==71
    assert sum(report['successful_reviews_by_role'].values())==88
    assert '71 of 88' in body
    with (P/'results/resource_records.csv').open() as f: resources=list(csv.DictReader(f))
    for row,config in zip(tables[3][1:],['one_shot','generic','full','no_feasibility','no_contrarian','no_novelty_retrieval']):
        rs=[r for r in resources if r['configuration']==config]
        counts=[int(r['additional_api_attempts']) for r in rs];secs=[float(r['additional_seconds']) for r in rs]
        expected=str(min(counts)) if min(counts)==max(counts) else f'{min(counts)}–{max(counts)}'
        assert row[1]==expected
        assert row[2]==('<0.01' if max(secs)<.01 else f'{min(secs):.1f}–{max(secs):.1f}')
    case=next(c for c in report['cases'] if c['run_id']=='fff8592ef95a73dda616')
    assert case['attempts']==13 and case['reported_tokens']==133543
    assert len(case['audit']['assessments'])==6
    job=json.loads((ROOT/'results/web_runs'/case['job_id']/'job.json').read_text())
    reviews=[o for rd in job['result']['rounds'] for o in rd['reviews']]+job['result']['final_reviews']
    own={'novelty':['novelty'],'feasibility':['feasibility'],'clarity':['clarity','importance'],'contrarian':[]}
    assert len(reviews)==8 and all(o['review'].get(m) is None for o in reviews for m in ['novelty','feasibility','clarity','importance'] if m not in own[o['role']])
    with ZipFile(P/'Research_Paper_IEEE.docx') as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith(('.xml','.rels')):ET.fromstring(z.read(name))
        doc=ET.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        assert [c.get('{'+ns['w']+'}num') for c in doc.findall('.//w:cols',ns)]==['1','2']
        assert len([n for n in z.namelist() if n.startswith('word/media/')])==3
        assert 'Times New Roman' in z.read('word/styles.xml').decode()
    tex=(P/'main.tex').read_text()
    assert r'\documentclass[conference]{IEEEtran}' in tex
    assert len(re.findall(r'\\bibitem\{r\d+\}',tex))==12
    assert len(re.findall(r'\\begin\{figure\}',tex))==3
    text=subprocess.check_output(['pdftotext','-raw',str(P/'Research_Paper_IEEE.pdf'),'-']).decode()
    normalized=' '.join(text.split())
    for title in ['INTRODUCTION','RELATED WORK','SYSTEM AND STUDY PROTOCOL','EXPERIMENTAL SETUP','RESULTS','POST-PILOT CASE STUDY AND EVALUATION REPAIR','LIMITATIONS AND IMPLICATIONS','CONCLUSION','ACKNOWLEDGMENT','REFERENCES']:
        assert re.sub(r'\s+','',title) in re.sub(r'\s+','',normalized),title
    for number in [1,2,3,4,5,6,7,8,9,10,11,12]:assert f'[{number}]' in normalized
    assert all(s in normalized for s in ['815,568','133,543','71 of 88','182.66','496,679','633.24','Evaluation Metrics','Future Work'])
    info=subprocess.check_output(['pdfinfo',str(P/'Research_Paper_IEEE.pdf')]).decode()
    fonts=subprocess.check_output(['pdffonts',str(P/'Research_Paper_IEEE.pdf')]).decode()
    pages=int(re.search(r'Pages:\s+(\d+)',info)[1]);assert pages==json.loads((P/'build_manifest.json').read_text())['pages']
    assert '612 x 792' in info and 'CID TrueType' in fonts
    result={'status':'passed','source_files_hash_verified':len(raw),'main_results_tables_checked':2,
            'references_checked':12,'docx_xml':'valid; one-column title and two-column body',
            'pdf_pages':pages,'pdf_page_size':'US Letter','pdf_fonts':'embedded TrueType subsets',
            'pdf_text':'all sections, reference numbers and key statistics extracted',
            'visual_inspection':'See visual_inspection.json for the separately recorded review of this PDF.',
            'latest_case_table':'verified against hash-bound live trace; separate from pilot',
            'limitations':['IEEEtran source not compiled locally (TeX unavailable).',
                           'DOCX package validated but Word/LibreOffice rendering not available.',
                           'PDF is an IEEE-style reading copy, not a PDF eXpress certification.']}
    (P/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
