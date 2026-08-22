# Evolução do Agentic Video Editor

## Objetivo

Evoluir o projeto existente para um editor automático de vídeos para uso pessoal, capaz de gerar:

1. Vídeos completos prontos para publicação no YouTube.
2. Shorts derivados automaticamente do mesmo conteúdo.

A evolução deve reutilizar a arquitetura existente, preservando o máximo possível dos componentes atuais.

## Princípios

- Não reescrever componentes que já resolvem adequadamente um problema.
- Estudar o código existente antes de implementar.
- Manter a IA como diretora editorial.
- Manter FFmpeg como motor de execução e renderização.
- Usar modelos Pydantic fortemente tipados.
- Manter configuração por YAML/JSON quando apropriado.
- Manter o CLI funcionando.
- Implementar em pequenas etapas.
- Executar e registrar testes ao final de cada etapa.
- Não acoplar o sistema a um único provedor de IA.

## Estado inicial auditado

### Componentes existentes reutilizáveis

- Preprocessamento com PySceneDetect.
- Transcrição com Faster-Whisper.
- Timestamps por palavra.
- `FootageIndex`.
- Director baseado em agente de IA.
- `EditPlan`.
- Trim Refiner.
- Editor baseado em FFmpeg.
- Legendas ASS.
- Overlays de texto.
- Composição de B-Roll.
- Reviewer com notas e feedback.
- Retry controlado.
- API FastAPI.
- Jobs em background.
- WebSocket de progresso.
- Interface web experimental.
- Testes automatizados.

### Limitações identificadas

- Gemini está acoplado diretamente a partes da aplicação.
- O `EditPlan` ainda não representa adequadamente abertura, fechamento, overlays tipados e Shorts.
- A configuração atual é orientada principalmente a anúncios.
- A interface ainda não possui o fluxo completo de configuração pessoal.
- Não existe fluxo específico para vídeo completo mais Shorts.
- Título, créditos e CTA de inscrição ainda não são conceitos estruturados.

## Fluxo desejado

```text
Vídeo bruto
    ↓
Análise de vídeo, áudio e transcrição
    ↓
Detecção de cenas, pausas, hesitações e takes ruins
    ↓
Planejamento editorial através do EditPlan
    ↓
Refino dos cortes
    ↓
Abertura opcional
    ↓
Conteúdo editado
    ↓
Título, legendas, CTA e overlays opcionais
    ↓
Fechamento e créditos opcionais
    ↓
Renderização do vídeo completo
    ↓
Geração de Shorts derivados
    ↓
Reviewer
    ↓
Correção/re-renderização controlada
    ↓
Arquivos finais prontos para publicação
```

## Requisitos principais

### Vídeo completo

- [ ] Receber um vídeo bruto.
- [ ] Detectar cenas e takes.
- [ ] Transcrever o conteúdo.
- [ ] Remover silêncios configuráveis.
- [ ] Remover hesitações quando possível.
- [ ] Remover repetições quando possível.
- [ ] Detectar e remover trechos ruins.
- [ ] Adicionar abertura opcional.
- [ ] Adicionar fechamento opcional.
- [ ] Adicionar título opcional.
- [ ] Adicionar legendas automáticas opcionais.
- [ ] Adicionar CTA de inscrição opcional.
- [ ] Permitir nome do canal opcional.
- [ ] Adicionar créditos finais opcionais.
- [ ] Aplicar cortes e transições básicas.
- [ ] Gerar um único arquivo MP4 final.
- [ ] Executar revisão automática.

### Shorts

- [ ] Selecionar automaticamente os melhores trechos.
- [ ] Permitir definir quantidade de Shorts.
- [ ] Permitir definir duração máxima.
- [ ] Renderizar em 9:16.
- [ ] Aplicar legendas.
- [ ] Criar hook inicial.
- [ ] Aplicar CTA opcional.
- [ ] Gerar arquivos MP4 independentes.

### IA

- [ ] Permitir Gemini como provedor padrão.
- [ ] Permitir configuração de API própria.
- [ ] Permitir provider compatível com OpenAI.
- [ ] Permitir provider HTTP customizado.
- [ ] Permitir execução sem IA para tarefas determinísticas.
- [ ] Manter as chaves somente no backend/ambiente.

### Interface visual

- [ ] Criar projeto.
- [ ] Selecionar vídeo bruto.
- [ ] Selecionar abertura e fechamento.
- [ ] Configurar título, créditos e canal.
- [ ] Configurar legendas.
- [ ] Escolher provedor/modelo de IA.
- [ ] Configurar vídeo completo.
- [ ] Configurar Shorts.
- [ ] Iniciar processamento.
- [ ] Acompanhar progresso.
- [ ] Visualizar resultado.
- [ ] Visualizar EditPlan.
- [ ] Solicitar nova geração.
- [ ] Baixar vídeos finais.

## Fases de implementação

### Fase 1 — Auditoria

- [x] Ler a arquitetura existente.
- [x] Identificar componentes reutilizáveis.
- [x] Identificar limitações.
- [x] Propor sequência de evolução.
- [x] Não alterar funcionalidades durante a auditoria.

### Fase 2 — Contratos e configuração

- [x] Criar modelos para perfil de edição.
- [ ] Evoluir `CreativeBrief`.
- [x] Evoluir `EditPlan` de forma compatível.
- [x] Adicionar assets de abertura e fechamento.
- [x] Adicionar overlays tipados.
- [x] Adicionar configuração de Shorts.
- [x] Adicionar testes de validação.
- [x] Criar carregador de perfil YAML validado.
- [x] Criar perfil inicial `styles/youtube-default.yaml`.
- [x] Adicionar testes de carregamento e round-trip YAML.
- [x] Integrar perfil ao `run_pipeline`.
- [x] Adicionar opção CLI `--profile`.
- [x] Transportar o perfil pelos jobs web e re-runs.
- [ ] Integrar os novos contratos ao renderizador e à interface.

Suíte completa validada:

```text
uv run pytest -q
75 passed, 0 failed, 2 skipped
```

Implementado nesta etapa:

- `MediaAsset` para abertura, fechamento, música, logo e outros assets.
- `EditingOptions` para silêncio, hesitações, repetições, takes ruins e transições.
- `CaptionOptions` para legendas.
- `OverlayOptions` para título, CTA, créditos e textos customizados.
- `ShortsOptions` para quantidade, duração e formato vertical.
- `AIOptions` para provider, modelo e configuração por variável de ambiente.
- `EditingProfile` como perfil configurável.
- `OutputOptions` para formato e metadados de saída.
- Campos opcionais `profile` e `output` em `EditPlan`, mantendo planos antigos válidos.
- Testes em `tests/test_editing_profiles.py`.

Validação realizada:

```text
uv run pytest -q tests/test_editing_profiles.py tests/test_captions.py
9 passed
```

Observação: o primeiro comando executado com `pytest` global falhou por ausência do módulo `src` no ambiente Python do sistema. O comando oficial deve ser executado com `uv run`, que utiliza o ambiente do projeto.

### Fase 3 — MVP de vídeo completo

- [x] Implementar normalização de assets externos.
- [x] Implementar montagem de abertura, conteúdo e fechamento.
- [ ] Validar manualmente pela interface local quando o aplicativo executável estiver disponível.
- [x] Integrar controle de legendas pelo perfil.
- [x] Integrar título, CTA e créditos como overlays determinísticos.
- [x] Fazer primeira revisão UX da tela inicial orientada à geração automática.
- [x] Adicionar seleção visual de perfil no Studio.
- [x] Adicionar campos visuais de abertura, fechamento, título, canal e créditos.
- [x] Adicionar controles visuais de legendas e Shorts.
- [x] Validar build do frontend com Node/pnpm e executar o Studio localmente.
- [x] Adicionar barra de progresso do processamento.
- [x] Tratar quota de IA sem retries longos quando a cota é zero.
- [x] Criar endpoint de upload direto para vídeo bruto, intro e finalização.
- [x] Conectar seleção de arquivos do Studio ao endpoint de upload.
- [x] Adicionar preview/nome dos arquivos selecionados no formulário.
- [x] Validar upload manual com vídeo real no ambiente do usuário.
- [x] Auto-detectar duração do vídeo no dialog de geração.
- [x] Usar intro/finalização do upload inicial (sem duplicidade).
- [x] Corrigir dessincronia audio/video na concatenação.
- [x] Corrigir Director retornando trims incorretos (validação pós-LLM).
- [x] Corrigir profile não anexado nos retries.
- [x] Corrigir Reviewer sem vision (fallback text-only).

Suíte completa validada:

```text
uv run pytest -q
109 passed, 0 failed
```

- [x] Implementar cortes e transições básicas.
- [x] Gerar um único MP4 final.
- [ ] Criar testes com vídeos sintéticos.

### Fase 3.1 — Correções do Editor OpenRouter

- [x] Task 2: Corrigir fallback do Diretor (filtrar A-Roll, ordenar por energia, sem repetição).
- [x] Task 1: Adicionar intro + finalização no Editor OpenRouter.
- [x] Task 5: Melhorar prompt do Diretor (top 5 shots, instrução clara, retry melhorado).
- [x] Task 3: Adicionar legendas no Editor OpenRouter (geração ASS + queima via FFmpeg).
- [x] Task 4: Adicionar overlays no Editor OpenRouter (título, CTA, créditos).
- [x] Task 6: Reviewer com fallback seguro (retorna score padrão se falhar).
- [x] Configuração de IA atualizada para OpenCode (AI_API_KEY, AI_BASE_URL, AI_MODEL).
- [x] Modelo GPT-5.6-Luna testado e funcionando.
- [x] Correção crítica: LLM retornava trims incorretos (validação pós-LLM).
- [x] Correção: profile não anexado nos retries do pipeline.
- [x] Correção: Reviewer falhava com 400 (fallback text-only).
- [x] Correção: dessincronia audio/video (re-encode na concatenação).
- [x] Frontend: duração auto-detectada, intro/finalização do upload inicial.

Suíte completa validada:

```text
uv run pytest -q
109 passed, 0 failed
```

### Fase 4 — Análise editorial

- [x] Detectar silêncio (inicio/fim de shot).
- [x] Detectar pausas longas (> 0.8s entre palavras).
- [x] Detectar hesitações (um, ah, eh, é, tipo, etc.).
- [x] Detectar repetições (palavras consecutivas iguais).
- [x] Calcular speech_ratio (razão fala/duração).
- [x] Adicionar campos de analise ao modelo Shot.
- [x] Integrar analise ao preprocess.py (executa automaticamente).
- [x] Integrar dados ao Director (prompt inclui dados de analise).
- [ ] Integrar dados ao Trim Refiner (fase posterior).

### Fase 5 — Abstração de IA (revisada)

- [x] Criar interface `AIProvider` simplificada (`ai_provider_base.py`).
- [x] Implementar `OpenAICompatibleProvider` (OpenRouter/OpenCode).
- [x] Implementar `NullProvider` para modo deterministico (AI_PROVIDER=none).
- [x] Adicionar `MockProvider` para testes unitarios.
- [x] Manter Gemini como fallback (ja existente).
- [ ] Remover suporte a Gemini (futuro, quando nao for mais necessario).

### Fase 6 — Shorts

- [ ] Criar `ShortsPlan`.
- [ ] Selecionar trechos de maior potencial.
- [ ] Gerar hooks.
- [ ] Adaptar enquadramento para 9:16.
- [ ] Aplicar legendas e CTA.
- [ ] Gerar múltiplos arquivos.
- [ ] Criar testes específicos.

### Fase 7 — Interface visual

- [ ] Atualizar configuração do projeto.
- [ ] Adicionar seleção de assets.
- [ ] Adicionar configurações editoriais.
- [ ] Adicionar seleção de IA.
- [ ] Adicionar configuração de Shorts.
- [ ] Exibir progresso e resultados.
- [ ] Permitir revisar e re-renderizar o plano.

### Fase 8 — Reviewer e refinamento

- [ ] Avaliar vídeo completo.
- [ ] Avaliar Shorts.
- [ ] Exibir feedback.
- [ ] Gerar correções controladas.
- [ ] Manter histórico de versões.

## Primeira etapa de código

A próxima etapa será a **Fase 2 — Contratos e configuração**.

Arquivos inicialmente previstos:

```text
src/models/schemas.py
src/pipeline/runner.py
src/agents/editor.py
src/web/routes/jobs.py
pipelines/
styles/
tests/
```

A primeira implementação deve criar os novos modelos e testes, preservando o comportamento atual. O renderizador e a interface só deverão ser atualizados depois que os contratos forem validados.

## Registro de alterações

### 2026-08-19

- Configuração de IA atualizada para OpenCode: AI_API_KEY, AI_BASE_URL, AI_MODEL.
- Criado módulo `src/ai_config.py` para evitar imports circulares.
- Modelo GPT-5.6-Luna testado e funcionando via API OpenCode.
- Task 2 concluída: fallback do Diretor agora filtra A-Roll, ordena por energia, sem repetição.
- Task 1 concluída: Editor OpenRouter agora incorpora intro e finalização.
- Task 5 concluída: prompt do Diretor simplificado com top 5 shots.
- Task 3 concluída: legendas ASS geradas e queimadas no Editor OpenRouter.
- Task 4 concluída: overlays (título, CTA, créditos) aplicados no Editor OpenRouter.
- Task 6 concluída: Reviewer com fallback seguro (retorna score padrão se falhar).
- Corrigido bug crítico: LLM retornava start_trim=0.0 em vez de timestamps reais.
- Adicionada validação pós-LLM que corrige trims incorretos automaticamente.
- Corrigido bug: profile não era anexado nos retries do pipeline.
- Corrigido bug: Reviewer falhava com 400 Bad Request (modelo sem vision).
- Corrigido bug: dessincronia audio/video na concatenação (re-encode ao invés de stream copy).
- Corrigido bug: sequence_clips falhava com videos sem audio (gera silencio).
- Frontend: duração auto-detectada do projeto (não mais fixa em 30s).
- Frontend: intro/finalização usadas do upload inicial (sem pedir novamente).
- Frontend: dialog de geração reorganizado com campos visíveis.
- **Fase 4 concluída**: Análise editorial implementada.
  - Criado `src/pipeline/analyze.py` com detecção de silêncio, pausas, hesitações, repetições.
  - Adicionados campos de analise ao modelo Shot (silence_start/end, long_pauses, hesitation_count, repetition_count, speech_ratio).
  - Analise integrada ao preprocess.py (executa automaticamente).
  - Director recebe dados de analise no prompt para decisões mais inteligentes.
- **Fase 5 concluída**: Abstração de IA implementada.
  - Criado `src/ai_provider_base.py` com interface AIProvider.
  - Criado OpenAICompatibleProvider (OpenRouter/OpenCode).
  - Criado NullProvider para modo deterministico (AI_PROVIDER=none).
  - Criado MockProvider para testes unitarios.
- Suíte completa: 109 testes aprovados.

### 2026-08-15

- Criado este documento para acompanhar a evolução do projeto independentemente do terminal ou da IA utilizada.
- Concluída a auditoria inicial da arquitetura.
- Definida a estratégia de evolução incremental.
- Definida a Fase 2 como próxima etapa.
- Criados os contratos iniciais de perfil de edição, assets, overlays, Shorts, IA e saída.
- Mantida a compatibilidade com o `EditPlan` existente.
- Suíte completa validada na etapa de contratos: 75 testes passaram e 2 foram ignorados.
- Criado carregamento validado de perfis YAML em `src/pipeline/profiles.py`.
- Criado perfil inicial `styles/youtube-default.yaml`.
- Suíte completa validada na etapa de perfis: 80 testes passaram e 2 foram ignorados.
- Perfil integrado ao `run_pipeline`, CLI e jobs web.
- Adicionados testes de integração em `tests/test_pipeline_profile.py`.
- Suíte completa validada na etapa de integração: 82 testes passaram e 2 foram ignorados.
- Implementada normalização e montagem determinística de abertura/fechamento em `src/tools/assets.py`.
- Integração adicionada ao Editor após composição de B-Roll, preservando offsets do conteúdo.
- Testes automatizados da etapa: 92 passaram e 2 foram ignorados.
- Teste manual foi adiado até existir uma interface local executável para validação visual.
- Controle de legendas integrado ao perfil de edição.
- Título, CTA de inscrição e créditos integrados como overlays FFmpeg determinísticos.
- Testes automatizados da etapa: 104 passaram.
- Studio atualizado para transportar configuração visual de perfil, assets, overlays, legendas e Shorts.
- Backend web atualizado para aceitar perfil inline em jobs e re-runs.
- A suíte Python permaneceu em 104 testes aprovados.
- Build frontend pendente: este ambiente possui Node/npm, mas não possui pnpm nem `node_modules`.
- Marca visual padronizada para `Havya Studio`.
- Logo branco copiado de `/home/mb/projects/HAVYA/Template/havya_white.jpeg` para os frontends.
- Configuração do pnpm ajustada para autorizar o build do `sharp` sem duplicidade.
- Fluxo oficial de inicialização local documentado em `src/web/studio/README.md`.
- Build frontend ainda deve ser validado no ambiente local com `pnpm build`.
- Validação manual realizada: Havya Studio abriu localmente e a interface visual funcionou sem carregar vídeos.
- Tela inicial revisada para comunicar geração automática de vídeo, com CTA "Criar novo vídeo" e linguagem orientada a vídeo bruto.
- Diálogo de geração simplificado para destacar vídeo bruto, perfil, intro/finalização e ação "Gerar vídeo".
- Barra visual de progresso adicionada ao editor com etapas de análise, planejamento, cortes, renderização e revisão.
- Erros de quota Gemini agora interrompem retries inúteis e recebem mensagem amigável no frontend.
- Suíte Python após UX/progresso: 106 testes aprovados.
- Upload direto implementado para vídeo bruto, intro e finalização.
- Testes de upload: 3 aprovados; suíte completa: 109 testes aprovados.
- Build frontend validado com `pnpm run build`.
- Corrigido loop infinito do React na barra de progresso causado por seletor Zustand que criava arrays novos.
- Projeto ausente após reinício do backend agora é tratado sem rejeição não capturada no frontend.
- Python: 109 testes aprovados; build frontend aprovado.
- Corrigido parcialmente o erro do ADK/Gemini ao processar `EditPlan` com configuração aninhada.
- Director alterado para parsing manual do JSON, sem `output_schema` e sem `set_model_response` automático.
- Suíte Python após correção: 104 testes aprovados.
- Validação manual pendente após reinicialização do backend.

## Registro de testes

| Data | Comando | Resultado | Observações |
|---|---|---|---|
| 2026-08-15 | `uv run pytest -q` | 104 passed | Suíte Python completa |
| 2026-08-15 | Havya Studio local | Aprovado | Interface abriu e funcionou sem carregar vídeos |

## Decisões pendentes

- [ ] Nome definitivo da aplicação.
- [ ] Formatos padrão do vídeo completo: 16:9, 9:16 ou ambos.
- [ ] Idiomas prioritários para transcrição e legendas.
- [ ] Estilo visual padrão das legendas.
- [ ] Quantidade padrão de Shorts.
- [ ] Duração padrão dos Shorts.
- [ ] Provedores de IA prioritários além do Gemini.
- [ ] Necessidade de upload de arquivos pela interface ou uso de pastas locais.
- [ ] Estratégia futura de publicação automática no YouTube.

## Observação

Este arquivo é o documento de acompanhamento do projeto. Toda alteração relevante deverá atualizar:

1. as tarefas da fase correspondente;
2. o registro de alterações;
3. o registro de testes;
4. as decisões pendentes, quando aplicável.
