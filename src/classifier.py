"""Step 2: intent classifier + confidence calibration + auto-resolve threshold.

Model   : TF-IDF (word 1-2 grams + char 3-5 grams, robust to typos) -> Logistic Regression
Category: derived from the predicted intent (intent -> category map), so they never disagree
Honesty : Bitext is template-generated, so in-distribution test accuracy is ~99.9% and means little.
          We ALSO evaluate on eval/realistic_tickets.csv: hand-written messy tickets + out-of-scope
          ones (app crashes, legal threats, prompt injection) that must NOT be auto-answered.
Threshold: chosen on the realistic DEV half with a cost function
          (a wrong auto-reply costs 3x what a correct one saves), reported on the TEST half.
Run:  python -m src.classifier
"""
import json
import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
from sklearn.pipeline import FeatureUnion, Pipeline

from src.config import DATA_PROCESSED, MODELS_DIR, REPORTS_DIR, ROOT

MODEL_PATH = MODELS_DIR / "intent_clf.joblib"
REALISTIC = ROOT / "eval" / "realistic_tickets.csv"
WRONG_COST = 3.0   # a wrong automatic answer is 3x worse than a correct one is good


def build_model():
    feats = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True)),
    ])
    return Pipeline([("tfidf", feats), ("clf", LogisticRegression(C=10, max_iter=2000))])


def expected_calibration_error(conf, correct, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def choose_threshold(conf, correct, wrong_cost=WRONG_COST):
    """Pick the confidence threshold that maximises: correct auto-answers - wrong_cost * wrong ones.
    Out-of-scope tickets count as 'wrong' if they are auto-answered."""
    best_t, best_u = 1.0, -np.inf
    for t in np.round(np.arange(0.05, 1.00, 0.01), 2):
        m = conf >= t
        u = correct[m].sum() - wrong_cost * (~correct[m]).sum()
        if u > best_u:
            best_t, best_u = float(t), u
    return best_t


def realistic_eval(model, df, thr):
    proba = model.predict_proba(df["text"])
    pred, conf = model.classes_[proba.argmax(1)], proba.max(1)
    ins = (df["intent"] != "out_of_scope").values
    correct = pred == df["intent"].values          # always False for out_of_scope rows
    auto = conf >= thr
    return {"n": int(len(df)), "in_scope_accuracy": float(correct[ins].mean()),
            "auto_coverage_in_scope": float(auto[ins].mean()),
            "auto_accuracy": float(correct[auto].mean()) if auto.any() else None,
            "out_of_scope_escalated": float((~auto[~ins]).mean()) if (~ins).any() else None}


class IntentClassifier:
    def __init__(self, model, intent_to_category, threshold):
        self.model, self.intent_to_category, self.threshold = model, intent_to_category, threshold

    def predict(self, text: str) -> dict:
        proba = self.model.predict_proba([text])[0]
        order = np.argsort(proba)[::-1][:3]
        classes = self.model.classes_
        intent = classes[order[0]]
        return {"intent": intent, "category": self.intent_to_category[intent],
                "confidence": round(float(proba[order[0]]), 4),
                "confident": bool(proba[order[0]] >= self.threshold),
                "top3": [{"intent": classes[i], "p": round(float(proba[i]), 4)} for i in order]}

    @classmethod
    def load(cls, path=MODEL_PATH):
        d = joblib.load(path)       # saved as a plain dict so it unpickles from any entry point
        return cls(d["model"], d["intent_to_category"], d["threshold"])


def main():
    import pandas as pd
    tr, va, te = (pd.read_csv(DATA_PROCESSED / f"{s}.csv") for s in ("train", "val", "test"))
    i2c = dict(zip(tr["intent"], tr["category"]))
    try:                                   # feedback loop: add human-corrected tickets to training
        from src import store
        fb = pd.DataFrame(store.export_feedback_labels())
        fb = fb[fb["intent"].isin(i2c)] if len(fb) else fb
        if len(fb):
            print(f"adding {len(fb)} human-corrected tickets from feedback")
            tr = pd.concat([tr, fb.assign(category=fb["intent"].map(i2c), noisy=False)], ignore_index=True)
    except Exception:
        pass

    base = DummyClassifier(strategy="most_frequent").fit(tr["text"], tr["intent"])
    model = build_model().fit(tr["text"], tr["intent"])

    pt = model.predict_proba(te["text"])
    pred, conf = model.classes_[pt.argmax(1)], pt.max(1)
    correct = pred == te["intent"].values
    noisy = te["noisy"].values

    real = pd.read_csv(REALISTIC)
    dev, rtest = real[real.split == "dev"], real[real.split == "test"]
    pd_ = model.predict_proba(dev["text"])
    thr = choose_threshold(pd_.max(1), model.classes_[pd_.argmax(1)] == dev["intent"].values)

    report = {
        "bitext_test": {
            "baseline_accuracy": accuracy_score(te["intent"], base.predict(te["text"])),
            "accuracy": accuracy_score(te["intent"], pred),
            "macro_f1": f1_score(te["intent"], pred, average="macro"),
            "category_accuracy": float(np.mean(np.array([i2c[p] for p in pred]) == te["category"].values)),
            "accuracy_noisy_text": float(correct[noisy].mean()),
            "ece": expected_calibration_error(conf, correct)},
        "auto_threshold": thr,
        "realistic_test": realistic_eval(model, rtest, thr),
        "realistic_all_no_threshold": realistic_eval(model, real, 0.0),
    }
    print(json.dumps(report, indent=2, default=lambda x: round(x, 4)))

    cm = confusion_matrix(te["intent"], pred, labels=model.classes_)
    np.fill_diagonal(cm, 0)
    cm = pd.DataFrame(cm, index=model.classes_, columns=model.classes_)
    top = cm.stack().sort_values(ascending=False).head(8)
    print("\nmost confused (true -> predicted):")
    for (a, b), n in top[top > 0].items():
        print(f"  {a:28s} -> {b:28s} {n}")

    (REPORTS_DIR / "classifier_report.json").write_text(json.dumps(report, indent=2))
    (REPORTS_DIR / "classifier_per_intent.txt").write_text(classification_report(te["intent"], pred, digits=3))
    joblib.dump({"model": model, "intent_to_category": i2c, "threshold": thr}, MODEL_PATH)
    print(f"\nsaved -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
