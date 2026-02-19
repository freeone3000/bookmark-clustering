import sklearn

from .embed import EmbeddingSet

Clustering = str # placeholder

def cluster(embeddings: EmbeddingSet) -> Clustering:
    # sklearn spectral clustering requires us to know the number of clusters ahead of time
    # so we first, from StackOverflow, "look at the eigenvalues of the graph Laplacian and chose the K corresponding to the maximum drop-off."
    # we calculate this by finding our pairwise distance metric, which gives us our graph in Hilbert space
    # then we can get our graph laplacian, ... (knowledge gap here) calculate the eigenvalues, and find the max drop-off to determine K

    pass