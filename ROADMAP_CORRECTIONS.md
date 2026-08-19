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

**Status**: CONCLUIDA

**Arquivo**: `src/agents/editor_openrouter.py`

**Problema**: O editor nao usa os assets de intro e finalizacao.

**Solucao implementada**:
1. Apos renderizar o conteudo, verificar `edit_plan.profile.opening`
2. Se existir, chamar `assemble_with_assets()` com opening_path
3. Verificar `edit_plan.profile.closing`
4. Se existir, incluir closing_path na montagem
5. O `assemble_with_assets()` normaliza e concatena automaticamente

### Task 2: Corrigir fallback do Diretor

**Status**: CONCLUIDA

**Arquivo**: `src/agents/director_openrouter.py`

**Problema**: Fallback repete o mesmo shot.

**Solucao implementada**:
1. Filtrar shots A-Roll (roll_type == "a-roll" ou "unknown")
2. Ordenar por energy_level (maior primeiro)
3. Dividir a duracao alvo entre os shots disponiveis
4. Cada shot aparece apenas uma vez (maximo 5)

### Task 3: Adicionar legendas no Editor OpenRouter

**Status**: CONCLUIDA

**Arquivo**: `src/agents/editor_openrouter.py`

**Problema**: Legendas nao sao geradas.

**Solucao implementada**:
1. Se `edit_plan.profile.captions.enabled`:
2. Para cada entry, chamar `generate_ass_captions()`
3. Mesclar ASS files com offsets de tempo
4. Queimar com `burn_ass_subtitles()`
5. Continuar o pipeline com o video legendado

### Task 4: Adicionar overlays no Editor OpenRouter

**Status**: CONCLUIDA

**Arquivo**: `src/agents/editor_openrouter.py`

**Problema**: Overlays de texto nao sao aplicados.

**Solucao implementada**:
1. Verificar se ha overlays no profile ou no output
2. Chamar `apply_plan_overlays()` com o plano completo
3. Aplicar titulo, CTA e creditos automaticamente

### Task 5: Simplificar prompt do Diretor

**Status**: CONCLUIDA

**Arquivo**: `src/agents/director_openrouter.py`

**Problema**: Llama nao segue o prompt.

**Solucao implementada**:
1. Reduzir para top 5 shots por energy_level
2. Incluir instrucao clara de selecao
3. Mantido temperature=0.1
4. Retry com mensagem mais explicita sobre formato esperado

### Task 6: Reviewer com fallback seguro

**Status**: CONCLUIDA

**Arquivo**: `src/agents/reviewer_openrouter.py`

**Problema**: Vision pode falhar com modelos gratuitos.

**Solucao implementada**:
1. Try/catch completo na chamada OpenRouter
2. Se falhar, retornar ReviewScore padrao:
   - overall: 0.6
   - feedback: "Revisao automatica indisponivel"
3. Pipeline nao derruba mais por erro do reviewer

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
