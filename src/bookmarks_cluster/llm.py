import subprocess

def load_summarize():
    # TODO actually math this context number
    subprocess.call(["lms", "load", "lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-MLX-8bit", "--context-length", "10240"])

def unload_summarize():
    subprocess.call(["lms", "unload", "lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-MLX-8bit"])

def load_embed():
    subprocess.call(["lms", "load", "Qwen/Qwen3-Embedding-8B-GGUF/Qwen3-Embedding-8B-Q4_K_M.gguf"])

def unload_embed():
    subprocess.call(["lms", "unload", "Qwen/Qwen3-Embedding-8B-GGUF/Qwen3-Embedding-8B-Q4_K_M.gguf"])