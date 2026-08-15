# Havya Studio (Frontend)

Interface visual local do Havya para edição automática de vídeos.

## Requisitos

- Node.js 20+ recomendado.
- pnpm 11+.
- Backend FastAPI disponível na porta 8000.
- FFmpeg instalado no sistema.

## Inicialização local

### 1. Iniciar o backend

Em um terminal:

```bash
cd ~/projects/HAVYA/agentic-video-editor
uv run uvicorn src.web.app:app --reload --port 8000
```

Verifique a API:

```bash
curl http://localhost:8000/api/health
```

Resposta esperada:

```json
{"status":"ok"}
```

### 2. Instalar dependências do frontend

Em outro terminal:

```bash
cd ~/projects/HAVYA/agentic-video-editor/src/web/studio
corepack enable
corepack prepare pnpm@11.22.0 --activate
pnpm install
```

O projeto autoriza explicitamente o build do `sharp`, necessário pelo Next.js.

### 3. Iniciar o Havya Studio

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm dev --port 3000
```

Abra no navegador:

```text
http://localhost:3000
```

O Next.js também possui rewrite padrão para `http://localhost:8000`, portanto a variável `NEXT_PUBLIC_API_URL` pode ser omitida quando o backend estiver nessa porta.

## Primeiro teste visual

1. Abra `http://localhost:3000`.
2. Crie um projeto apontando para uma pasta local com vídeos.
3. Aguarde o status `ready`.
4. Abra o projeto.
5. Clique em **Run Pipeline**.
6. Confirme a presença de:
   - marca Havya Studio;
   - perfil de edição;
   - abertura e fechamento;
   - título;
   - nome do canal;
   - créditos;
   - legendas;
   - Shorts;
   - quantidade e duração dos Shorts.

Nesta etapa, não é necessário iniciar uma renderização completa. O objetivo é validar a inicialização e a configuração visual.

## Build de produção

```bash
pnpm build
pnpm start --port 3000
```

## Tech Stack

- Next.js 16, React 19, TypeScript
- Tailwind CSS 4
- Zustand
- @dnd-kit
- Recharts
- Lucide
