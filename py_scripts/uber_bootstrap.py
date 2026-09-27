### ---------------------
# Uber index: bootstrap significance test between 2 texts.
# Computes U for each text, then resamples the tokens many times to get a distribution of U -> confidence intervals + p-value for the difference.
### ---------------------

import re
import math
import sys
import numpy as np
from collections import Counter


### ---------------------
# 1. TOKENISATION
### ---------------------

def tokenize(text: str) -> list[str]:
    # Lowercase + word tokens. Keeps apostrophes and hyphens inside words. Accented letters handled just in case.
    return re.findall(r"\b[a-zA-ZÀ-ÿ''\-]+\b", text.lower())


### ---------------------
# 2. UBER INDEX
### ---------------------

def uber_index(tokens: list[str]) -> float:
    # U = (log T)^2 / (log T - log V), T = tokens, V = types.
    # WARNING: log base 10 here, not ln like other scripts -> the values are NOT on the same scale as corpus-profile-maker / helper_v3.
    T = len(tokens)
    V = len(set(tokens))
    if T == 0 or V == 0:
        raise ValueError("Empty token list.")
    logT = math.log10(T)
    logV = math.log10(V)
    if logT == logV:
        raise ValueError("log T == log V: U is undefined (all tokens are unique).")
    return (logT ** 2) / (logT - logV)


### ---------------------
# 3. BOOTSTRAP
### ---------------------

def bootstrap_uber(tokens: list[str], n_iter: int = 10_000, seed: int = 42) -> np.ndarray:
    # Draw T tokens WITH replacement, n_iter times, and compute U each time.
    # The array of U values = the sampling distribution of U for this text.
    # Fixed seed (42) so the results are reproducible from one run to the next.
    np.random.seed(seed)
    T = len(tokens)
    arr = np.array(tokens)
    results = []

    for _ in range(n_iter):
        sample = np.random.choice(arr, size=T, replace=True)
        t = len(sample)
        v = len(set(sample))
        logT = math.log10(t)
        logV = math.log10(v)
        if logT != logV:
            results.append((logT ** 2) / (logT - logV))

    return np.array(results)


### ---------------------
# 4. REPORT (one text)
### ---------------------

def report(label: str, tokens: list[str], boot: np.ndarray) -> None:
    u_obs = uber_index(tokens)
    print(f"\n{label}")
    print(f"  Tokens  : {len(tokens):,}")
    print(f"  Types   : {len(set(tokens)):,}")
    print(f"  U (obs) : {u_obs:.4f}")
    print(f"  U (boot): {np.mean(boot):.4f} ± {np.std(boot):.4f}")
    ### 95% CI = 2.5th and 97.5th percentiles of the bootstrap distribution.
    print(f"  95% CI  : [{np.percentile(boot, 2.5):.4f}, {np.percentile(boot, 97.5):.4f}]")


### ---------------------
# 5. MAIN
### ---------------------

def main():
    if len(sys.argv) != 3:
        print("Usage: python uber_bootstrap.py <text1> <text2>")
        sys.exit(1)

    paths = sys.argv[1], sys.argv[2]
    texts = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            texts.append(f.read())

    tokens1 = tokenize(texts[0])
    tokens2 = tokenize(texts[1])

    # 10,000 iterations: slow on long texts, but stable CIs.
    N_BOOT = 10_000
    print(f"\nRunning {N_BOOT:,} bootstrap iterations per text...")
    boot1 = bootstrap_uber(tokens1, N_BOOT)
    boot2 = bootstrap_uber(tokens2, N_BOOT)

    print("\n" + "=" * 50)
    print("UBER INDEX — BOOTSTRAP RESULTS")
    print("=" * 50)

    report("Text 1 — " + paths[0], tokens1, boot1)
    report("Text 2 — " + paths[1], tokens2, boot2)

    # Difference test. ONE-TAILED: H0 = text 2 is not richer than text 1.
    # p = share of bootstrap differences <= 0.
    # -> the order of the two files matters: put the one expected to be richer second.
    obs_diff  = uber_index(tokens2) - uber_index(tokens1)
    boot_diff = boot2 - boot1
    p_val     = np.mean(boot_diff <= 0)   # one-tailed: H0 = Text2 <= Text1

    print("\n--- Difference (Text 2 − Text 1) ---")
    print(f"  Observed diff : {obs_diff:.4f}")
    print(f"  Bootstrap diff: {np.mean(boot_diff):.4f} ± {np.std(boot_diff):.4f}")
    print(f"  95% CI        : [{np.percentile(boot_diff, 2.5):.4f}, {np.percentile(boot_diff, 97.5):.4f}]")
    print(f"  p-value (H0: T2 ≤ T1): {p_val:.4f}")

    if p_val < 0.001:
        verdict = "SIGNIFICANT (p < 0.001)"
    elif p_val < 0.05:
        verdict = f"SIGNIFICANT (p = {p_val:.4f})"
    else:
        verdict = f"NOT significant (p = {p_val:.4f})"

    print(f"\n  Verdict: {verdict}")
    print("=" * 50)


if __name__ == "__main__":
    main()
