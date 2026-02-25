import sklearn
import numpy as np

from .embed import EmbeddingSet

Clustering = str # placeholder

def cluster(embeddings: EmbeddingSet) -> Clustering:
    # sklearn spectral clustering requires us to know the number of clusters ahead of time
    # so we first, from StackOverflow, "look at the eigenvalues of the graph Laplacian and chose the K corresponding to the maximum drop-off."
    # we calculate this by finding our pairwise distance metric, which gives us our graph in Hilbert space
    # then we can get our graph laplacian, ... (knowledge gap here) calculate the eigenvalues, and find the max drop-off to determine K

    # if we use cosine similarity as our graph weights, we now have a graph in Hilbert space
    graph_weights = sklearn.metrics.pairwise.cosine_similarity(embeddings.embeddings)
    # where we can then tak the graph Laplacian
    graph_laplacian = sklearn.graph.laplacian(graph_weights, normed=True)
    # pairwise cosine is symmetric, so we can use eigh to get eigenvalues, which gives us sorted results
    eigenvalues, _ = np.linalg.eigh(graph_laplacian)

