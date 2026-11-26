from django.db.models import Count, Max, Min, Sum
from django.utils import timezone

from apps.accounts.models import Organization
from apps.core.middleware import suspend_audit
from apps.core.utils import mask_identifier
from apps.transactions.models import TransactionRelationship


def build_graph(organization, days=30, min_amount=0, limit=500):
    if isinstance(organization, int):
        organization = Organization.objects.get(pk=organization)
    cutoff = timezone.now() - timezone.timedelta(days=days)
    transactions = list(
        organization.transactions.filter(timestamp__gte=cutoff, amount__gte=min_amount)
        .select_related("account", "risk_score")
        .order_by("-timestamp")[:limit]
    )
    nodes = {}
    edges = {}
    counterparties = {}
    for transaction in transactions:
        source = transaction.account.account_number
        target = transaction.counterparty_reference or "unknown-counterparty"
        risk = transaction.risk_score.risk_score if hasattr(transaction, "risk_score") else 0
        nodes.setdefault(
            source,
            {
                "id": source,
                "label": f"ACC {source[-4:]}",
                "kind": "account",
                "risk": risk,
                "transactions": 0,
            },
        )
        if target not in nodes:
            nodes[target] = {
                "id": target,
                "label": f"CP {target[-4:]}",
                "kind": "counterparty",
                "risk": 0,
                "transactions": 0,
            }
            counterparties[target] = 0
        nodes[source]["transactions"] += 1
        nodes[target]["transactions"] += 1
        nodes[target]["risk"] = max(nodes[target]["risk"], risk)
        counterparties[target] += 1
        key = tuple(sorted((source, target)))
        if key not in edges:
            edges[key] = {
                "source": source,
                "target": target,
                "value": 0.0,
                "count": 0,
                "types": set(),
            }
        edges[key]["value"] += float(transaction.amount)
        edges[key]["count"] += 1
        edges[key]["types"].add(transaction.transaction_type)

    for node in nodes.values():
        if node["kind"] == "counterparty" and counterparties.get(node["id"], 0) > 1:
            node["kind"] = "cluster"
    edge_list = []
    for edge in edges.values():
        edge["types"] = sorted(edge["types"])
        edge["value"] = round(edge["value"], 2)
        edge_list.append(edge)

    positions = {}
    try:
        import networkx as nx

        network = nx.Graph()
        network.add_nodes_from(nodes.keys())
        network.add_edges_from((edge["source"], edge["target"]) for edge in edge_list)
        layout = nx.spring_layout(network, seed=42) if network.number_of_nodes() else {}
        positions = {key: {"x": float(value[0]), "y": float(value[1]), "z": 0.0} for key, value in layout.items()}
    except ImportError:
        for index, key in enumerate(nodes.keys()):
            positions[key] = {"x": float(index), "y": 0.0, "z": 0.0}

    for node in nodes.values():
        node["position"] = positions.get(node["id"], {"x": 0.0, "y": 0.0, "z": 0.0})

    return {
        "graph": {
            "nodes": list(nodes.values()),
            "edges": edge_list,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edge_list),
                "transaction_count": len(transactions),
                "total_value": round(sum(edge["value"] for edge in edge_list), 2),
            },
        },
        "generated_at": timezone.now().isoformat(),
    }


def detect_clusters(organization, days=30, min_amount=0):
    if isinstance(organization, int):
        organization = Organization.objects.get(pk=organization)
    graph = build_graph(organization, days=days, min_amount=min_amount, limit=1000)["graph"]
    try:
        import networkx as nx
    except ImportError:
        return {"clusters": [], "reason": "networkx unavailable"}
    network = nx.Graph()
    for node in graph["nodes"]:
        network.add_node(node["id"], **node)
    for edge in graph["edges"]:
        network.add_edge(edge["source"], edge["target"], weight=edge["value"])
    clusters = []
    for index, component in enumerate(sorted(nx.connected_components(network), key=len, reverse=True), start=1):
        if len(component) < 2:
            continue
        subgraph = network.subgraph(component)
        members = list(component)
        total_value = round(sum(float(data.get("weight", 0)) for _, _, data in subgraph.edges(data=True)), 2)
        degrees = dict(subgraph.degree())
        hubs = sorted(degrees.items(), key=lambda item: item[1], reverse=True)[:3]
        suspect_scores = [network.nodes[node].get("risk", 0) for node in members]
        clusters.append(
            {
                "id": f"cluster-{index}",
                "member_count": len(members),
                "edge_count": subgraph.number_of_edges(),
                "total_value": total_value,
                "average_risk": round(sum(suspect_scores) / len(suspect_scores), 2),
                "hubs": [
                    {"id": node, "label": network.nodes[node].get("label", ""), "degree": degree}
                    for node, degree in hubs
                ],
                "members": [
                    {"id": node, "label": network.nodes[node].get("label", "")}
                    for node in members[:20]
                ],
            }
        )
    return {"clusters": clusters[:25]}


def sync_transaction_relationships(organization):
    if isinstance(organization, int):
        organization = Organization.objects.get(pk=organization)
    account_numbers = set(organization.financial_accounts.values_list("account_number", flat=True))
    rows = list(
        organization.transactions.values("account__account_number", "counterparty_reference")
        .annotate(
            transaction_count=Count("id"),
            total_amount=Sum("amount"),
            first_seen=Min("timestamp"),
            last_seen=Max("timestamp"),
        )
    )
    account_map = {item.account_number: item for item in organization.financial_accounts.all()}
    with suspend_audit():
        for row in rows:
            source = row["account__account_number"]
            target = row["counterparty_reference"] or "unknown-counterparty"
            relationship_type = "sequence" if target in account_numbers else "direct"
            TransactionRelationship.objects.update_or_create(
                organization=organization,
                source_identifier=source,
                target_identifier=target,
                relationship_type=relationship_type,
                defaults={
                    "source_account": account_map.get(source),
                    "target_account": account_map.get(target),
                    "transaction_count": row["transaction_count"],
                    "total_amount": row["total_amount"] or 0,
                    "first_seen": row["first_seen"],
                    "last_seen": row["last_seen"],
                    "evidence": {"generated_from": "transactions", "synthetic_safe": True},
                },
            )
    return TransactionRelationship.objects.filter(organization=organization).count()


def graph_payload(organization, days=30, min_amount=0, limit=500):
    return build_graph(organization, days=days, min_amount=min_amount, limit=limit)


def cluster_payload(organization, days=30, min_amount=0):
    return detect_clusters(organization, days=days, min_amount=min_amount)


def path_payload(organization, source, target):
    graph = build_graph(organization, days=365, min_amount=0, limit=1000)["graph"]
    try:
        import networkx as nx
    except ImportError:
        return {"found": False, "path": [], "reason": "networkx unavailable"}
    network = nx.Graph()
    for node in graph["nodes"]:
        network.add_node(node["id"], label=node.get("label"))
    for edge in graph["edges"]:
        network.add_edge(edge["source"], edge["target"], weight=edge.get("value", 0))
    try:
        path = nx.shortest_path(network, source, target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return {"found": False, "path": [], "source": source, "target": target}
    return {"found": True, "path": path, "length": len(path) - 1}


def masked_label(value):
    return mask_identifier(value)
