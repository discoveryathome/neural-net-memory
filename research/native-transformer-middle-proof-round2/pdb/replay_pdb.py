"""Regenerate and independently audit transformer pattern databases.

Only dependencies: Python standard library, sibling generators, and the frozen
repository verifier. Run with --repo REPO --out SCRATCH [--cap-units 10].
Tables are generated artifacts and need not be committed.
"""
from array import array
from collections import deque
from pathlib import Path
import argparse
import copy
import hashlib
import heapq
import json
import math
import random
import sys
import tempfile

INF = (1 << 32) - 1
FULL_SHA = '7d60aaf32c25d4d000872f9d317cdb0cbc71c929307eb69faf7e974c795d5854'
BACK_HASH = {10:'5a66a501384823793f9afb4529f7619465e199f869dd6ab98dec1d537c107a76',11:'e48ed0271ffbd28b5c267591fca82eeaeec06b1a696911c747ddaa05a559566b',12:'a4fcff1b2db6d60bc0e37ad7212e9ddbf7c1b64bbcc2c03efe542e6ad523acd9',13:'2566df7c876c48c7b8aa4699d9e6e7664943d89ac0ee7c2171fb5fb25d88ac90'}
DEMAND_HASH = {10:'676dc852e9abf92a460760763df6f4e33551eab7fa769244937ccbd3a39f79bc',11:'2d76ddd1dc9ba7099408673d2d329a808390d43d9b5ca593f7b8bbbf0a40bc09',12:'7eba73845111f3fa98d6a76232cb155341e608ac42f8cdfd3c2792675a81c722',13:'fa680180039378bea727097b952fff65fb1db1a2158295524b8609beff10b39e'}

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

def direct(graph, cap, names, demand):
    """Independent forward Dijkstra on all14 live bits and all14 done bits."""
    nodes = graph['nodes']
    index = {v['id']:i for i,v in enumerate(nodes)}
    mask = lambda xs: sum(1 << index[x] for x in xs if x in index)
    deps = [mask(v['deps']) for v in nodes]
    req = [mask(v['backward_requires']) for v in nodes]
    children = [sum(1 << j for j,v in enumerate(nodes) if a['id'] in v['deps']) for a in nodes]
    full = (1 << len(nodes)) - 1
    output = mask(graph['outputs'])
    memory = [sum(v['bytes'] for v in graph['inputs'])] * (full + 1)
    for live in range(1, full + 1):
        bit = live & -live
        memory[live] = memory[live ^ bit] + nodes[bit.bit_length()-1]['bytes']
    initial = (mask(names), 0, not demand)
    assert memory[initial[0]] <= cap
    best = {initial:0}
    queue = [(0,*initial)]
    expanded = 0
    while queue:
        cost, live, done, phase = heapq.heappop(queue)
        if best[live,done,phase] != cost:
            continue
        expanded += 1
        if expanded > 250000:
            raise RuntimeError('direct control state limit, no proof claim')
        if phase and done == full:
            return cost
        moves = []
        if not phase and live & output == output:
            moves.append(((live,done,True),0))
        for i,node in enumerate(nodes):
            bit = 1 << i
            if live & bit:
                moves.append(((live ^ bit,done,phase),0))
            elif node['recomputable'] and live & deps[i] == deps[i] and memory[live | bit] <= cap:
                moves.append(((live | bit,done,phase),node['cost']))
            if phase and not(done & bit) and done & children[i] == children[i] and live & req[i] == req[i]:
                moves.append(((live,done | bit,phase),0))
        for target, extra in moves:
            value = cost + extra
            if value < best.get(target,10**100):
                best[target] = value
                heapq.heappush(queue,(value,*target))
    return None

def negative_controls(meta_path, frozen, demand):
    base = load(meta_path)
    original = read_array(meta_path.parent / base['binary_file'], base)
    kinds = ['overstated','understated','wrong_terminal','invalid_memory','wrong_local_hash','wrong_full_hash','rehashed_wrong_cost']
    kinds += ['wrong_backward_cap'] if demand else ['missing_ideal','missing_live_node']
    with tempfile.TemporaryDirectory(prefix='pdb-neg-',dir=meta_path.parent) as temp:
        root = Path(temp)
        if demand:
            bpath = meta_path.parent / base['backward_metadata']
            back = load(bpath)
            (root / bpath.name).write_text(json.dumps(back))
            (root / back['binary_file']).write_bytes((bpath.parent / back['binary_file']).read_bytes())
        for kind in kinds:
            meta = copy.deepcopy(base)
            values = array('I',original)
            if kind == 'overstated':values[0] += 1
            if kind == 'understated':values[0] -= 1
            if kind == 'wrong_terminal':values[1 << 13 if demand else meta['done_masks'].index((1 << 14)-1) * meta['row_width']] += 1
            if kind == 'invalid_memory':values[(1 << 14)-1 if demand else meta['row_width']-1] = 0
            if kind == 'wrong_local_hash':meta['local_graph_sha256'] = '0' * 64
            if kind == 'wrong_full_hash':meta['full_graph_sha256'] = '0' * 64
            if kind == 'rehashed_wrong_cost':
                meta['local_graph']['nodes'][1]['cost'] += 32768
                meta['local_graph_sha256'] = digest(meta['local_graph'])
            if kind == 'missing_ideal':meta['done_masks'] = meta['done_masks'][1:]
            if kind == 'missing_live_node':meta['live_nodes'] = meta['live_nodes'][1:]
            if kind == 'wrong_backward_cap':
                changed = copy.deepcopy(back)
                changed['cap_bytes'] += 131072
                name = 'wrong-cap.json'
                (root / name).write_text(json.dumps(changed))
                meta['backward_metadata'] = name
            if sys.byteorder != 'little':values.byteswap()
            raw = values.tobytes()
            meta['binary_file'] = kind + '.bin'
            meta['binary_sha256'] = hashlib.sha256(raw).hexdigest()
            (root / meta['binary_file']).write_bytes(raw)
            forged = root / (kind + '.json')
            forged.write_text(json.dumps(meta))
            try:
                (audit_demand if demand else audit_backward)(forged,frozen)
            except (AssertionError,ValueError,KeyError):
                continue
            raise AssertionError('accepted negative fixture ' + kind)
    return len(kinds)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--cap-units',type=int,choices=[10,11,12,13],default=10)
    args = parser.parse_args()
    sys.path.insert(0,str(args.repo.resolve()))
    global load, digest, validate_graph
    from verifier import load, digest, validate_graph
    from pattern_db import PatternDB
    from output_demand_db import OutputDemandDB
    frozen = load(args.repo / 'benchmarks/graphs/transformer-b4-t128.json')
    assert digest(frozen) == FULL_SHA
    graph = copy.deepcopy(frozen)
    graph['nodes'] = graph['nodes'][:14]
    graph['outputs'] = ['b0_residual2']
    graph['id'] = 'transformer-b4-t128-local-backward-pattern'
    args.out.mkdir(parents=True,exist_ok=True)
    cap = args.cap_units * graph['inputs'][0]['bytes']
    back = PatternDB(graph,cap).build(seconds=30,states=1000000)
    bp = args.out / f'b4-backward-pdb-cap{args.cap_units}.json'
    bm = back.write(bp,FULL_SHA)
    assert bm['binary_sha256'] == BACK_HASH[args.cap_units]
    demand = OutputDemandDB(graph,cap,back).build(seconds=30)
    dp = args.out / f'b4-output-demand-pdb-cap{args.cap_units}.json'
    dm = demand.write(dp,bp.name,FULL_SHA)
    assert dm['binary_sha256'] == DEMAND_HASH[args.cap_units]
    audits = dict(backward=audit_backward(bp,frozen),demand=audit_demand(dp,frozen))
    fixtures = [[],['b0_context'],['b0_residual1'],['b0_up','b0_gelu']]
    for names in fixtures:
        assert back.value(names) == direct(graph,cap,names,False)
        assert demand.value(names) == direct(graph,cap,names,True)
    negatives = dict(backward=negative_controls(bp,frozen,False),demand=negative_controls(dp,frozen,True))
    print(json.dumps(dict(status='PASS',cap_units=args.cap_units,full_graph_sha256=FULL_SHA,backward_binary_sha256=bm['binary_sha256'],demand_binary_sha256=dm['binary_sha256'],independent_audits=audits,direct_dijkstra_controls=8,negative_controls=negatives),sort_keys=True),flush=True)

if __name__ == '__main__':
    main()
