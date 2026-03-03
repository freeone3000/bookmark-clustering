from typing import NamedTuple

import numpy as np
from scipy.sparse.csgraph import laplacian
from sklearn.metrics.pairwise import rbf_kernel

from .bookmark_types import Bookmark
from .embed import EmbeddingSet
from sklearn.cluster import SpectralClustering


class Cluster(NamedTuple):
    bookmarks: list[Bookmark]
    label: str

Clustering = list[Cluster]


def cluster(embed_set: EmbeddingSet, min_bound: int = 15, max_bound: int = 70) -> Clustering:
    # sklearn spectral clustering requires us to know the number of clusters ahead of time
    # so we first, from StackOverflow, "look at the eigenvalues of the graph Laplacian and chose the K corresponding to the maximum drop-off."
    # we calculate this by finding our pairwise distance metric, which gives us our graph in Hilbert space
    # then we can get our graph laplacian, calculate the eigenvalues, and find the max drop-off to determine K

    # get the differences between the eigenvalues, and sort them in descending order
    embeddings = np.stack(embed_set.embeddings)
    rbf = rbf_kernel(embeddings, gamma=0.5)
    L = laplacian(rbf, normed=True)
    eigen = np.linalg.eigh(L)
    diff = np.diff(eigen[0])

    # find the first one between our bounds and use that as our K for spectral clustering
    sort_desc = np.flip(np.argsort(diff)) + 1
    mask = np.greater_equal(sort_desc, np.full_like(sort_desc, min_bound)) & \
           np.less_equal(sort_desc, np.full_like(sort_desc, max_bound))
    num_clusters = sort_desc[mask][0]

    # find our actual fit clusters
    sc = SpectralClustering(affinity='precomputed', n_clusters=num_clusters)
    actual_fit = sc.fit_predict(rbf)

    # Find the representative point for each cluster by minimizing least-squares distance in RBF space
    # For each cluster, find the point that minimizes sum of squared distances to all other points
    closest_indices = []
    for cluster_id in range(num_clusters):
        cluster_mask = actual_fit == cluster_id
        cluster_points = embeddings[cluster_mask]

        # Compute pairwise RBF distances within the cluster
        cluster_rbf = rbf_kernel(cluster_points, gamma=0.5)

        # For each point in the cluster, compute sum of squared distances to all others
        # In RBF space, distance ~= sqrt(2 - 2*similarity), but minimizing sum of similarities
        # is equivalent to minimizing sum of squared distances
        sum_similarities = np.sum(cluster_rbf, axis=1)

        # The point that maximizes sum of similarities minimizes sum of squared distances
        best_local_idx = np.argmax(sum_similarities)

        # Convert local index back to global index
        global_idx = np.where(cluster_mask)[0][best_local_idx]
        closest_indices.append(global_idx)

    # construct our final clusters with the representative point as the label
    clusters = []
    for cluster_id in range(num_clusters):
        cluster_mask = actual_fit == cluster_id
        cluster_bookmarks = [Bookmark(guid='', url=embed_set.urls[i], title=embed_set.titles[i], content=None) for i in np.where(cluster_mask)[0]]
        label = embed_set.titles[closest_indices[cluster_id]]
        clusters.append(Cluster(cluster_bookmarks, label))
    return clusters


def print_clusters_tree(clustering: Clustering) -> str:
    """Pretty-print clusters as a tree structure.

    Args:
        clustering: List of Cluster objects to display

    Returns:
        A formatted string representing the cluster tree
    """
    lines = []

    for cluster_idx, cluster in enumerate(clustering):
        # Add cluster as root node
        is_last_cluster = cluster_idx == len(clustering) - 1
        cluster_prefix = "└── " if is_last_cluster else "├── "
        lines.append(f"{cluster_prefix}Cluster: {cluster.label} ({len(cluster.bookmarks)} bookmarks)")

        # Add bookmarks as children
        for bookmark_idx, bookmark in enumerate(cluster.bookmarks):
            is_last_bookmark = bookmark_idx == len(cluster.bookmarks) - 1

            if is_last_cluster:
                bookmark_prefix = "    " if is_last_bookmark else "    "
            else:
                bookmark_prefix = "│   " if not is_last_bookmark else "    "

            connector = "└── " if is_last_bookmark else "├── "
            lines.append(f"{bookmark_prefix}{connector}{bookmark.title}")
            lines.append(f"{bookmark_prefix}    └── {bookmark.url}")

    return "\n".join(lines)
