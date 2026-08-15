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

- [ ] Normalizar assets externos.
- [ ] Montar abertura, conteúdo e fechamento.
- [ ] Integrar legendas.
- [ ] Integrar título, CTA e créditos.
- [ ] Implementar cortes e transições básicas.
- [ ] Gerar um único MP4 final.
- [ ] Criar testes com vídeos sintéticos.

### Fase 4 — Análise editorial

- [ ] Detectar silêncio.
- [ ] Detectar pausas longas.
- [ ] Detectar hesitações.
- [ ] Detectar repetições.
- [ ] Detectar takes ruins.
- [ ] Integrar dados ao Director e Trim Refiner.

### Fase 5 — Abstração de IA

- [ ] Criar interface `AIProvider`.
- [ ] Implementar Gemini.
- [ ] Implementar provider OpenAI-compatible.
- [ ] Implementar provider HTTP customizado.
- [ ] Permitir IA desligada.
- [ ] Adicionar provider fake para testes.

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

## Registro de testes

| Data | Comando | Resultado | Observações |
|---|---|---|---|
| — | — | — | A registrar na primeira etapa de implementação |

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
