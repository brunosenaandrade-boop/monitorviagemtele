# Monitor de Viagens

Bot do Telegram para monitorar preços de passagens aéreas com landing page de captura de leads.

## Stack

- **Frontend:** Landing page HTML/CSS/JS
- **Backend:** Vercel Serverless Functions (Python)
- **Bot:** Telegram Bot API (Webhook)
- **Database:** Upstash Redis
- **API de Voos:** Amadeus

## Estrutura do Projeto

```
├── index.html          # Landing page de captura de leads
├── api/
│   └── webhook.py      # Bot do Telegram (serverless)
├── vercel.json         # Configuração do Vercel
├── requirements.txt    # Dependências Python
└── README.md           # Documentação
```

## Funcionalidades

### Landing Page
- Design moderno e responsivo
- Captura de leads (WhatsApp)
- Integração com Google Sheets
- Elementos de alta conversão

### Bot Telegram
- Busca de aeroportos por nome da cidade
- Pesquisa de voos em tempo real
- Criação de monitoramentos
- Alertas de preço

## URLs

- **Landing Page:** https://viagem.seumotoristavip.com.br
- **Bot Telegram:** @meu_monitor_viagens_bot

## Variáveis de Ambiente

Configure no Vercel:

```
TELEGRAM_BOT_TOKEN=seu_token
AMADEUS_API_KEY=sua_key
AMADEUS_API_SECRET=seu_secret
UPSTASH_REDIS_REST_URL=sua_url
UPSTASH_REDIS_REST_TOKEN=seu_token
```

## APIs Utilizadas

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Amadeus Flight API](https://developers.amadeus.com)
- [Upstash Redis](https://upstash.com)
- [Google Sheets API](https://developers.google.com/sheets)

## Deploy

O projeto está hospedado no Vercel com deploy automático via GitHub.

## Licença

MIT
