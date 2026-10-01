"""Export the archived development results used by the revised ISPA draft.

This script performs no training and creates no synthetic experimental data.
Run-level JSON reports are the numerical source. Original remote console logs
are not present in this checkout; their earlier validation is not repeated here.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import statistics as st

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[1]
ARCHIVE = ROOT / 'TTFL_snapshot_20260925/source/experiments/results'
DATA = OUT / 'revision_evidence'
FIG = OUT / 'figures_revised'
DATA.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
SOURCES = {
    'standard': ('v2_30r_s2_20260927', 'long_window_report.json'),
    'known_trigger': ('v2_30r_probe_s2_20260927', 'probe_report.json'),
    'recovery': ('v2_30r_recovery_s2_20260927', 'recovery_report.json'),
}
METHODS = ['fedavg', 'fltrust', 'single_stream', 'ttfl']
LABELS = dict(zip(METHODS, ['FedAvg', 'FLTrust', 'Single-state', 'TTFL']))
SCENARIOS = ['none', 'backdoor', 'delayed_backdoor']
SC_LABELS = ['No attack', 'Persistent', 'Delayed']
KEYS = ['final_accuracy', 'final_asr', 'attack_window_mean_asr',
        'normal_mean_exclusion', 'normal_ever_excluded_rate']
all_runs, groups, provenance = {}, {}, []
initial_by_seed = {}
partitions_by_seed = {}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for condition, (folder, name) in SOURCES.items():
    source = ARCHIVE / folder / name
    report = json.loads(source.read_text())
    runs = report['runs']
    assert len(runs) == {'standard':24, 'known_trigger':12, 'recovery':8}[condition]
    assert len({(r['scenario'],r['method'],r['seed']) for r in runs}) == len(runs)
    for run in runs:
        assert len(run['clean_accuracy']) == len(run['backdoor_asr']) == 30
        assert run['rounds'] == 30
        assert math.isclose(run['clean_accuracy'][-1], run['final_accuracy'])
        assert math.isclose(run['backdoor_asr'][-1], run['final_asr'])
        assert all(0 <= x <= 1 for x in run['clean_accuracy'] + run['backdoor_asr'])
        run_dir = source.parent / run['run_id']
        manifest_path = run_dir / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        assert manifest['clients'] == 20 and manifest['rounds'] == 30
        assert manifest['local_epochs'] == 1
        assert manifest['server_proxy_size'] == 500
        assert manifest['shared_client_pool_size'] == 0
        assert manifest['asr_excludes_target_label'] is True
        assert manifest['seed'] == run['seed']
        assert manifest['known_trigger_probe'] == (condition == 'known_trigger')
        initial = json.loads((run_dir/'initial_model.json').read_text())['sha256']
        assert initial_by_seed.setdefault(run['seed'], initial) == initial
        proxy_file = run_dir/'partitions/server_proxy.json'
        client_files = sorted((run_dir/'partitions').glob('client_*.json'))
        assert len(client_files) == 20
        proxy = set(json.loads(proxy_file.read_text())['indices'])
        clients = {f.stem: json.loads(f.read_text())['indices'] for f in client_files}
        flat = [i for values in clients.values() for i in values]
        assert len(proxy) == 500 and len(flat) == len(set(flat)) == 49500
        assert not proxy.intersection(flat)
        partition_digest = hashlib.sha256(json.dumps(
            {'proxy':sorted(proxy),'clients':clients},sort_keys=True).encode()).hexdigest()
        assert partitions_by_seed.setdefault(run['seed'],partition_digest) == partition_digest
        if run['attack_start_round'] is not None:
            stop = manifest['attack_stop_round'] or 31
            window = run['backdoor_asr'][manifest['attack_start_round']-1:stop-1]
            assert math.isclose(st.mean(window), run['attack_window_mean_asr'])
        rates = run.get('normal_exclusion_by_round')
        if rates is not None:
            assert len(rates) == 30
            assert math.isclose(st.mean(rates), run['normal_mean_exclusion'])
        completion = json.loads((run_dir / 'completion.json').read_text())
        assert completion['status'] == 'success'
        provenance.append({
            'condition':condition, 'run_id':run['run_id'], 'manifest':manifest,
            'manifest_sha256':sha(manifest_path),
            'report_path':str(source.relative_to(ROOT)), 'report_sha256':sha(source),
            'completion':completion,
            'initial_model_sha256':initial,
            'partition_indices_sha256':partition_digest,
            'disjoint_training_indices_checked':True,
            'local_console_log_available':bool(list(run_dir.glob('**/server.log'))),
        })
    all_runs[condition] = runs
    (DATA / f'{condition}_runs.json').write_text(json.dumps(runs, indent=2))
    group_rows = []
    for scenario in sorted({r['scenario'] for r in runs}):
        for method in METHODS:
            selected = [r for r in runs if r['scenario']==scenario and r['method']==method]
            if not selected:
                continue
            assert len(selected)==2
            row = {'scenario':scenario, 'method':method, 'n':2}
            for key in KEYS:
                values = [r[key] for r in selected if r[key] is not None]
                row[key] = {'mean':st.mean(values),'sd':st.stdev(values)} if values else None
            # Check the archived group summaries against independently recomputed statistics.
            if 'groups' in report:
                old = next(g for g in report['groups'] if g['scenario']==scenario and g['method']==method)
                for key in KEYS:
                    if row[key] is not None:
                        for stat in ('mean','sd'):
                            assert math.isclose(row[key][stat],old[key][stat],abs_tol=1e-12)
            group_rows.append(row)
    groups[condition] = group_rows

(DATA/'provenance.json').write_text(json.dumps(provenance,indent=2))
(DATA/'group_statistics.json').write_text(json.dumps(groups,indent=2))
with (DATA/'per_seed_results.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['condition','run_id','scenario','method','seed',*KEYS])
    writer.writeheader()
    for condition,runs in all_runs.items():
        for run in runs:
            writer.writerow({'condition':condition,**{k:run[k] for k in writer.fieldnames[1:]}})
with (DATA/'round_curves.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['condition','run_id','seed','method','scenario','round','accuracy','asr','benign_exclusion'])
    for condition,runs in all_runs.items():
        for r in runs:
            rates=r.get('normal_exclusion_by_round',[None]*30)
            for i in range(30):
                writer.writerow([condition,r['run_id'],r['seed'],r['method'],r['scenario'],i+1,r['clean_accuracy'][i],r['backdoor_asr'][i],rates[i]])

def cell(obj):
    return '--' if obj is None else f"${100*obj['mean']:.2f}\\pm{100*obj['sd']:.2f}$"

for condition in ['standard','known_trigger']:
    rows=[]
    for scenario,label in zip(SCENARIOS,SC_LABELS):
        for method in METHODS:
            g=next((x for x in groups[condition] if x['scenario']==scenario and x['method']==method),None)
            if g:
                rows.append(' & '.join([label,LABELS[method],*[cell(g[k]) for k in KEYS]])+r' \\')
        rows.append(r'\midrule')
    (DATA/f'{condition}_table.tex').write_text('\n'.join(rows[:-1])+'\n')

manuscript = OUT/'ispa2026_submission_revised.tex'
if manuscript.exists():
    source = manuscript.read_text()
    block = ('% BEGIN GENERATED STANDARD TABLE\n' +
             (DATA/'standard_table.tex').read_text().rstrip() +
             '\n% END GENERATED STANDARD TABLE')
    source = re.sub(r'% BEGIN GENERATED STANDARD TABLE.*?% END GENERATED STANDARD TABLE',
                    lambda match: block, source, flags=re.S)
    manuscript.write_text(source)

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.labelsize':8,
    'legend.fontsize':7,'xtick.labelsize':7,'ytick.labelsize':7,'pdf.fonttype':42,
    'ps.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
colors=['#737373','#aa7334','#2171a6','#a43136']
styles=[':', '-.', '--', '-']
markers=['^','s','o','D']

def export(fig,name):
    for ext in ['pdf','svg','png']:
        fig.savefig(FIG/f'{name}.{ext}',dpi=250,bbox_inches='tight',pad_inches=.03)
    plt.close(fig)

# Full comparison: raw per-seed trajectories, with no invented error bars.
fig,axes=plt.subplots(2,3,figsize=(7.16,3.8),sharex=True)
for col,scenario in enumerate(SCENARIOS):
    for mi,method in enumerate(METHODS):
        runs=[r for r in all_runs['standard'] if r['scenario']==scenario and r['method']==method]
        for row,key in enumerate(['clean_accuracy','backdoor_asr']):
            ax=axes[row,col]
            ys=np.array([r[key] for r in runs])*100
            for ys_seed in ys:
                ax.plot(range(1,31),ys_seed,color=colors[mi],lw=.55,alpha=.35)
            ax.plot(range(1,31),ys.mean(0),color=colors[mi],ls=styles[mi],lw=1.15,
                marker=markers[mi],markevery=6,ms=2.5,label=LABELS[method])
            ax.set_ylim(0,65 if row==0 else 100);ax.set_xlim(1,30)
            ax.grid(alpha=.17,lw=.5)
            if scenario=='delayed_backdoor':ax.axvline(11,color='.25',ls=':',lw=.7)
            if row==1:ax.set_xlabel('Communication round')
    axes[0,col].set_title(SC_LABELS[col],fontsize=9)
axes[0,0].set_ylabel('Clean accuracy (%)')
axes[1,0].set_ylabel('Target-hit rate / ASR (%)')
handles,labels=axes[0,0].get_legend_handles_labels()
fig.legend(handles,labels,loc='upper center',ncol=4,bbox_to_anchor=(.52,1.05),frameon=False)
fig.tight_layout(h_pad=.8,w_pad=.8)
export(fig,'fig_results')

# Paired conditions: expose the cost in benign participation.
fig,axes=plt.subplots(1,3,figsize=(7.16,2.15))
for col,(key,title) in enumerate([('final_asr','Final ASR (%)'),('attack_window_mean_asr','Attack-window ASR (%)'),('normal_mean_exclusion','Benign exclusion (%)')]):
    ax=axes[col]
    for mi,method in enumerate(['single_stream','ttfl']):
        for ci,condition in enumerate(['standard','known_trigger']):
            xx=np.array([0.,1.])+(-.22 if mi==0 else .22)+(-.06 if ci==0 else .06)
            means=[]
            for x,scenario in zip(xx,['backdoor','delayed_backdoor']):
                vals=[100*r[key] for r in all_runs[condition] if r['method']==method and r['scenario']==scenario]
                means.append(st.mean(vals))
                ax.plot([x]*2,vals,color=colors[mi+2],marker='o' if ci==0 else 's',ls='',ms=3,
                    markerfacecolor='white' if ci==0 else colors[mi+2])
            ax.plot(xx,means,ls='--' if ci==0 else '-',lw=.9,color=colors[mi+2],
                label=f"{LABELS[method]}, {'K0' if ci==0 else 'K1'}")
    ax.set_xticks([0,1],['Persistent','Delayed']);ax.set_xlim(-.45,1.45)
    ax.set_ylabel(title);ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.2)
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='upper center',ncol=2,bbox_to_anchor=(.5,1.2),frameon=False)
fig.tight_layout(w_pad=.6)
export(fig,'fig_probe_tradeoff')

# Direct participation for the attacked client: two seeds, no inferred weights.
fig,axes=plt.subplots(1,2,figsize=(7.16,2.1),sharey=True)
for ax,scenario,title in zip(axes,['backdoor','delayed_backdoor'],['Persistent attack','Delayed attack']):
    for si,seed in enumerate([20240925,20240926]):
        r=next(x for x in all_runs['known_trigger'] if x['method']=='ttfl' and x['scenario']==scenario and x['seed']==seed)
        source=ARCHIVE/SOURCES['known_trigger'][0]/r['run_id']/'round_metrics.jsonl'
        audit=[json.loads(line) for line in source.read_text().splitlines() if line.strip()]
        repairs={(x['round'],str(x['client_id'])) for x in r['audit_provenance']['blacklist_records_recovered']}
        vals=[]
        for row in audit:
            stat=row['client_layer_stats'].get('1')
            if stat is None:
                assert (row['round'],'1') in repairs
                vals.append(0.)
            else: vals.append(100*stat['included_layers']/row['layer_count'])
        ax.step(range(1,31),vals,where='mid',color=colors[si+2],ls=styles[si+2],lw=1.2,label=str(seed))
    ax.axvline(1 if scenario=='backdoor' else 11,color='.3',ls=':',lw=.8)
    ax.set_title(title,fontsize=9);ax.set_xlabel('Communication round')
    ax.set_xlim(.5,30.5);ax.set_ylim(-3,103);ax.grid(alpha=.18)
axes[0].set_ylabel('Attacker tensors admitted (%)')
axes[1].legend(title='Development seed',frameon=False,fontsize=7,title_fontsize=7)
fig.tight_layout()
export(fig,'fig_attacker_participation')
print(f'Validated numerical consistency of {sum(map(len,all_runs.values()))} archived runs; exported tables, per-seed data and 3 figures.')
