.PHONY: install data train retrieval eval eval-llm api ui test all docker
install:   ; pip install -r requirements.txt
data:      ; python -m src.data
train:     ; python -m src.classifier
retrieval: ; python -m src.retrieval eval
eval:      ; python -m src.evaluate
eval-llm:  ; python -m src.evaluate --llm
api:       ; uvicorn src.api:app --reload
ui:        ; streamlit run dashboard.py
test:      ; pytest -q
all: data train retrieval eval test
docker:    ; docker compose up --build
