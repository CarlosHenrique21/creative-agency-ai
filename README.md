# Flyer Forge — Social Media Agency AI

Sistema multiagente para geração automatizada de flyers para redes sociais.  
Orquestrado com **Google ADK**, modelos de texto **GPT-4o** e geração de imagens **gpt-image-1**.

---

## Arquitetura

```
POST /api/v1/flyers/generate
          │
          ▼
   ┌──────────────────┐
   │  Brand Strategist│  GPT-4o — consulta RAG de docs e define posicionamento
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────────┐
   │  Creative Director   │  GPT-4o — consulta RAG visual e cria direção criativa
   └────────┬─────────────┘
            │
            ▼  ┌─────────────────────── LoopAgent (máx 3 ciclos) ──────────────────────┐
            │  │                                                                         │
            │  │  ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐            │
            └──┼─▶│  Copywriter │───▶│   Designer  │───▶│ Social Media Mgr │            │
               │  └─────────────┘    └─────────────┘    └────────┬─────────┘            │
               │   GPT-4o             GPT-4o                      │                      │
               │   write_platform_copy generate_flyer_image       ▼                      │
               │                      + logo composite   ┌─────────────────┐             │
               │                                         │ Quality Reviewer│             │
               │                                         └────────┬────────┘             │
               │                                          GPT-4o  │                      │
               │                                          score_flyer_quality             │
               │                                                   │                      │
               │                              aprovado? ──── não ──┘ (volta Copywriter)  │
               │                                   │                                      │
               └───────────────────────────────────┼──────────────────────────────────────┘
                                                   ▼
                                           Flyers entregues
```

### Agentes

| Agente | Modelo | Responsabilidade |
|---|---|---|
| **Brand Strategist** | GPT-4o | Analisa brief + RAG de documentos → diretrizes de marca |
| **Creative Director** | GPT-4o | RAG visual + diretrizes → conceito criativo unificado |
| **Copywriter** | GPT-4o | Escreve headline, subheadline, body copy e CTA por plataforma |
| **Designer** | GPT-4o | Monta prompt visual → chama `gpt-image-1` → compõe logo |
| **Social Media Manager** | GPT-4o | Revisa boas práticas de cada plataforma |
| **Quality Reviewer** | GPT-4o | Notas 0-10 em 4 critérios; aprova (≥7.5) ou aciona revisão |

### Plataformas suportadas

| Plataforma | Resolução | Logo |
|---|---|---|
| Instagram Feed | 1080×1080 px | Canto inferior direito |
| Instagram Story | 1080×1920 px | Topo centralizado |
| LinkedIn Post | 1200×627 px | Canto inferior direito |
| LinkedIn Banner | 1584×396 px | Centro esquerdo |

---

## Stack

- **Google ADK** — orquestração (`SequentialAgent` + `LoopAgent`)
- **GPT-4o** — todos os agentes de texto
- **gpt-image-1** — geração de imagens
- **Pillow** — composição da logo sobre o flyer
- **ChromaDB** — vector store local para os dois sistemas RAG
- **FastAPI** — API REST
- **Pydantic** — validação de schemas na borda da API

---

## Sistemas RAG

### Brand RAG — documentos da marca
Ingere arquivos da marca, chunka, embeda com `text-embedding-3-small` e persiste no ChromaDB.  
Consultado pelo **Brand Strategist** e **Creative Director**.

Formatos suportados: `.pdf` `.docx` `.txt` `.md` `.json`

### Visual RAG — referências visuais
Cada imagem é analisada pelo **GPT-4o Vision**, que extrai estilo, mood, paleta, composição e keywords.  
A descrição é embeddada e armazenada no ChromaDB.  
Consultado pelo **Creative Director** e **Designer** para ancorar o prompt do `gpt-image-1`.

Formatos suportados: `.jpg` `.png` `.webp` `.gif`

---

## Estrutura do projeto

```
social-media-agency/
├── agents/
│   ├── brand_strategist/    # LlmAgent — posicionamento de marca
│   ├── creative_director/   # LlmAgent — direção criativa
│   ├── copywriter/          # LlmAgent — textos por plataforma
│   ├── designer/            # LlmAgent — prompts visuais + imagens
│   ├── social_media_manager/# LlmAgent — revisão de boas práticas
│   └── quality_reviewer/    # LlmAgent — scoring e aprovação
├── tools/
│   ├── image_tools.py       # generate_flyer_image (gpt-image-1 + logo)
│   ├── rag_tools.py         # query_brand_knowledge, query_visual_references
│   ├── copy_tools.py        # write_platform_copy
│   └── quality_tools.py     # score_flyer_quality
├── api/
│   ├── routes.py            # POST /api/v1/flyers/generate
│   └── rag_routes.py        # endpoints de ingestão e logo
├── core/
│   ├── config.py            # settings via .env
│   ├── orchestrator.py      # ADK SequentialAgent + LoopAgent + Runner
│   └── state.py             # CampaignInput, FlyerSpec, QualityScore
├── rag/
│   ├── brand_store.py       # ChromaDB — documentos
│   ├── visual_store.py      # ChromaDB — referências visuais
│   ├── logo_compositor.py   # Pillow — composição da logo
│   ├── ingest_cli.py        # CLI de ingestão
│   └── dependencies.py      # singletons dos stores
├── models/                  # schemas Pydantic de request/response
├── brand_assets/
│   ├── docs/                # coloque aqui os documentos da marca
│   ├── images/              # coloque aqui as imagens de referência
│   └── logo/                # coloque aqui a logo (<brand_id>.png)
└── tests/
```

---

## Configuração

```bash
# 1. Instalar dependências (uv gerencia o venv automaticamente)
uv sync

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env e adicione sua OPENAI_API_KEY
```

`.env`:
```env
OPENAI_API_KEY=sk-...
```

---

## Rodando

```bash
PYTHONPATH=. uv run python main.py
# ou com hot-reload:
PYTHONPATH=. uv run uvicorn main:app --reload
```

Documentação interativa: `http://localhost:8000/docs`

---

## Testando com o ADK

O ADK oferece duas formas nativas de testar o pipeline sem precisar subir a API.

### Playground web (recomendado)

```bash
PYTHONPATH=. uv run adk web .
```

Abre `http://localhost:8000` com uma interface de chat onde você conversa diretamente
com o pipeline. Os agentes rodam em sequência, você vê o estado sendo atualizado e
os logs de cada tool call em tempo real.

Exemplo de mensagem para iniciar um teste:

> *Crie flyers para o lançamento da EcoBottle, uma garrafa sustentável para jovens de 18 a 30 anos. Use as plataformas instagram_feed e linkedin_post. Cores: verde #2D6A4F, branco e destaque #95D5B2. Tom jovem e sustentável.*

### Terminal interativo

```bash
PYTHONPATH=. uv run adk run .
```

Mesma experiência do playground, mas direto no terminal — útil para CI ou ambientes sem browser.

### O que observar durante o teste

| O que aparece | O que significa |
|---|---|
| `[brand_strategist]` respondendo | RAG de docs foi consultado, diretrizes geradas |
| `query_visual_references` chamada | RAG visual ativo, keywords extraídas |
| `write_platform_copy` chamada | Copy de cada plataforma salvo no estado |
| `generate_flyer_image` chamada | gpt-image-1 gerando + logo sendo composta |
| `score_flyer_quality` chamada | Notas atribuídas; se média < 7.5 o loop repete |
| `status: completed` no estado final | Todos os flyers aprovados |

### Sem brand_id (teste rápido sem RAG)

Para um teste sem precisar ingerir documentos, basta não informar `brand_id`.
Os agentes usam apenas o perfil de marca passado na mensagem.

---

## Uso

### 1. Preparar os assets da marca (opcional mas recomendado)

**Via CLI:**
```bash
# Documentos
python -m rag.ingest_cli docs --brand-id ecobottle --dir ./brand_assets/docs

# Imagens de referência (analisadas por GPT-4o Vision)
python -m rag.ingest_cli images --brand-id ecobottle --dir ./brand_assets/images

# Listar o que foi ingerido
python -m rag.ingest_cli list --brand-id ecobottle
```

**Via API:**
```bash
# Upload de documentos
curl -X POST http://localhost:8000/api/v1/brands/ecobottle/ingest/docs \
  -F "files=@brand_guide.pdf" -F "files=@voice_tone.md"

# Upload de imagens de referência
curl -X POST http://localhost:8000/api/v1/brands/ecobottle/ingest/images \
  -F "files=@ref1.png" -F "files=@ref2.jpg"

# Upload da logo (PNG com transparência recomendado)
curl -X POST http://localhost:8000/api/v1/brands/ecobottle/logo \
  -F "file=@ecobottle_logo.png"
```

Ou simplesmente coloque os arquivos diretamente em:
- `brand_assets/docs/` — documentos
- `brand_assets/images/` — referências visuais
- `brand_assets/logo/ecobottle.png` — logo

### 2. Gerar os flyers

```bash
curl -X POST http://localhost:8000/api/v1/flyers/generate \
  -H "Content-Type: application/json" \
  -d '{
    "brief": "Lançamento do EcoBottle — garrafa sustentável para jovens de 18-30 anos.",
    "brand_id": "ecobottle",
    "brand": {
      "name": "EcoBottle",
      "primary_color": "#2D6A4F",
      "secondary_color": "#FFFFFF",
      "accent_color": "#95D5B2",
      "font_style": "modern sans-serif",
      "tone": "jovem e sustentável"
    },
    "platforms": ["instagram_feed", "instagram_story", "linkedin_post"]
  }'
```

> `brand_id` é opcional. Sem ele, os agentes usam apenas o perfil de marca do request.

---

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/flyers/generate` | Gera flyers para as plataformas selecionadas |
| `POST` | `/api/v1/brands/{id}/ingest/docs` | Upload de documentos da marca |
| `POST` | `/api/v1/brands/{id}/ingest/images` | Upload de imagens de referência |
| `POST` | `/api/v1/brands/{id}/logo` | Upload da logo da marca |
| `DELETE` | `/api/v1/brands/{id}/logo` | Remove a logo |
| `GET` | `/api/v1/brands/{id}/assets` | Lista todos os assets ingeridos |
| `DELETE` | `/api/v1/brands/{id}` | Remove todos os dados RAG da marca |
| `GET` | `/api/v1/health` | Health check |

---

## Testes

```bash
pytest tests/ -v
```

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | — | Chave OpenAI — **obrigatória** |
| `IMAGE_MODEL` | `gpt-image-1` | Modelo de geração de imagens |
| `IMAGE_QUALITY` | `high` | Qualidade da imagem (`low` `medium` `high`) |
| `MAX_REVISION_CYCLES` | `3` | Máximo de ciclos de revisão do LoopAgent |
| `API_PORT` | `8000` | Porta do servidor |
| `DEBUG` | `false` | Hot-reload |
| `CHROMA_BRAND_DIR` | `./chroma_db/brands` | Persistência do Brand RAG |
| `CHROMA_VISUAL_DIR` | `./chroma_db/visuals` | Persistência do Visual RAG |
