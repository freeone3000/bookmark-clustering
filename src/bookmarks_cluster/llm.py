def load():
    import subprocess
    proc = subprocess.Popen(["lms", "load", "lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-MLX-8bit", "--context", "10240"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    proc.wait()