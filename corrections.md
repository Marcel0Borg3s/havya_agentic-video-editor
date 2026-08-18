# Plano de Correções - Havya Agentic Video Editor

## Diagnóstico

O projeto usa Google ADK (Agent Development Kit) que foi projetado para Gemini.
O adapter OpenRouter (`src/models/openrouter_llm.py`) registra no ADK mas tem 3
problemas estruturais que impedem o funcionamento:

1. **Tool calls nao funcionam**: O adapter envia tools no formato OpenAI mas o
   ADK espera que o modelo retorne `function_call` parts. O Llama 4 Scout via
   OpenRouter nao segue o protocolo ADK corretamente.

2. **Output schema ignorado**: O ADK passa `output_schema` via `response_schema`
   no `GenerateContentConfig`. O adapter OpenRouter converte para
   `response_format` mas o Llama 4 nao respeita `json_schema` strict mode.

3. **Modelo repete a entrada**: Sem tool calls e sem schema, o modelo simplesmente
   retorna o JSON do brief que recebeu como entrada, em vez do EditPlan esperado.

## Estrategia

Em vez de adaptar o protocolo ADK para OpenRouter, criar um caminho direto
que bypassa o ADK quando `AI_PROVIDER=openrouter`. O Gemini continua funcionando
via ADK quando `AI_PROVIDER=gemini`.

## Passo 1: Criar Director direto via OpenRouter

Arquivo: `src/agents/director_openrouter.py`

Criar uma funcao `run_director_openrouter(brief, footage_index_path)` que:

1. Le o `footage_index.json` do disco
2. Constroi um prompt com:
   - A instrucao do Director (ja existe em `DIRECTOR_INSTRUCTION`)
   - O brief em JSON
   - O footage index resumido (source_file, start_time, end_time, description,
     transcript, roll_type de cada shot)
3. Chama `call_openrouter(prompt, response_schema=DirectorOutput)`
4. Faz o repair do JSON (mesma logica ja implementada)
5. Valida com `DirectorOutput.model_validate(best)`
6. Retorna um `EditPlan`

O prompt deve instruir o modelo a:
- NAO usar tool calls
- Produzir APENAS o JSON do EditPlan
- Usar os shots do footage index diretamente (ja estao no prompt)
- Seguir o schema DirectorOutput: entries, music_path, total_duration

Exemplo de construcao do prompt:

```python
def run_director_openrouter(brief, footage_index_path):
    from src.ai_provider import call_openrouter
    from src.models.schemas import FootageIndex, EditPlan
    from src.agents.director import DirectorOutput, DIRECTOR_INSTRUCTION

    index = FootageIndex.model_validate_json(
        Path(footage_index_path).read_text("utf-8")
    )

    # Resumir shots para o prompt
    shots_summary = []
    for i, shot in enumerate(index.shots):
        shots_summary.append(
            f"Shot {i}: source_file={shot.source_file}, "
            f"start_time={shot.start_time}, end_time={shot.end_time}, "
            f"description={shot.description}, "
            f"transcript={shot.transcript[:100] if shot.transcript else ''}, "
            f"roll_type={shot.roll_type}"
        )

    prompt = (
        DIRECTOR_INSTRUCTION
        + "\n\n## Footage Index\n"
        + "\n".join(shots_summary)
        + "\n\n## Creative Brief\n"
        + brief.model_dump_json()
        + "\n\n## Instrucoes de saida\n"
        + "Retorne APENAS um JSON object com:\n"
        + "- entries: lista de 5-10 objetos com shot_id, start_trim, end_trim,\n"
        + "  position, text_overlay, transition\n"
        + "- music_path: null\n"
        + "- total_duration: soma das duracoes A-roll\n"
        + "NAO use tool calls. NAO inclua markdown. Apenas o JSON.\n"
    )

    result = call_openrouter(prompt, response_schema=DirectorOutput)

    # Repair JSON
    import json
    cleaned = result["text"].strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if not cleaned.startswith("{"):
        idx = cleaned.find("{")
        if idx >= 0:
            cleaned = cleaned[idx:]

    # Progressive parse
    best = None
    for end in range(len(cleaned), 0, -1):
        if cleaned[end - 1] != "}":
            continue
        try:
            best = json.loads(cleaned[:end])
            break
        except json.JSONDecodeError:
            continue
    if best is None:
        best = json.loads(cleaned)

    parsed = DirectorOutput.model_validate(best)
    return EditPlan(
        brief=brief,
        entries=parsed.entries,
        music_path=parsed.music_path,
        total_duration=parsed.total_duration,
    )
```

## Passo 2: Criar Reviewer direto via OpenRouter

Arquivo: `src/agents/reviewer_openrouter.py`

Criar `run_reviewer_openrouter(brief, video_path, job_output_dir)` que:

1. Usa `call_openrouter` com `video_path` para enviar frames do video
2. Prompt com as instrucoes do Reviewer (ja existe em `REVIEWER_INSTRUCTION`)
3. `response_schema=ReviewScore`
4. Repair JSON
5. Retorna `ReviewScore`

Mesma estrutura do Director. O `call_openrouter` ja extrai frames do video
via ffmpeg, entao o Reviewer funciona com vision.

## Passo 3: Criar Editor direto via OpenRouter

Arquivo: `src/agents/editor_openrouter.py`

Criar `run_editor_openrouter(edit_plan, footage_index, profile, output_dir)` que:

1. NAO precisa de IA para a maior parte do trabalho
2. O Editor usa FFmpeg para: clip, concat, overlay, render
3. A unica parte que usa IA e a selecao de musica (opcional)
4. Para OpenRouter, pular a selecao de musica ou usar uma chamada simples

Na pratica, o Editor ja tem todas as tools de FFmpeg. O adapter OpenRouter
pode simplesmente executar as mesmas operacoes deterministicas sem precisar
de um LLM para orquestrar.

Alternativa mais simples: chamar as funcoes de render diretamente em Python
sem passar por um agent. O `src/tools/edit.py` e `src/tools/render.py` ja tem
toda a logica.

## Passo 4: Modificar o pipeline runner

Arquivo: `src/pipeline/runner.py`

No ponto onde o runner chama `run_director`, `run_reviewer`, `run_editor`:

```python
from src.config import AI_PROVIDER

if AI_PROVIDER == "openrouter":
    from src.agents.director_openrouter import run_director_openrouter
    edit_plan = run_director_openrouter(brief, footage_index_path)
else:
    edit_plan = _with_transient_retry(
        run_director, brief=brief, footage_index_path=footage_index_path
    )
```

Mesma logica para reviewer e editor.

## Passo 5: Simplificar o Trim Refiner para OpenRouter

O trim refiner ja tem suporte OpenRouter (passo anterior). Mas o modelo
Llama 4 Scout pode nao ser bom em analisar frames de video.

Para o modo OpenRouter, o trim refiner pode simplesmente pular o refinamento
e manter os trim points originais do Director. Isso e aceitavel para o MVP.

```python
if AI_PROVIDER == "openrouter":
    _log("[trim_refiner] Skipping refinement (OpenRouter mode)")
    return original_trim
```

## Passo 6: Atualizar .env.example

```env
# AI Provider: "gemini" (Google) or "openrouter" (free models)
AI_PROVIDER=openrouter

# --- OpenRouter (free) ---
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=meta-llama/llama-4-scout

# --- Gemini (Google) ---
# AI_PROVIDER=gemini
# GOOGLE_API_KEY=your_key_here
# GEMINI_DIRECTOR_MODEL=gemini-3.6-flash
```

## Passo 7: Testar cada componente isoladamente

### Teste 1: Director OpenRouter
```python
from src.agents.director_openrouter import run_director_openrouter
from src.models.schemas import CreativeBrief

brief = CreativeBrief(
    product="Produto Teste",
    audience="Publico geral",
    tone="energetic",
    duration_seconds=30,
    style_ref=None,
)
plan = run_director_openrouter(brief, "output/projects/<id>/footage_index.json")
print(f"Entries: {len(plan.entries)}")
print(f"Duration: {plan.total_duration}")
```

### Teste 2: Reviewer OpenRouter
```python
from src.agents.reviewer_openrouter import run_reviewer_openrouter
score = run_reviewer_openrouter(brief, "output/jobs/<id>/final.mp4", "output/jobs/<id>")
print(f"Overall: {score.overall}")
```

### Teste 3: Pipeline completo
```bash
# Com AI_PROVIDER=openrouter no .env
ave edit --footage-dir ./footage --brief '{"product":"test","audience":"general","tone":"energetic","duration_seconds":30}' --pipeline pipelines/ugc-ad.yaml
```

## Passo 8: Teste frontend

1. Reiniciar backend com `AI_PROVIDER=openrouter`
2. Reiniciar frontend
3. Criar projeto com video real
4. Clicar em "Gerar video"
5. Verificar se o pipeline completa sem erros
6. Verificar se o video final e gerado

## Ordem de execucao

1. Passo 1 (Director OpenRouter) - Mais critico
2. Passo 4 (Pipeline runner) - Conectar o Director
3. Passo 5 (Trim Refiner skip) - Evitar erros
4. Passo 2 (Reviewer OpenRouter) - Para completar o loop
5. Passo 3 (Editor direto) - Simplificar
6. Passo 7 (Testes isolados)
7. Passo 8 (Teste frontend)

## Arquivos a criar

- `src/agents/director_openrouter.py`
- `src/agents/reviewer_openrouter.py`
- `src/agents/editor_openrouter.py` (opcional, pode usar logica deterministica)

## Arquivos a modificar

- `src/pipeline/runner.py` - Adicionar branches OpenRouter
- `src/agents/trim_refiner.py` - Skip no modo OpenRouter
- `.env.example` - Atualizar documentacao

## Riscos e mitigacoes

- **Llama 4 Scout pode nao seguir o schema JSON**: O repair JSON ja trata isso.
  Se persistir, adicionar um prompt mais explicito com exemplo de JSON.
- **Qualidade do EditPlan pode ser menor**: Aceitavel para MVP. O usuario pode
  ajustar manualmente na timeline.
- **Vision pode nao funcionar bem com frames**: Se o modelo nao suportar imagens,
  pular a analise visual e usar apenas metadados do footage index.
- **Modelo pode ser lento**: Timeout de 120s por chamada. Se necessario, aumentar.
