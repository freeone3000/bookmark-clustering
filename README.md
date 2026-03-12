## Inspiration
Based off of [Gabriella's work on browsing code by meaning](https://haskellforall.com/2026/02/browse-code-by-meaning),
this attempts to cluster firefox bookmarks by determining site content. LLMs are used for classification and summarization,
with spectral clustering being used to categorize.

## Requirements
- Python >= 3.11
- LM Studio with `jina-embeddings-v5-text-small-clustering` installed as a Text Embedding model
- LM Studio with `qwen/qwen3-vl-8b` installed as a Large Language Model
- Bookmarks in Firefox. Will load from your default profile.

## Usage

Run the following command:
```
python main.py
```

This will output to `output/bookmarks_clustered.html`. This can then be imported back into firefox.

## Notes
This currently generates an *exemplar* data point. Outputting embeddings based on the centroid is later work.
(It will likely involve using in-process Qwen3 rather than remote.)

Look at https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct for transformer-based arch