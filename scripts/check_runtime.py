"""Fail a build if required serving artifacts cannot load. No training or network calls."""
import hashlib
import importlib.metadata
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sklearn.exceptions import InconsistentVersionWarning
from src.classifier import IntentClassifier, MODEL_PATH
from src.retrieval import get_retriever

with warnings.catch_warnings():
    warnings.simplefilter('error', InconsistentVersionWarning)
    classifier = IntentClassifier.load()
assert len(classifier.intent_to_category) == 27
assert classifier.predict('Where is my order?')['top3']
r = get_retriever()
assert r.chunks and r.search('Where is my order?', k=3)
print('Serving model loaded; no training performed')
print('model_sha256=' + hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest())
print('sklearn=' + importlib.metadata.version('scikit-learn'))
print('retrieval=' + r.dense.kind + '; chunks=' + str(len(r.chunks)))
