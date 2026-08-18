# Analise do projeto e roadmap de correcoes

## Analise honesta do estado atual

### O que funciona

1. Upload de videos pela interface (funciona, inclui intro e finalizacao)
2. Preprocessamento: deteccao de cenas, transcricao, footage index
3. Pipeline runner: Diretor -> Trim Refiner -> Editor -> Reviewer
4. Editor deterministico com FFmpeg (clip, concat, render)
5. Interface web: tela inicial, tela do editor, dialog de geracao
6. Suporte a OpenRouter (bypass do ADK)
7. 109 testes automatizados aprovados

### O que nao funciona bem

1. **Diretor via OpenRouter**: o Llama 4 Scout frequentemente retorna
   raciocinio em vez de JSON. Quando o fallback aciona, gera um plano
   trivial que repete o mesmo shot varias vezes.
2. **Intro e finalizacao nao sao usadas**: o Editor deterministico
   (`editor_openrouter.py`) so faz clip + concat + render. Ele nao
   incorpora os assets de abertura e fechamento que o usuario enviou.
3. **Legendas nao sao aplicadas**: o Editor OpenRouter nao queima legendas.
4. **Overlays nao sao aplicados**: titulo, CTA e creditos sao ignorados.
5. **Shorts nao sao gerados**: nao ha implementacao no Editor OpenRouter.
6. **Reviewer via OpenRouter**: envia frames do video para o Llama, mas
   modelos gratuitos podem nao ter capacidade de vision adequada.
7. **Trim Refiner**: skipado no modo OpenRouter (correto, mas limita qualidade).

### O resultado atual

Um video curto com cortes repetidos do mesmo trecho, sem intro, sem
finalizacao, sem legendas, sem overlays. Funcionalmente o pipeline
completa, mas o resultado nao atende o objetivo de um "video editado
pronto para publicacao".

## O projeto tem viabilidade?

**Sim, mas nao com modelos gratuitos do OpenRouter como Diretor.**

O projeto foi arquitetado para Gemini, que tem:
- Input de video nativo (analisa o video frame a frame)
- Tool calling confiavel (search_moments, analyze_footage)
- Output schema estruturado (EditPlan em JSON garantido)

Modelos gratuitos do OpenRouter (Llama 4 Scout) nao tem:
- Input de video nativo
- Tool calling confiavel via ADK
- Garantia de output estruturado

### Caminho viavel

1. **Usar Gemini quando tiver cota** (modo gemini)
2. **Usar OpenRouter como fallback deterministico** (modo openrouter)
   - Diretor: usa o LLM para selecionar shots, mas com prompt extremamente
     simples e fallback robusto
   - Editor: deterministico com FFmpeg, incluindo intro, finalizacao,
     legendas e overlays
   - Reviewer: opcional no modo OpenRouter

## Roadmap de correcoes

### Prioridade 1: Editor deterministico completo

O Editor OpenRouter precisa incorporar TODOS os elementos:

1. Prepend da abertura (se existir no perfil)
2. Clip + concat do conteudo principal
3. Append da finalizacao (se existir no perfil)
4. Queimar legendas ASS (se ativado no perfil)
5. Aplicar overlays de texto (titulo, CTA, creditos)
6. Render final em 16:9

Arquivo: `src/agents/editor_openrouter.py`

Passos:
1. apos clipar e sequenciar o conteudo, fazer prepend da intro
2. fazer append da finalizacao
3. se captions ativado, gerar ASS e queimar
4. se overlays configurados, aplicar com drawtext
5. render final

### Prioridade 2: Diretor com prompt melhorado

O Diretor OpenRouter precisa de um prompt que o Llama consiga seguir:

1. Dar apenas 3-5 shots (nao 20+)
2. Pedir explicitamente: "selecione os melhores 3 shots"
3. Fornecer um exemplo completo de JSON na resposta esperada
4. Se fallback, usar os shots de maior energy_level primeiro

Arquivo: `src/agents/director_openrouter.py`

### Prioridade 3: Fallback do Diretor mais inteligente

Em vez de repetir o mesmo shot, o fallback deve:

1. Usar todos os shots A-Roll disponiveis
2. Dividir a duracao alvo entre eles
3. Ordenar por energy_level (maior primeiro)
4. Nao repetir shots

### Prioridade 4: Reviewer opcional no modo OpenRouter

Se o modelo nao suportar vision, retornar um score padrao:
- overall: 0.6
- feedback: "Review automatica indisponivel no modo OpenRouter"

### Prioridade 5: Integrar Shorts no Editor

Gerar Shorts apos o video principal:
1. Selecionar trechos de maior energia
2. Recortar em 9:16
3. Aplicar legendas
4. Renderizar arquivos independentes

## Tarefas passo a passo para execucao

### Task 1: Corrigir Editor OpenRouter (intro + finalizacao)

**Arquivo**: `src/agents/editor_openrouter.py`

**Problema**: O editor nao usa os assets de intro e finalizacao.

**Solucao**:
1. Apos sequenciar os clips do conteudo, verificar `edit_plan.profile.opening`
2. Se existir, fazer prepend usando `sequence_clips([intro_path, conteudo])`
3. Verificar `edit_plan.profile.closing`
4. Se existir, fazer append usando `sequence_clips([conteudo, closing_path])`
5. Testar com videos reais que tem intro e finalizacao

### Task 2: Corrigir fallback do Diretor

**Arquivo**: `src/agents/director_openrouter.py`

**Problema**: Fallback repete o mesmo shot.

**Solucao**:
1. Filtrar apenas shots A-Roll (roll_type == "a-roll" ou "unknown")
2. Ordenar por energy_level (maior primeiro)
3. Dividir a duracao alvo entre os shots disponiveis
4. Cada shot aparece apenas uma vez
5. Se houver B-Roll, intercalar entre os A-Roll

### Task 3: Adicionar legendas no Editor OpenRouter

**Arquivo**: `src/agents/editor_openrouter.py`

**Problema**: Legendas nao sao geradas.

**Solucao**:
1. Se `edit_plan.profile.captions.enabled`:
2. Para cada entry, chamar `generate_ass_captions(footage_index_path, shot_id, start_trim, end_trim, output)`
3. Queimar com `burn_ass_subtitles(video, ass_path, output)`
4. Continuar o pipeline com o video legendado

### Task 4: Adicionar overlays no Editor OpenRouter

**Arquivo**: `src/agents/editor_openrouter.py`

**Problema**: Overlays de texto nao sao aplicados.

**Solucao**:
1. Se `edit_plan.profile.overlays`:
2. Chamar `build_plan_overlays(edit_plan, duration)` para gerar lista
3. Chamar `apply_plan_overlays(video, overlays, output)` para aplicar

### Task 5: Simplificar prompt do Diretor

**Arquivo**: `src/agents/director_openrouter.py`

**Problema**: Llama nao segue o prompt.

**Solucao**:
1. Reduzir para maximo 5 shots no prompt
2. Incluir exemplo completo de JSON esperado
3. Usar temperature=0.0
4. Adicionar "Respota anterior invalida" no retry

### Task 6: Reviewer com fallback seguro

**Arquivo**: `src/agents/reviewer_openrouter.py`

**Problema**: Vision pode falhar com modelos gratuitos.

**Solucao**:
1. Try/catch na chamada OpenRouter
2. Se falhar, retornar ReviewScore padrao:
   - overall: 0.6
   - feedback: "Revisao automatica indisponivel"
3. Nao derrubar o pipeline

### Task 7: Atualizar EVOLUCAO_PROJETO.md

Marcar tasks concluidas e adicionar o que falta.

## Ordem de execucao recomendada

1. Task 2 (fallback Diretor) - corrige o resultado ruim imediatamente
2. Task 1 (intro + finalizacao) - usa os assets enviados
3. Task 5 (prompt Diretor) - melhora qualidade da selecao
4. Task 3 (legendas) - funcionalidade esperada
5. Task 4 (overlays) - funcionalidade esperada
6. Task 6 (Reviewer fallback) - robustez
7. Task 7 (documentacao) - manter registro

## Limitacoes reais

1. **Modelos gratuitos do OpenRouter nao tem input de video nativo**:
   a analise de cenas usa apenas metadados do footage index (descricao,
   transcricao, energia), nao analise visual frame a frame.

2. **A qualidade do EditPlan depende do modelo**:
   com Gemini (quando tem cota), o resultado e muito melhor porque o
   Gemini analisa o video nativamente.

3. **O Trim Refiner e skipado no modo OpenRouter**:
   os cortes ficam menos precisos. Aceitavel para MVP.

4. **Shorts ainda nao implementados**:
   nem no modo Gemini nem no modo OpenRouter. E uma fase posterior.

5. **A deteccao de silencios/hesitacoes ainda nao foi implementada**:
   o preprocessamento detecta cenas e transcreve, mas nao marca
   silencios ou hesitacoes. Isso limita a qualidade dos cortes.
