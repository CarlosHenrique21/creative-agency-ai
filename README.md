# Social Media Agency — Sistema Multiagente

Sistema multiagente para geração automatizada de flyers para redes sociais, construído com LangGraph + FastAPI + gpt-image-1.

## Arquitetura

```
Brief da Campanha
      │
      ▼
┌─────────────────┐
│ Brand Strategist│  Analisa o brief e consolida diretrizes de marca
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Creative Director  │  Cria o conceito criativo e direção visual
└────────┬────────────┘
         │
         ▼
┌─────────────────┐
│   Copywriter    │  Escreve headline, copy e CTA por plataforma
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Designer     │  Gera prompts e chama gpt-image-1
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│ Social Media Manager │  Revisa boas práticas de cada plataforma
└────────┬─────────────┘
         │
         ▼
┌──────────────────┐
│ Quality Reviewer │  Atribui notas (0-10) e aprova ou pede revisão
└────────┬─────────┘
         │
    aprovado? ──── não ──→ volta ao Copywriter (máx 3 ciclos)
         │
        sim
         │
         ▼
    Flyers entregues
```

### Plataformas suportadas
| Plataforma | Resolução |
|---|---|
| Instagram Feed | 1080×1080px |
| Instagram Story | 1080×1920px |
| LinkedIn Post | 1200×627px |
| LinkedIn Banner | 1584×396px |

## Configuração

```bash
# 1. Instalar dependências
pip install -e ".[dev]"

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env e adicione sua OPENAI_API_KEY

# 3. Rodar o servidor
python main.py
# ou
uvicorn main:app --reload
```

## Uso

### Via API REST

```bash
curl -X POST http://localhost:8000/api/v1/flyers/generate \
  -H "Content-Type: application/json" \
  -d '{
    "brief": "Lançamento do produto EcoBottle — garrafa sustentável para jovens 18-30.",
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

### Documentação interativa
Após iniciar o servidor, acesse: `http://localhost:8000/docs`

## Estrutura do projeto

```
social-media-agency/
├── agents/
│   ├── brand_strategist/    # Análise de marca e posicionamento
│   ├── creative_director/   # Direção criativa da campanha
│   ├── copywriter/          # Redação de textos por plataforma
│   ├── designer/            # Geração de imagens com gpt-image-1
│   ├── social_media_manager/# Revisão de boas práticas
│   └── quality_reviewer/    # Avaliação de qualidade e aprovação
├── api/                     # Rotas FastAPI
├── core/
│   ├── config.py            # Configurações via .env
│   ├── orchestrator.py      # Grafo LangGraph
│   └── state.py             # Estado compartilhado da campanha
├── models/                  # Schemas de request/response
├── prompts/                 # System prompts de cada agente
├── output/
│   ├── flyers/              # Imagens geradas
│   └── reports/             # Logs de campanha
└── tests/
```

## Testes

```bash
pytest tests/ -v
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | — | Chave da API OpenAI (obrigatória) |
| `IMAGE_MODEL` | `gpt-image-1` | Modelo de geração de imagens |
| `IMAGE_QUALITY` | `high` | Qualidade da imagem (`low`, `medium`, `high`) |
| `MAX_REVISION_CYCLES` | `3` | Máximo de ciclos de revisão |
| `API_PORT` | `8000` | Porta do servidor |
| `DEBUG` | `false` | Modo debug com hot-reload |
