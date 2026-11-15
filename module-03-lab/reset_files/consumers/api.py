"""Consumer 3: the metrics API. It passes every request to the semantic layer and adds nothing of its own."""
from semantic_layer import query


def get_metric(metric, start, end, where=None, user="finance"):
    """start is inclusive and end is exclusive, as everywhere in the semantic layer."""
    rows = query([metric], start=start, end=end, where=where, user=user, definition=1)
    return rows[0][metric] if rows else 0
