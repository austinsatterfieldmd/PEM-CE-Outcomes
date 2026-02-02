"""Quick test of Gemini with 6000 max_tokens."""
import asyncio
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

from src.core.taggers.openrouter_client import get_openrouter_client
from src.core.services.prompt_manager import get_prompt_manager
import pandas as pd


async def test_gemini():
    client = get_openrouter_client()
    pm = get_prompt_manager()

    # Load sample questions
    df = pd.read_excel(PROJECT_ROOT / 'data/checkpoints/stage2_ready_cleaned_20260125_162222.xlsx')
    df = df[df['STAGE1_disease_state'] == 'Multiple myeloma'].head(3)

    disease_prompt = pm.get_disease_prompt('Multiple myeloma', version='v2.0')

    for idx, row in df.iterrows():
        q = str(row['OPTIMIZEDQUESTION'])
        a = str(row['OPTIMIZEDCORRECTANSWER']) if pd.notna(row.get('OPTIMIZEDCORRECTANSWER')) else ''

        messages = [
            {'role': 'system', 'content': disease_prompt},
            {'role': 'user', 'content': f'Question: {q}\nCorrect Answer: {a}\nContext: This question is about Multiple myeloma.'}
        ]

        print(f'Testing question {idx}...')
        try:
            resp = await client.generate('gemini', messages, response_format={'type': 'json_object'})
            content = resp.get('content', '')

            # Try to parse
            if '```json' in content:
                start = content.find('```json') + 7
                end = content.find('```', start)
                content = content[start:end].strip()
            elif '```' in content:
                start = content.find('```') + 3
                end = content.find('```', start)
                content = content[start:end].strip()

            tags = json.loads(content)
            print(f'  SUCCESS: {len(tags)} fields returned')
        except json.JSONDecodeError as e:
            print(f'  JSON PARSE FAILED: {e}')
            print(f'  Content length: {len(content)} chars')
            print(f'  Last 200 chars: ...{content[-200:]}')
        except Exception as e:
            print(f'  ERROR: {e}')
        print()

    print(f'Total API cost: ${client.get_total_cost():.4f}')


if __name__ == '__main__':
    asyncio.run(test_gemini())
