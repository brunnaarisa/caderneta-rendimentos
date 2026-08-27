# 🤖 FinançasIA — Seu Consultor Financeiro Pessoal no Telegram

Bot de Telegram com inteligência artificial que funciona como um **consultor financeiro pessoal 24h**, ajudando pessoas a organizar suas finanças, sair de dívidas e começar a investir.

## 💡 O que faz (e por que as pessoas pagam)

Diferente de calculadoras genéricas, o FinançasIA:

1. **Entende SUA situação** — renda, gastos, dívidas, objetivos
2. **Cria um plano personalizado** — passo a passo para atingir seus objetivos
3. **Acompanha seu progresso** — você registra gastos pelo chat e ele analisa
4. **Dá alertas inteligentes** — "Você já gastou 80% do seu orçamento de alimentação"
5. **Ensina no seu ritmo** — dicas diárias adaptadas ao seu nível
6. **Compara investimentos** — busca CDI ao vivo e mostra onde seu dinheiro rende mais
7. **Monta estratégia de dívidas** — método avalanche ou bola de neve personalizado

## 💰 Modelo de monetização

| Recurso | Grátis | Premium (R$14,90/mês) |
|---------|--------|----------------------|
| Calculadora de rendimentos | ✅ | ✅ |
| Comparar bancos/corretoras | ✅ | ✅ |
| Consultas IA por dia | 3 | Ilimitadas |
| Registro de gastos | ❌ | ✅ |
| Plano financeiro personalizado | ❌ | ✅ |
| Alertas de orçamento | ❌ | ✅ |
| Relatório semanal | ❌ | ✅ |
| Estratégia de dívidas | ❌ | ✅ |
| Metas com acompanhamento | ❌ | ✅ |

## 🚀 Como rodar

### 1. Pré-requisitos

- Python 3.10+
- Uma conta no Telegram
- Chave de API da Anthropic (Claude) — [console.anthropic.com](https://console.anthropic.com)

### 2. Criar o bot no Telegram

1. Abra o Telegram e procure por **@BotFather**
2. Envie `/newbot`
3. Escolha um nome (ex: "FinançasIA") e um username (ex: `financas_ia_bot`)
4. Copie o **token** que o BotFather te dá

### 3. Configurar e rodar

```bash
cd bot

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com seu token do Telegram e chave da Anthropic

# Rodar o bot
python main.py
```

### 4. Hospedagem barata (para rodar 24h)

| Opção | Custo | Dificuldade |
|-------|-------|-------------|
| **Railway.app** | ~US$5/mês | Fácil |
| **Render.com** | Grátis (com limitações) | Fácil |
| **Oracle Cloud Free Tier** | Grátis (sempre) | Médio |
| **VPS na Hostinger** | ~R$15/mês | Médio |

## 📁 Estrutura do projeto

```
bot/
├── main.py              # Ponto de entrada — inicia o bot
├── config.py            # Configurações e variáveis de ambiente
├── requirements.txt     # Dependências Python
├── .env.example         # Template de variáveis de ambiente
│
├── handlers/            # Handlers de comandos e mensagens
│   ├── __init__.py
│   ├── start.py         # /start — onboarding do usuário
│   ├── consulta.py      # Consultas à IA
│   ├── gastos.py        # Registro e análise de gastos
│   ├── investimentos.py # Calculadora e comparador
│   ├── dividas.py       # Estratégia de dívidas
│   ├── metas.py         # Metas financeiras
│   └── premium.py       # Gestão de assinatura
│
├── services/            # Lógica de negócio
│   ├── __init__.py
│   ├── ai_advisor.py    # Integração com Claude (IA)
│   ├── cdi_service.py   # Busca CDI ao vivo do Banco Central
│   ├── finance_calc.py  # Cálculos financeiros
│   └── user_service.py  # Gestão de dados do usuário
│
└── database/            # Persistência de dados
    ├── __init__.py
    └── db.py            # SQLite para dados dos usuários
```

## 📊 Projeção de receita

Se o bot alcançar:
- **100 assinantes premium**: R$1.490/mês
- **500 assinantes premium**: R$7.450/mês
- **1.000 assinantes premium**: R$14.900/mês

Custo operacional estimado:
- API Claude: ~R$50-200/mês (dependendo do uso)
- Hospedagem: R$15-50/mês
- **Margem de lucro: 85-95%**

## 📜 Licença

MIT
