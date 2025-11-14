import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def detect_layout(blocks: list) -> dict:
    """
    Applies KMeans clustering on x-coordinates to detect 1, 2, or 3-column layouts.
    This works best with the 'LTTextBox' blocks from pdfminer.
    """
    if not blocks:
        return {"columns": 1, "column_centers": []}

    # Use the starting x-coordinate of each block
    x_coords = np.array([[b['x0']] for b in blocks])

    if len(x_coords) < 3: # Not enough data to cluster
         return {"columns": 1, "column_centers": [np.mean(x_coords)]}

    scores = {}
    models = {}

    # Test for 1, 2, and 3 columns
    for n_clusters in range(1, 4):
        # KMeans requires at least as many samples as clusters
        if len(x_coords) < n_clusters:
            continue
        
        if n_clusters == 1:
            scores[1] = 1.0 # Base score for 1 cluster
            models[1] = KMeans(n_clusters=1, n_init=10).fit(x_coords)
            continue

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit(x_coords)
        # Silhouette score requires at least 2 clusters
        score = silhouette_score(x_coords, kmeans.labels_)
        scores[n_clusters] = score
        models[n_clusters] = kmeans
        
    # Best score wins
    best_n = max(scores, key=scores.get)
    best_model = models[best_n]
    
    # Get the x-coordinate of each column center
    centers = sorted(best_model.cluster_centers_.flatten().tolist())
    
    return {"columns": best_n, "column_centers": centers, "labels": best_model.labels_.tolist()}