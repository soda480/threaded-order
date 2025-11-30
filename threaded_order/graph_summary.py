"""
Graph summary formatting helpers for threaded_order.

This module produces a human-readable summary of a DAGraph instance, used
by the CLI to display the dependency graph.
"""

def _graph_get_nodes_and_ids(dag):
    """ return a sorted list of node names and a stable numeric ID mapping.

        IDs are deterministic based on sorted node order.
        Returns:
            nodes: [name, ...]
            ids: {name: numeric_id}
    """
    nodes = sorted(dag.nodes())
    ids = {}
    for idx, name in enumerate(nodes):
        ids[name] = idx
    return nodes, ids

def _graph_build_indegree_and_adj(dag, nodes):
    """ build indegree table and adjacency (outgoing edges) table.

        Returns:
            indegree: {node: number_of_parents}
            adj:      {node: [sorted_child_nodes]}
            num_edges: total edge count
    """
    indegree = {}
    adj = {}
    num_edges = 0

    for name in nodes:
        parents = dag.parents_of(name)
        children = dag.children_of(name)

        indegree[name] = len(parents)
        children_sorted = sorted(children) if children else []
        adj[name] = children_sorted
        num_edges += len(children_sorted)

    return indegree, adj, num_edges

def _graph_find_roots_and_leaves(nodes, indegree, adj):
    """ identify root nodes (no parents) and leaf nodes (no children).

        Returns:
            roots: [node, ...]
            leaves: [node, ...]
    """
    roots = []
    leaves = []

    for name in nodes:
        if indegree[name] == 0:
            roots.append(name)
        if not adj[name]:
            leaves.append(name)

    return roots, leaves

def _graph_compute_levels(nodes, roots, indegree, adj, ids):
    """ compute topological levels using a Kahn-style layering algorithm.

        Each level contains nodes that can run in parallel after prior levels complete.

        Returns:
            levels: [ [node1, node2], [node3], ... ]
    """
    levels = []
    if not nodes:
        return levels

    indeg = {}
    for name, value in indegree.items():
        indeg[name] = value

    queue = sorted(roots, key=lambda n: ids[n])
    seen = set()

    while queue:
        level = []
        next_queue = []

        for name in queue:
            if name in seen:
                continue
            seen.add(name)
            level.append(name)

            for dst in adj[name]:
                indeg[dst] -= 1
                if indeg[dst] == 0:
                    next_queue.append(dst)

        if level:
            level.sort(key=lambda n: ids[n])  # noqa: E731
            levels.append(level)

        queue = sorted(next_queue, key=lambda n: ids[n])

    if not levels:
        levels = [nodes]

    return levels

def _graph_format_header(num_nodes, num_edges, roots, leaves, levels_count, ids):
    """ format the summary header section:
            Graph: X nodes, Y edges
            Roots: [id], [id], ...
            Leaves: [id], [id], ...
            Levels: Z
    """
    lines = []
    lines.append(f'Graph: {num_nodes} nodes, {num_edges} edges')

    if roots:
        root_ids = ', '.join(f'[{ids[name]}]' for name in roots)
        lines.append(f'Roots: {root_ids}')

    if leaves:
        leaf_ids = ', '.join(f'[{ids[name]}]' for name in leaves)
        lines.append(f'Leaves: {leaf_ids}')

    lines.append(f'Levels: {levels_count}')
    return lines

def _graph_format_nodes(nodes, ids):
    """ format the Nodes: section:
            [id] node_name
    """
    lines = ['Nodes:']
    for name in nodes:
        lines.append(f'  [{ids[name]}] {name}')
    return lines

def _graph_format_edges(nodes, adj, ids):
    """ format the Edges: section:
            [src_id] -> [child_id], ...
            or
            [src_id] -> (none)
    """
    lines = ['Edges:']
    for name in nodes:
        children = adj[name]
        if children:
            targets = ', '.join(f'[{ids[c]}]' for c in children)
        else:
            targets = '(none)'
        lines.append(f'  [{ids[name]}] -> {targets}')
    return lines

def format_graph_summary(dag):
    """ produce the full human-readable DAG summary used by the CLI.

        Example output:

            Graph: 18 nodes, 21 edges
            Roots: [0], [1]
            Leaves: [6], [7]
            Levels: 4

            Nodes:
            [0] tests/test_a.py::test_A
            ...

            Edges:
            [0] -> [2]
            ...

        Returns:
            A single string containing the formatted summary.
    """
    nodes, ids = _graph_get_nodes_and_ids(dag)

    if not nodes:
        return 'Graph: 0 nodes, 0 edges'

    indegree, adj, num_edges = _graph_build_indegree_and_adj(dag, nodes)
    roots, leaves = _graph_find_roots_and_leaves(nodes, indegree, adj)
    levels = _graph_compute_levels(nodes, roots, indegree, adj, ids)

    lines = []

    header_lines = _graph_format_header(
        num_nodes=len(nodes),
        num_edges=num_edges,
        roots=roots,
        leaves=leaves,
        levels_count=len(levels),
        ids=ids,
    )
    lines.extend(header_lines)
    lines.append('')

    lines.extend(_graph_format_nodes(nodes, ids))
    lines.append('')

    lines.extend(_graph_format_edges(nodes, adj, ids))

    return '\n'.join(lines)
