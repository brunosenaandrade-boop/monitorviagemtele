# Monitor de Viagens - Telegram Bot

Bot do Telegram para monitorar preços de passagens aéreas e receber alertas quando os preços caírem.

## Funcionalidades

- Criar monitoramentos de voos (origem, destino, datas)
- Buscar voos em tempo real
- Receber alertas quando o preço cair
- Definir preço máximo para alertas
- Histórico de preços
- Interface 100% pelo Telegram (botões interativos)

## Configuração

### 1. Criar Bot no Telegram

1. Abra o Telegram e busque por `@BotFather`
2. Envie `/newbot`
3. Siga as instruções e copie o **token** gerado

### 2. Criar conta na Amadeus (API de Voos)

1. Acesse [developers.amadeus.com](https://developers.amadeus.com)
2. Crie uma conta gratuita
3. Crie um novo app em "My Self-Service Workspace"
4. Copie a **API Key** e **API Secret**

> O plano gratuito permite 500 requisições/mês (suficiente para uso pessoal)

### 3. Configurar Variáveis de Ambiente

Copie o arquivo de exemplo e preencha:

```bash
cp .env.example .env
```

Edite o `.env`:

```
TELEGRAM_BOT_TOKEN=seu_token_do_botfather
AMADEUS_API_KEY=sua_api_key
AMADEUS_API_SECRET=seu_api_secret
CHECK_INTERVAL_MINUTES=60
```

### 4. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 5. Rodar o Bot

```bash
python bot.py
```

## Uso

1. Abra o Telegram e busque pelo seu bot
2. Envie `/start`
3. Use os botões para:
   - **Novo Monitoramento**: Criar alerta de preço
   - **Meus Monitoramentos**: Ver alertas ativos
   - **Buscar Voo Agora**: Pesquisa rápida de preços

### Fluxo de Monitoramento

```
1. Escolher origem (ex: GRU)
2. Escolher destino (ex: MIA)
3. Data de ida (ex: 25/12/2024)
4. Data de volta (opcional)
5. Quantidade de adultos
6. Preço máximo (opcional)
```

## Códigos de Aeroportos

### Brasil
| Código | Cidade |
|--------|--------|
| GRU | São Paulo - Guarulhos |
| CGH | São Paulo - Congonhas |
| GIG | Rio de Janeiro - Galeão |
| SDU | Rio de Janeiro - Santos Dumont |
| BSB | Brasília |
| CNF | Belo Horizonte - Confins |
| SSA | Salvador |
| REC | Recife |
| FOR | Fortaleza |
| POA | Porto Alegre |
| CWB | Curitiba |
| FLN | Florianópolis |

### Internacionais Populares
| Código | Cidade |
|--------|--------|
| MIA | Miami |
| MCO | Orlando |
| JFK | New York - JFK |
| EWR | New York - Newark |
| LIS | Lisboa |
| OPO | Porto |
| MAD | Madrid |
| BCN | Barcelona |
| CDG | Paris |
| FCO | Roma |
| LHR | Londres |
| AMS | Amsterdam |
| DXB | Dubai |
| BUE | Buenos Aires |
| SCL | Santiago |

## Deploy Gratuito

### Opção 1: Railway
1. Crie conta em [railway.app](https://railway.app)
2. Conecte seu repositório GitHub
3. Configure as variáveis de ambiente
4. Deploy automático!

### Opção 2: Render
1. Crie conta em [render.com](https://render.com)
2. Crie um "Background Worker"
3. Configure as variáveis de ambiente
4. Deploy!

### Opção 3: Rodar Local (sempre ligado)
Use `tmux` ou `screen` para manter rodando:

```bash
screen -S flightbot
python bot.py
# Ctrl+A, D para sair sem parar
```

## Estrutura do Projeto

```
flight-monitor/
├── bot.py              # Bot principal do Telegram
├── database.py         # Funções do banco de dados SQLite
├── flight_service.py   # Integração com API Amadeus
├── requirements.txt    # Dependências Python
├── .env.example        # Exemplo de configuração
└── README.md           # Este arquivo
```

## Limitações

- API Amadeus gratuita: 500 requisições/mês
- Verificação padrão: a cada 60 minutos
- Busca máxima: 5 voos por pesquisa

## Licença

MIT - Use como quiser!
