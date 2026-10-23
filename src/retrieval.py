"""Step 3: hybrid retrieval over the knowledge base (kb/*.md).

  chunking : one chunk per '## ' section, id = '<file>#<section-slug>'
  sparse   : BM25 (implemented here, ~25 lines)
  dense    : sentence-transformers if installed, else TF-IDF (word + char) cosine
  fusion   : Reciprocal Rank Fusion (RRF) of the two rankings
  routing  : optional intent hint from the classifier -> a 3rd ranking of the KB sections mapped
             to the predicted top-3 intents (eval/intent_to_kb.json), fused with RRF
  rerank   : optional cross-encoder if sentence-transformers is installed (USE_RERANKER=1)

Run:  python -m src.retrieval eval     # recall@k / MRR for bm25 vs dense vs hybrid
      python -m src.retrieval "my refund hasn't arrived"
"""
import json, math, os, re, sys
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from src.config import KB_DIR, ROOT, DATA_PROCESSED, REPORTS_DIR, RANDOM_STATE, DEMO_MODE

DENSE_MODEL = os.getenv("DENSE_MODEL", "BAAI/bge-small-en-v1.5")
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
TOKEN = re.compile(r"[a-z0-9]+")
STOP = set("a an the and or of to in on for is are be it i my me we you your our can do how what with "
           "this that at by from as was have has not no please hi hello".split())


def tokenize(text):
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


@dataclass
class Chunk:
    id: str
    title: str
    text: str


def load_chunks(kb_dir=KB_DIR):
    chunks = []
    for path in sorted(kb_dir.glob("*.md")):
        doc = path.read_text()
        title = re.search(r"^# (.+)$", doc, re.M).group(1)
        for sec in re.split(r"^## ", doc, flags=re.M)[1:]:
            head, _, body = sec.partition("\n")
            chunks.append(Chunk(f"{path.stem}#{slug(head)}", f"{title} - {head.strip()}", body.strip()))
    return chunks


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = [tokenize(d) for d in docs]
        self.k1, self.b = k1, b
        self.avgdl = np.mean([len(d) for d in self.docs])
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    def scores(self, query):
        q = tokenize(query)
        out = np.zeros(len(self.docs))
        for i, (tf, d) in enumerate(zip(self.tf, self.docs)):
            for t in q:
                if t in tf:
                    f = tf[t]
                    out[i] += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(d) / self.avgdl))
        return out


class Dense:
    def __init__(self, docs):
        try:
            if DEMO_MODE or os.getenv("RETRIEVAL_BACKEND", "auto") == "tfidf":
                raise ImportError("Explicit lightweight TF-IDF serving mode")
            from sentence_transformers import SentenceTransformer
            self.st, self.kind = SentenceTransformer(DENSE_MODEL), DENSE_MODEL
            self.V = self._norm(self.st.encode(docs, normalize_embeddings=True))
        except Exception:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.pipeline import make_union
            self.st, self.kind = None, "tfidf(word+char)"
            self.vec = make_union(TfidfVectorizer(sublinear_tf=True, stop_words="english"),
                                  TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True))
            self.V = self._norm(self.vec.fit_transform(docs).toarray())

    @staticmethod
    def _norm(v):
        v = np.asarray(v, dtype=np.float32)
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)

    def scores(self, query):
        q = self.st.encode([query], normalize_embeddings=True) if self.st else self.vec.transform([query]).toarray()
        return self.V @ self._norm(q)[0]


def rrf(rankings, k=60):
    fused = Counter()
    for r in rankings:
        for rank, idx in enumerate(r):
            fused[idx] += 1.0 / (k + rank + 1)
    return fused


class Retriever:
    def __init__(self, chunks=None):
        self.chunks = chunks or load_chunks()
        self.intent_map = json.loads((ROOT / "eval" / "intent_to_kb.json").read_text())
        self.pos = {c.id: i for i, c in enumerate(self.chunks)}
        texts = [f"{c.title}. {c.text}" for c in self.chunks]
        self.bm25, self.dense = BM25(texts), Dense(texts)
        self.reranker = None
        if not DEMO_MODE and os.getenv("RETRIEVAL_BACKEND", "auto") != "tfidf" and os.getenv("USE_RERANKER") == "1":
            try:
                from sentence_transformers import CrossEncoder
                self.reranker = CrossEncoder(RERANK_MODEL)
            except Exception:
                pass

    def _intent_ranking(self, intents):
        out = []
        for it in intents:
            for cid in self.intent_map.get(it, []):
                if cid in self.pos and self.pos[cid] not in out:
                    out.append(self.pos[cid])
        return out

    def search(self, query, k=3, mode="hybrid", intents=None):
        """intents: optional list of predicted intents (best first) used as a routing hint."""
        if mode == "bm25":
            s = self.bm25.scores(query); order = np.argsort(-s)
            scored = [(i, float(s[i])) for i in order]
        elif mode == "dense":
            s = self.dense.scores(query); order = np.argsort(-s)
            scored = [(i, float(s[i])) for i in order]
        else:
            rankings = [np.argsort(-self.bm25.scores(query)), np.argsort(-self.dense.scores(query))]
            if intents:
                rankings.append(self._intent_ranking(intents))
                rankings.append(self._intent_ranking(intents[:1]))   # extra weight for the top intent
            fused = rrf(rankings)
            scored = fused.most_common()
        if self.reranker is not None and mode == "hybrid":
            cand = [i for i, _ in scored[:10]]
            rs = self.reranker.predict([(query, self.chunks[i].text) for i in cand])
            scored = sorted(zip(cand, map(float, rs)), key=lambda x: -x[1])
        return [{"id": self.chunks[i].id, "title": self.chunks[i].title,
                 "text": self.chunks[i].text, "score": round(s, 4)} for i, s in scored[:k]]


@lru_cache
def get_retriever():
    return Retriever()


def evaluate(k=3):
    import pandas as pd
    gold = json.loads((ROOT / "eval" / "intent_to_kb.json").read_text())
    real = pd.read_csv(ROOT / "eval" / "realistic_tickets.csv")
    real = real[real.intent != "out_of_scope"]
    bitext = pd.read_csv(DATA_PROCESSED / "test.csv").groupby("intent").sample(20, random_state=RANDOM_STATE)
    r = get_retriever()
    from src.classifier import IntentClassifier
    clf = IntentClassifier.load()
    rows = []
    for name, df in [("realistic", real), ("bitext_sample", bitext)]:
        for mode in ("bm25", "dense", "hybrid", "hybrid+intent"):
            hits, rr = [], []
            for text, intent in zip(df["text"], df["intent"]):
                hint = None
                if mode == "hybrid+intent":   # PREDICTED intents, never the gold label
                    hint = [t["intent"] for t in clf.predict(text)["top3"]]
                ids = [h["id"] for h in r.search(text, k=10, mode=mode.split("+")[0], intents=hint)]
                rel = set(gold[intent])
                hits.append(any(i in rel for i in ids[:k]))
                rank = next((n + 1 for n, i in enumerate(ids) if i in rel), None)
                rr.append(1 / rank if rank else 0)
            rows.append({"set": name, "mode": mode, f"recall@{k}": np.mean(hits), "mrr": np.mean(rr), "n": len(df)})
    res = pd.DataFrame(rows)
    print(f"dense encoder: {r.dense.kind} | reranker: {'on' if r.reranker else 'off'}")
    print(res.round(3).to_string(index=False))
    res.to_csv(REPORTS_DIR / "retrieval_eval.csv", index=False)
    return res


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "eval":
        evaluate()
    else:
        for h in get_retriever().search(" ".join(sys.argv[1:]) or "where is my refund"):
            print(h["score"], h["id"], "-", h["text"][:90])
