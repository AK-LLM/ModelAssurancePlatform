"""OpenCompass configuration for a local OpenAI-compatible endpoint managed by MAP."""

import os
from opencompass.models import OpenAI
from opencompass.datasets import humaneval_datasets

BASE_URL = os.getenv('MAP_OPENAI_BASE_URL', 'http://localhost:1234/v1')
MODEL_NAME = os.getenv('MAP_OPENAI_MODEL', 'local-model')
API_KEY = os.getenv('MAP_OPENAI_API_KEY', 'lm-studio')

models = [
    dict(
        type=OpenAI,
        path=MODEL_NAME,
        key=API_KEY,
        openai_api_base=BASE_URL,
        query_per_second=1,
        rpm_verbose=False,
        max_out_len=1024,
        batch_size=1,
    )
]

datasets = [*humaneval_datasets[:1]]
