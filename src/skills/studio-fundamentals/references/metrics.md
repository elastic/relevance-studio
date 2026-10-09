# Relevance metrics

Source of truth: `docs/docs/v1.2/guide/concepts.md`, Elasticsearch's
[Ranking Evaluation API](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval).
All four metrics are computed by that API for each benchmark's `task.k`.

- **NDCG** (Normalized Discounted Cumulative Gain) — measures how well the top `k` results
  are *ordered* by judged relevance, not just whether relevant docs appear. Rewards relevant
  documents ranked higher more than the same documents ranked lower. The best general-purpose
  metric for graded (non-binary) rating scales, since it uses the full rating value rather
  than a relevant/not-relevant cutoff.
- **Precision@k** — the fraction of the top `k` results that are judged relevant. Simple and
  intuitive, but ignores rank order within the top `k` and ignores rating gradation (treats a
  rating above the relevance threshold as binary "relevant").
- **Recall@k** — the fraction of *all* relevant documents (across the whole index, not just
  top `k`) that were retrieved in the top `k`. Useful when missing a relevant document is
  worse than ranking it lower; less useful when the judged pool is small or sparse.
- **MRR** (Mean Reciprocal Rank) — measures how early the *first* relevant document appears.
  Best for use cases with a single "right answer" (navigational search, known-item lookup),
  less informative when users expect multiple good results in a list.

## Choosing a metric

- Graded rating scale (0–4), general web/e-commerce search → **NDCG** as the headline metric.
- Binary rating scale, "did we find it" use cases → **Precision** or **MRR**.
- Concerned about missing relevant docs entirely (e.g. legal/compliance search) → **Recall**.
- Default (`task.metrics` unset) is `["ndcg", "precision", "recall"]` — report all three
  unless the user has a stated preference.

## Effect of unrated documents

Documents with no judgement are treated as not relevant by the Ranking Evaluation API, which
can understate a strategy's true performance if judgement coverage is incomplete. Always
report the unrated percentage alongside any metric and treat a high unrated % as a caveat on
confidence — see `judgement-gap-fill` and `evaluation-analysis` skills. As a rule of thumb,
treat unrated % above ~25% as low confidence and above ~50% as not yet meaningful.
