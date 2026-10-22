"""Separate forward-edge Bellman and tight-goal audits of generated tables.

These auditors enumerate forward legal transitions, whereas the generators use
reverse Dijkstra. Every finite value must reach a correctly priced goal along
tight edges; every outgoing edge satisfies Bellman's inequality. Frozen local
fields and the full graph hash are checked independently of metadata hashes.
"""
from array import array
from collections import deque
from pathlib import Path
import hashlib,math,sys
from verifier import load,digest,validate_graph
INF=(1<<32)-1
FULL_SHA='49253c00a0941d94630e5323343af6e2d19e7317f26864fc19e01bc782bc638b'
def read_array(path, meta):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == meta['binary_sha256']
    values = array('I')
    values.frombytes(raw)
    assert values.itemsize == 4
    if sys.byteorder != 'little':
        values.byteswap()
    return values

def graph_fields(meta, frozen):
    graph = meta['local_graph']
    validate_graph(graph)
    assert digest(frozen) == FULL_SHA == meta['full_graph_sha256']
    assert digest(graph) == meta['local_graph_sha256']
    assert graph['nodes'] == frozen['nodes'][:14]
    assert graph['inputs'] == frozen['inputs']
    assert graph['outputs'] == ['b0_residual2']
    return graph

def tight_paths(values, reverse_tight_edges, goals, finite):
    good = bytearray(len(values))
    queue = deque(goals)
    for goal in goals:
        good[goal] = 1
    while queue:
        target = queue.popleft()
        for source in reverse_tight_edges[target]:
            if not good[source]:
                good[source] = 1
                queue.append(source)
    assert sum(good) == finite

def audit_backward(meta_path, frozen):
    meta = load(meta_path)
    graph = graph_fields(meta, frozen)
    nodes = graph['nodes']
    index = {v['id']:i for i,v in enumerate(nodes)}
    needed = set().union(*(set(v['backward_requires']) for v in nodes)) & set(index)
    while True:
        previous = needed.copy()
        for node in nodes:
            if node['id'] in needed:
                needed.update(d for d in node['deps'] if d in index)
        if previous == needed:
            break
    names = [v['id'] for v in nodes if v['id'] in needed]
    assert names == meta['live_nodes']
    live_index = {v:i for i,v in enumerate(names)}
    mask = lambda xs: sum(1 << live_index[x] for x in xs if x in live_index)
    children = [sum(1 << j for j,v in enumerate(nodes) if a['id'] in v['deps']) for a in nodes]
    full = (1 << len(nodes)) - 1
    ideals = [d for d in range(full + 1) if all(not(d >> i & 1) or d & children[i] == children[i] for i in range(len(nodes)))]
    assert ideals == meta['done_masks']
    done_index = {d:i for i,d in enumerate(ideals)}
    width = 1 << len(names)
    assert width == meta['row_width']
    unit = math.gcd(*(v['cost'] for v in nodes))
    assert unit == meta['cost_unit']
    values = read_array(meta_path.parent / meta['binary_file'], meta)
    assert len(values) == width * len(ideals)
    memory = [sum(v['bytes'] for v in graph['inputs'])] * width
    for live in range(1, width):
        bit = live & -live
        memory[live] = memory[live ^ bit] + nodes[index[names[bit.bit_length()-1]]]['bytes']
    reverse = [[] for _ in values]
    goals = []
    finite = edges = 0
    for row, done in enumerate(ideals):
        for live in range(width):
            at = row * width + live
            value = values[at]
            if memory[live] > meta['cap_bytes']:
                assert value == INF
                continue
            finite += value != INF
            if done == full:
                assert value == 0
                goals.append(at)
            moves = []
            for i,name in enumerate(names):
                bit = 1 << i
                node = nodes[index[name]]
                if live & bit:
                    moves.append((row * width + (live ^ bit), 0))
                elif node['recomputable'] and live & mask(node['deps']) == mask(node['deps']) and memory[live | bit] <= meta['cap_bytes']:
                    moves.append((row * width + (live | bit), node['cost'] // unit))
            for i,node in enumerate(nodes):
                if not(done >> i & 1) and done & children[i] == children[i] and live & mask(node['backward_requires']) == mask(node['backward_requires']):
                    moves.append((done_index[done | (1 << i)] * width + live, 0))
            for target, cost in moves:
                edges += 1
                if values[target] == INF:
                    continue
                assert value != INF and value <= cost + values[target]
                if value == cost + values[target]:
                    reverse[target].append(at)
    tight_paths(values, reverse, goals, finite)
    return dict(valid_states=finite, edges=edges)

def audit_demand(meta_path, frozen):
    meta = load(meta_path)
    graph = graph_fields(meta, frozen)
    nodes = graph['nodes']
    index = {v['id']:i for i,v in enumerate(nodes)}
    width = 1 << len(nodes)
    assert width == meta['row_width']
    assert meta['live_nodes'] == [v['id'] for v in nodes]
    unit = math.gcd(*(v['cost'] for v in nodes))
    assert unit == meta['cost_unit']
    values = read_array(meta_path.parent / meta['binary_file'], meta)
    assert len(values) == width
    back_meta_path = meta_path.parent / meta['backward_metadata']
    back_meta = load(back_meta_path)
    assert back_meta['local_graph_sha256'] == meta['local_graph_sha256']
    assert back_meta['cap_bytes'] == meta['cap_bytes']
    assert back_meta['cost_unit'] == unit
    back = read_array(back_meta_path.parent / back_meta['binary_file'], back_meta)
    back_index = {name:i for i,name in enumerate(back_meta['live_nodes'])}
    base = back_meta['done_masks'].index(0) * back_meta['row_width']
    mask = lambda xs: sum(1 << index[x] for x in xs if x in index)
    output = mask(graph['outputs'])
    deps = [mask(v['deps']) for v in nodes]
    memory = [sum(v['bytes'] for v in graph['inputs'])] * width
    for live in range(1, width):
        bit = live & -live
        memory[live] = memory[live ^ bit] + nodes[bit.bit_length()-1]['bytes']
    reverse = [[] for _ in values]
    goals = []
    finite = edges = 0
    for live, value in enumerate(values):
        if memory[live] > meta['cap_bytes']:
            assert value == INF
            continue
        finite += value != INF
        if live & output == output:
            projected = sum(1 << back_index[v['id']] for i,v in enumerate(nodes) if live >> i & 1 and v['id'] in back_index)
            assert value == back[base + projected]
            if value != INF:
                goals.append(live)
        for i,node in enumerate(nodes):
            bit = 1 << i
            if live & bit:
                target, cost = live ^ bit, 0
            elif node['recomputable'] and live & deps[i] == deps[i] and memory[live | bit] <= meta['cap_bytes']:
                target, cost = live | bit, node['cost'] // unit
            else:
                continue
            edges += 1
            if values[target] == INF:
                continue
            assert value != INF and value <= cost + values[target]
            if value == cost + values[target]:
                reverse[target].append(live)
    tight_paths(values, reverse, goals, finite)
    return dict(valid_states=finite, edges=edges)


read=read_array
def audit_terminal(mp,frozen):
 meta=load(mp);g=meta['local_graph'];assert digest(g)==meta['local_graph_sha256'] and digest(frozen)==meta['full_graph_sha256'];assert g['nodes']==frozen['nodes'][:14] and g['inputs']==frozen['inputs'] and g['outputs']==['b0_residual2'];ns=g['nodes'];idx={v['id']:i for i,v in enumerate(ns)};width=meta['row_width'];assert width==8192 and meta['live_nodes']==[v['id'] for v in ns[:13]] and meta['phases']==[dict(down_seen=False,output_seen=False),dict(down_seen=True,output_seen=False)];cu=math.gcd(*(v['cost'] for v in ns));assert cu==meta['cost_unit'];a=read(mp.parent/meta['binary_file'],meta);assert len(a)==2*width;cap=meta['cap_bytes'];mask=lambda names:sum(1<<idx[x] for x in names if x in idx);dep=[mask(v['deps']) for v in ns];bpath=mp.parent/meta['backward_metadata'];bm=load(bpath);assert bm['cap_bytes']==cap and bm['local_graph_sha256']==meta['local_graph_sha256'] and bm['cost_unit']==cu;b=read(bpath.parent/bm['binary_file'],bm);zero=bm['done_masks'].index(0)*bm['row_width'];INF=(1<<32)-1;mem=[sum(v['bytes'] for v in g['inputs'])]*width
 for live in range(1,width):bit=live&-live;mem[live]=mem[live^bit]+ns[bit.bit_length()-1]['bytes']
 pred=[[] for _ in a];goals=[];finite=edges=0
 for phase in [0,1]:
  for live in range(width):
   at=phase*width+live;value=a[at]
   if mem[live]>cap or (phase==0 and live>>12&1):assert value==INF;continue
   finite+=value!=INF
   if phase==1 and live&dep[13]==dep[13] and mem[live]+ns[13]['bytes']<=cap:
    terminal=b[zero+(live&4095)]
    if terminal!=INF:
     assert value!=INF and value<=terminal
     if value==terminal:goals.append(at)
   for i,v in enumerate(ns[:13]):
    bit=1<<i
    if live&bit:nxt=phase*width+(live^bit);cost=0
    elif v['recomputable'] and live&dep[i]==dep[i] and mem[live|bit]<=cap:
     newphase=1 if i==12 else phase;nxt=newphase*width+(live|bit);cost=0 if i==12 and phase==0 else v['cost']//cu
    else:continue
    edges+=1;target=a[nxt]
    if target==INF:continue
    assert value!=INF and value<=cost+target,(phase,live,i,value,cost,target)
    if value==cost+target:pred[nxt].append(at)
 good=bytearray(len(a));queue=deque(goals)
 for at in goals:good[at]=1
 while queue:
  at=queue.popleft()
  for prev in pred[at]:
   if not good[prev]:good[prev]=1;queue.append(prev)
 assert sum(good)==finite
 return dict(valid_states=finite,edges=edges,tight_goal_states=len(goals))
