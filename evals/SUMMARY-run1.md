# Evaluation results

Runs: 12  |  graded: 12  |  uncontaminated: 9

- Correct diagnosis (all graded): **5/12**
- Correct diagnosis (uncontaminated only): **4/9**
- Verdict as expected: **7/12**

| Scenario | Run | Diagnosed | Correct | Verdict | Expected | Tokens | Time (s) | Flags |
|---|---|---|---|---|---|---|---|---|
| retrieval_latency | 1 | None | NO | denied | denied | 804 | 1.5 | - |
| retrieval_latency | 2 | retrieval_latency | yes | denied | denied | 899 | 1.1 | - |
| retrieval_latency | 3 | retrieval_latency | yes | denied | denied | 1212 | 2.9 | - |
| db_pool_exhaustion | 1 | None | NO | denied | denied | 638 | 8.8 | - |
| db_pool_exhaustion | 2 | retry_storm | NO | approved | denied | 1224 | 16.0 | - |
| db_pool_exhaustion | 3 | retry_storm | NO | approved | denied | 1218 | 1.5 | - |
| prompt_regression | 1 | None | NO | denied | approved | 971 | 2.2 | - |
| prompt_regression | 2 | prompt_regression | yes | approved | approved | 1209 | 1.8 | - |
| prompt_regression | 3 | prompt_regression | yes | approved | approved | 1238 | 3.6 | - |
| retry_storm | 1 | None | NO | denied | approved | 636 | 3.6 | contaminated? |
| retry_storm | 2 | None | NO | denied | approved | 878 | 1.6 | contaminated? |
| retry_storm | 3 | retry_storm | yes | approved | approved | 864 | 4.4 | contaminated? |
