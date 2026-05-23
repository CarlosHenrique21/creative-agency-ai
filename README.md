# Social Media Agency AI

Sistema multiagente interativo para geração de flyers para redes sociais com aprovação humana em pontos-chave.  
Orquestrado com **Google ADK**, modelos de texto **GPT-4o** e geração de imagens **gpt-image-1**.

---

## Pipeline interativo

O pipeline roda em três fases com duas pausas para input humano:

```
Usuário envia brief
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  FASE 1 — Pesquisa e escolha de tema                    │
│                                                         │
│  Brand Strategist → Visual Analyst → Market Analyst     │
│                                                         │
│  [PAUSA] Usuário escolhe um dos temas sugeridos         │
│                                                         │
│  Theme Selector — registra tema no estado               │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  FASE 2 — Direção criativa e textos                     │
│                                                         │
│  Creative Director → Copywriter → Copy Approver         │
│                                                         │
│  [PAUSA] Usuário aprova ou solicita alterações          │
│                                                         │
│  Copy Reviewer — aplica alterações ou confirma          │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  FASE 3 — Geração de imagens (LoopAgent, máx 3 ciclos) │
│                                                         │
│  Designer → Social Media Manager → Quality Reviewer     │
│                                                         │
│  Quality Reviewer chama exit_loop quando aprovado       │
└─────────────────────────────────────────────────────────┘
        │
        ▼
   Flyers entregues
```

### Agentes

| Agente | Fase | Responsabilidade |
|---|---|---|
| **Brand Strategist** | 1 | Inicializa campanha, consulta RAG de documentos, define posicionamento |
| **Visual Analyst** | 1 | Analisa imagens de referência com GPT-4o Vision, gera `visual_spec` |
| **Market Analyst** | 1 | Pesquisa tendências do mercado, sugere 5 temas, pausa para escolha |
| **Theme Selector** | 1 | Interpreta escolha do usuário, salva tema no estado |
| **Creative Director** | 2 | RAG de marca + tema → conceito criativo, mood, tom de voz |
| **Copywriter** | 2 | Escreve headline, subheadline, body copy e CTA por plataforma |
| **Copy Approver** | 2 | Exibe textos formatados, pausa para aprovação ou alteração |
| **Copy Reviewer** | 2 | Aplica alterações solicitadas ou confirma aprovação |
| **Designer** | 3 | Monta prompt visual detalhado → gera imagem com `gpt-image-1` → compõe logo |
| **Social Media Manager** | 3 | Avalia boas práticas de cada plataforma |
| **Quality Reviewer** | 3 | Notas 0-10 em 4 critérios; aprova (≥ 7.5) ou aciona nova iteração |

### Plataformas suportadas

| Plataforma | Resolução | Posição da logo |
|---|---|---|
| `instagram_feed` | 1024×1024 px | Rodapé centralizado |
| `instagram_story` | 1024×1536 px | Topo centralizado |
| `linkedin_post` | 1536×1024 px | Rodapé centralizado |
| `linkedin_banner` | 1536×1024 px | Centro esquerdo |

---

## Stack

- **Google ADK** — orquestração (`SequentialAgent` + `LoopAgent` + `LongRunningFunctionTool`)
- **GPT-4o** — todos os agentes de texto e análise de imagens (Vision)
- **gpt-image-1** — geração de imagens dos flyers
- **Pillow** — composição da logo sobre o flyer gerado
- **ChromaDB** — vector store local para RAG de documentos e referências visuais
- **FastAPI** — API REST
- **Pydantic** — validação de schemas

---

## Sistemas RAG

### Brand RAG — documentos da marca
Ingere arquivos da marca, chunka, embeda com `text-embedding-3-small` e persiste no ChromaDB.  
Consultado pelo **Brand Strategist** e **Creative Director**.

Formatos suportados: `.pdf` `.docx` `.txt` `.md` `.json` `.html` `.htm`

### Visual RAG — referências visuais
Cada imagem é analisada pelo **GPT-4o Vision**, que extrai estilo, mood, paleta, composição e elementos de UI.  
A descrição é embeddada e armazenada no ChromaDB.  
Consultado pelo **Visual Analyst** e **Designer** para ancorar o prompt do `gpt-image-1`.

Formatos suportados: `.jpg` `.png` `.webp`

---

## Estrutura do projeto

```
social-media-agency/
├── agent.py                 # Entry point do ADK — exporta App com resumability_config
├── agents/
│   ├── brand_strategist/    # LlmAgent — posicionamento de marca
│   ├── visual_analyst/      # LlmAgent — análise visual com Vision
│   ├── market_analyst/      # LlmAgent — pesquisa de mercado + pausa para escolha de tema
│   ├── theme_selector/      # LlmAgent — registra tema escolhido
│   ├── creative_director/   # LlmAgent — direção criativa
│   ├── copywriter/          # LlmAgent — textos por plataforma
│   ├── copy_approver/       # LlmAgent — exibe textos + pausa para aprovação
│   ├── copy_reviewer/       # LlmAgent — aplica alterações ou confirma
│   ├── designer/            # LlmAgent — prompts visuais + geração de imagens
│   ├── social_media_manager/# LlmAgent — revisão de boas práticas
│   └── quality_reviewer/    # LlmAgent — scoring e aprovação final
├── tools/
│   ├── image_tools.py       # generate_flyer_image (gpt-image-1 + logo)
│   ├── rag_tools.py         # query_brand_knowledge, query_visual_references
│   ├── copy_tools.py        # write_platform_copy
│   ├── quality_tools.py     # score_flyer_quality
│   ├── state_tools.py       # initialize_campaign, set_selected_theme, apply_copy_changes
│   ├── human_approval_tools.py  # request_theme_selection, request_copy_approval (LongRunningFunctionTool)
│   ├── visual_analysis_tools.py # analyze_brand_images (GPT-4o Vision)
│   └── market_tools.py      # analyze_market_trends
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
│   ├── logo_compositor.py   # Pillow — composição da logo (escala 32%, rodapé central)
│   ├── ingest_cli.py        # CLI de ingestão
│   └── dependencies.py      # singletons dos stores
├── models/                  # schemas Pydantic de request/response
├── brand_assets/
│   ├── docs/                # documentos da marca (.pdf, .docx, .html, etc.)
│   ├── images/              # imagens de referência visual
│   └── logo/                # logo da marca (<brand_id>.png)
└── tests/
```

---

## Configuração

```bash
# 1. Instalar dependências
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

## Rodando com o ADK Web (recomendado)

```bash
PYTHONPATH=. uv run adk web .
```

Abre `http://localhost:8000` com uma interface de chat onde você conversa diretamente com o pipeline.

### Como usar

1. Envie uma mensagem descrevendo a campanha:

   > *Quero criar flyers para instagram_feed e linkedin_post. Marca: BussolaFiscal brand_id: bussola_fiscal*

2. O pipeline perguntará o briefing caso não tenha sido fornecido.

3. O **Market Analyst** pesquisa tendências e apresenta 5 temas sugeridos — escolha pelo número ou descreva uma variação.

4. O **Copy Approver** exibe os textos criados para todos os formatos. Responda `APROVADO` para continuar ou descreva as alterações desejadas.

5. O **Designer** gera as imagens com `gpt-image-1` e compõe a logo automaticamente. O **Quality Reviewer** avalia e aprova ou solicita revisão.

### Preparar os assets da marca

Coloque os arquivos diretamente nas pastas antes de rodar:

```
brand_assets/docs/      ← brand guide, briefing, manual de identidade
brand_assets/images/    ← prints do produto, moodboard, referências visuais
brand_assets/logo/      ← <brand_id>.png (recomendado PNG com fundo transparente)
```

Ou ingira via CLI:

```bash
# Documentos
PYTHONPATH=. uv run python -m rag.ingest_cli docs --brand-id bussola_fiscal --dir ./brand_assets/docs

# Imagens de referência
PYTHONPATH=. uv run python -m rag.ingest_cli images --brand-id bussola_fiscal --dir ./brand_assets/images
```

### O que observar durante o pipeline

| Evento no ADK Web | Significado |
|---|---|
| `analyze_brand_images` chamada | GPT-4o Vision analisando referências visuais |
| `analyze_market_trends` chamada | Pesquisa de tendências do mercado |
| Pipeline pausado após temas | Aguardando sua escolha de tema |
| `write_platform_copy` chamada | Textos salvos no estado por plataforma |
| Pipeline pausado após textos | Aguardando aprovação ou alteração |
| `generate_flyer_image` chamada | gpt-image-1 gerando + logo sendo composta |
| `score_flyer_quality` chamada | Notas atribuídas; se média < 7.5 o loop repete |
| `exit_loop` chamada | Todos os flyers aprovados |

---

## Rodando via API

```bash
PYTHONPATH=. uv run python main.py
# ou com hot-reload:
PYTHONPATH=. uv run uvicorn main:app --reload
```

Documentação interativa: `http://localhost:8000/docs`

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
    "platforms": ["instagram_feed", "linkedin_post"]
  }'
```

---

## Endpoints da API

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
