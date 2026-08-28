# 🤖 FinançasIA — Consultor Financeiro com IA no Telegram

Bot de Telegram com inteligência artificial que funciona como um **consultor financeiro pessoal 24h**. Analisa mercado ao vivo, monta planos de investimento, monitora sua carteira e te avisa na hora certa de comprar e vender.

## 🔥 O que faz

- **🧠 Consultor IA 24h** — Pergunte qualquer dúvida financeira
- **📈 Análise de mercado ao vivo** — 13+ ativos (criptos + ações da B3)
- **🎯 Planos personalizados** — "Quero investir 500 e ganhar 100" → plano com análise ao vivo
- **💼 Carteira inteligente** — Registra compras, mostra lucro/prejuízo em tempo real
- **🛑 Stop-loss automático** — Proteção criada a cada compra (-10% / +25%)
- **🚨 Alertas urgentes** — "COMPRE BTC AGORA!" quando detecta oportunidade
- **🎯 Alertas de preço** — Avisa quando o ativo chega no preço que você quer
- **📡 Radar de oportunidades** — Escaneia 13 ativos e rankeia os melhores
- **☀️ Resumo matinal** — Briefing diário às 7h com mercado + carteira
- **🤖 Consultor proativo** — O bot te procura quando vê oportunidade
- **📊 Calculadora de IR** — Imposto de Renda sobre investimentos
- **📈 Evolução da carteira** — Gráfico histórico de performance
- **🏆 Gamificação** — XP, níveis, conquistas, streak, ranking
- **💳 Pagamento via Pix** — Premium com Mercado Pago automático

## 💰 Modelo de monetização

| Recurso | Grátis | Premium (R$14,90/mês) |
|---------|--------|----------------------|
| Consultas IA por dia | 3 | ♾️ Ilimitadas |
| Análise de mercado | ✅ | ✅ |
| Radar de oportunidades | ✅ | ✅ |
| O que eu faria (plano) | ✅ | ✅ |
| Carteira com alertas | ❌ | ✅ |
| Stop-loss automático | ❌ | ✅ |
| Evolução da carteira | ❌ | ✅ |
| Alertas urgentes | ✅ | ✅ |
| Alertas de preço-alvo | ✅ | ✅ |
| Resumo matinal | ✅ | ✅ |
| Registro de gastos | ❌ | ✅ |
| Calculadora de IR | ✅ | ✅ |
| Gamificação completa | ✅ | ✅ |

### 📊 Projeção de receita

| Assinantes | Receita/mês | Receita/ano |
|------------|-------------|-------------|
| 100 | R$1.490 | R$17.880 |
| 500 | R$7.450 | R$89.400 |
| 1.000 | R$14.900 | R$178.800 |

Custo operacional: ~R$65-250/mês (API Claude + hospedagem). **Margem: 85-95%**.

## 🚀 Como rodar

### 1. Criar o bot no Telegram

1. Abra o Telegram e procure por **@BotFather**
2. Envie `/newbot`
3. Escolha um nome (ex: "FinançasIA") e um username (ex: `financas_ia_bot`)
4. Copie o **token** que o BotFather te dá
5. Envie `/setdescription` e cole:
   ```
   🤖 Seu consultor financeiro com IA! Analiso mercado ao vivo, digo o que comprar, monitoro sua carteira e te aviso na hora de vender. Comece com /start
   ```
6. Envie `/setcommands` e cole:
   ```
   start - 🏠 Começar / Recomeçar
   ajuda - 📖 Ver todos os comandos
   oquefazer - 🔥 O que comprar hoje (análise ao vivo)
   radar - 📡 Escanear oportunidades
   analisar - 📈 Analisar um ativo (ex: /analisar btc)
   comprei - 📝 Registrar uma compra
   carteira - 💼 Ver minhas posições
   evolucao - 📊 Gráfico de evolução
   alvo - 🎯 Criar alerta de preço
   bomdia - ☀️ Ativar resumo matinal
   seguir - 👁️ Seguir um ativo
   meusativos - 📋 Minha watchlist
   painel - 📊 Dashboard completo
   premium - 💎 Plano Premium
   ```

### 2. Obter chave da API Anthropic (Claude)

1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. Crie uma conta
3. Vá em **API Keys** e crie uma nova chave
4. Copie a chave (começa com `sk-ant-`)

### 3. (Opcional) Configurar Mercado Pago para receber Pix

1. Acesse [mercadopago.com.br/developers](https://www.mercadopago.com.br/developers)
2. Crie uma **Aplicação**
3. Vá em **Credenciais de Produção**
4. Copie o **Access Token** (começa com `APP_USR-`)

### 4. Configurar e rodar

```bash
cd bot

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
nano .env  # Editar com seus tokens

# Rodar o bot
python main.py
```

### 5. Hospedagem (para rodar 24h)

| Opção | Custo | Dificuldade | Recomendo? |
|-------|-------|-------------|------------|
| **Railway.app** | ~US$5/mês | ⭐ Fácil | ✅ Melhor pra começar |
| **Render.com** | Grátis* | ⭐ Fácil | ⚠️ Desliga após inatividade |
| **Oracle Cloud Free** | Grátis sempre | ⭐⭐ Médio | ✅ Melhor custo-benefício |
| **VPS Hostinger** | ~R$15/mês | ⭐⭐ Médio | ✅ Bom e barato |
| **DigitalOcean** | US$4/mês | ⭐⭐ Médio | ✅ Confiável |

#### Deploy rápido no Railway:

1. Faça fork deste repositório
2. Acesse [railway.app](https://railway.app) e conecte seu GitHub
3. Crie novo projeto → Deploy from GitHub repo
4. Adicione as variáveis de ambiente (Settings → Variables)
5. Deploy automático! 🚀

## 🗂️ Todos os comandos (40+)

### 💬 Consultar a IA
- Envie qualquer dúvida financeira!
- Ou diga: _"quero investir 500 e ganhar 100 em 1 semana"_

### 📊 Investimentos
| Comando | O que faz |
|---------|-----------|
| `/oquefazer` | 🔥 Plano do que comprar hoje com análise ao vivo |
| `/desafio` | 🎯 Meta: "Quero ganhar X investindo Y em Z tempo" |
| `/analisar [ativo]` | 📈 Análise técnica completa (RSI, médias, suporte) |
| `/simular` | 📈 Projeção de patrimônio futuro |
| `/investir` | Calcular rendimento |
| `/comparar` | Comparar bancos/corretoras |
| `/perfil` | Seu perfil de investidor |
| `/sugestoes` | Investimentos para o seu perfil |

### 📡 Radar & Alertas
| Comando | O que faz |
|---------|-----------|
| `/radar` | 📡 Escaneia 13 ativos e rankeia oportunidades |
| `/alvo [ativo] [preço]` | 🎯 Alerta quando o preço chegar lá |
| `/alvos` | 📋 Seus alertas de preço ativos |
| `/removeralvo [id]` | 🗑️ Remover alerta |
| `/alertamercado` | 🚨 Ativar alertas URGENTES de mercado |
| `/bomdia` | ☀️ Resumo matinal personalizado (7h) |
| `/seguir [ativo]` | 👁️ Adicionar à watchlist |
| `/desseguir [ativo]` | ❌ Remover da watchlist |
| `/meusativos` | 📋 Watchlist com preços ao vivo |

### 💼 Carteira
| Comando | O que faz |
|---------|-----------|
| `/comprei` | 📝 Registrar compra (cria stop-loss automático!) |
| `/carteira` | 💼 Posições com lucro/prejuízo ao vivo |
| `/evolucao` | 📈 Gráfico de evolução da carteira |
| `/snapshot` | 📸 Salvar snapshot manual |
| `/alertas` | 🔔 Configurar alertas automáticos |
| `/ir` | 📊 Calculadora de Imposto de Renda |
| `/compartilhar` | 🏆 Compartilhar resultados nas redes |

### 🤖 Automação
| Comando | O que faz |
|---------|-----------|
| `/aporte` | 🚀 Plano mensal (aviso o que comprar no dia do salário) |
| `/meuplano` | Ver plano mensal |

### 🎓 Aprender
| Comando | O que faz |
|---------|-----------|
| `/aprender` | 📚 Aulas passo a passo (do zero) |
| `/comocomprar` | 📖 Como comprar cada tipo de ativo |
| `/dicadodia` | 💡 Dica financeira do dia |

### 🛠️ Ferramentas
| Comando | O que faz |
|---------|-----------|
| `/painel` | 📊 Dashboard financeiro completo |
| `/versus` | ⚔️ Comparar dois ativos ao vivo |
| `/aposentar` | 🏖️ Calculadora FIRE |

### 🏆 Gamificação
| Comando | O que faz |
|---------|-----------|
| `/conquistas` | ⭐ XP, nível, conquistas e streak |
| `/ranking` | 🏅 Ranking global |
| `/indicar` | 🤝 Convide amigos e ganhe bônus |

### ⚙️ Outros
| Comando | O que faz |
|---------|-----------|
| `/premium` | 💎 Assinar Premium (Pix) |
| `/verificarpix` | 🔍 Verificar pagamento |
| `/gasto` | 💸 Registrar gasto |
| `/resumo` | 📊 Resumo de gastos |
| `/orcamento` | 💰 Orçamento mensal |
| `/dividas` | 💳 Ver/cadastrar dívidas |
| `/meta` | 🎯 Criar meta financeira |

## ⚙️ Jobs automáticos (10)

| Job | Frequência | O que faz |
|-----|-----------|-----------|
| Alertas de carteira | 1h | Verifica posições e envia alertas |
| Lembrete de aporte | Diário 8h | Avisa o que comprar no dia do salário |
| Relatório semanal | Domingo 10h | Resumo da semana com sugestões |
| Dica diária | Diário 9h | Dica financeira do dia |
| Oportunidades urgentes | 2h | Escaneia mercado (RSI, Fear&Greed) |
| Alertas de preço | 1h | Verifica alertas de preço-alvo |
| Resumo matinal | Diário 7h | Briefing personalizado |
| Snapshots carteira | Diário 20h | Salva histórico de performance |
| Verificar pagamentos | 5min | Confirma Pix e ativa premium |
| Consultor proativo | Diário 14h | Envia sugestões inteligentes |

## 📁 Estrutura do projeto

```
bot/
├── main.py                    # Ponto de entrada (25 handler groups)
├── config.py                  # Configurações e variáveis de ambiente
├── requirements.txt           # Dependências Python
├── .env.example               # Template de variáveis de ambiente
│
├── handlers/                  # Handlers de comandos (15 módulos)
│   ├── start.py               # /start — onboarding + referral
│   ├── consulta.py            # IA + NLP para objetivos de investimento
│   ├── carteira.py            # /comprei, /carteira, /alertas + stop-loss
│   ├── oquefazer.py           # /oquefazer — plano de compra ao vivo
│   ├── desafio.py             # /desafio — meta de rendimento
│   ├── radar.py               # /radar — scanner de 13 ativos
│   ├── alerta_preco.py        # /alvo — alertas de preço-alvo
│   ├── alerta_mercado.py      # /alertamercado — alertas urgentes
│   ├── resumo_matinal.py      # /bomdia — briefing matinal
│   ├── watchlist.py           # /seguir — watchlist personalizada
│   ├── evolucao.py            # /evolucao — gráfico de performance
│   ├── compartilhar.py        # /compartilhar — social sharing
│   ├── imposto_renda.py       # /ir — calculadora de IR
│   ├── premium.py             # /premium — pagamento via Pix
│   ├── ferramentas.py         # /painel, /versus, /aposentar
│   ├── gamificacao.py         # /conquistas, /ranking, /indicar
│   └── ... (gastos, dividas, metas, etc.)
│
├── services/                  # Lógica de negócio
│   ├── ai_advisor.py          # Integração com Claude (IA)
│   ├── market_analysis.py     # Análise técnica + APIs de mercado
│   ├── portfolio_service.py   # CRUD da carteira
│   ├── payment_service.py     # Mercado Pago (Pix)
│   ├── alert_scheduler.py     # 10 jobs automáticos
│   ├── gamification_service.py# XP, níveis, conquistas
│   └── ... (user, finance, cdi, aporte)
│
└── database/
    └── db.py                  # SQLite — 17 tabelas
```

## 📜 Licença

MIT
