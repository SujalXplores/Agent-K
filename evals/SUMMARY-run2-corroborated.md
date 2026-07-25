# Evaluation results

Runs: 12  |  graded: 12  |  uncontaminated: 9

- Correct diagnosis (all graded): **5/12**
- Correct diagnosis (uncontaminated only): **3/9**
- Verdict as expected: **10/12**

| Scenario | Run | Diagnosed | Correct | Verdict | Expected | Tokens | Time (s) | Flags |
|---|---|---|---|---|---|---|---|---|
| retrieval_latency | 1 | retry_storm | NO | denied | denied | 824 | 1.7 | - |
| retrieval_latency | 2 | retry_storm | NO | denied | denied | 1242 | 2.9 | - |
| retrieval_latency | 3 | retry_storm | NO | denied | denied | 895 | 2.7 | - |
| db_pool_exhaustion | 1 | retrieval_latency | NO | denied | denied | 759 | 2.2 | - |
| db_pool_exhaustion | 2 | db_pool_exhaustion | yes | denied | denied | 879 | 3.0 | - |
| db_pool_exhaustion | 3 | None | NO | denied | denied | 872 | 1.1 | - |
| prompt_regression | 1 | prompt_regression | yes | approved | approved | 815 | 1.8 | - |
| prompt_regression | 2 | prompt_regression | yes | approved | approved | 921 | 1.3 | - |
| prompt_regression | 3 | retry_storm | NO | denied | approved | 922 | 2.5 | - |
| retry_storm | 1 | None | NO | denied | approved | 658 | 1.1 | contaminated? |
| retry_storm | 2 | retry_storm | yes | approved | approved | 907 | 0.9 | contaminated? |
| retry_storm | 3 | retry_storm | yes | approved | approved | 934 | 6.8 | contaminated? |
