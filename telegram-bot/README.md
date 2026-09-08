# 🐷 Caderneta Bot — Bot de Telegram para Investimentos

Bot de Telegram que compara rendimentos de caixinhas, cofrinhos, CDBs, LCIs e LCAs entre os principais bancos do Brasil — com a taxa CDI sempre atualizada do Banco Central.

## 💰 Modelo de Monetização

O bot usa **4 fontes de receita combinadas**:

### 1. Assinatura Premium (R$ 9,90/mês via Pix)

| Recurso | Gratuito | Premium |
|---------|----------|---------|
| Consulta CDI/IPCA | ✅ | ✅ |
| Comparar bancos | 3x/dia (top 5) | ∞ (top 15) |
| Simular rendimento | 2x/dia | ∞ |
| Melhor alocação | ❌ | ✅ |
| Simulador de metas | ❌ | ✅ |
| Alertas CDI | ❌ | ✅ |

**Meta realista de receita:**
- 1.000 usuários → ~30 premium (3% conversão) → **R$ 297/mês**
- 5.000 usuários → ~150 premium → **R$ 1.485/mês**
- 10.000 usuários → ~300 premium → **R$ 2.970/mês**

### 2. Programa de Indicação (Growth Loop)

Cada usuário ganha um link personalizado. A cada **3 indicações**, ganha 1 mês de Premium grátis. Isso:
- Cresce a base de usuários organicamente (sem custo de marketing)
- Os indicados se tornam novos assinantes potenciais
- Efeito viral em grupos de finanças no Telegram

### 3. Tráfego para o Site (AdSense / Afiliados)

Toda resposta do bot inclui um link para `cadernetaderendimentos.com.br`. Você pode:
- Monetizar o site com **Google AdSense** (banners e intersticiais)
- Colocar **links de afiliado** para abertura de conta nos bancos (Nubank, Inter, C6 etc.)
- Corretoras pagam entre **R$ 20-80 por conta aberta** via indicação

### 4. Comprovante de Pagamento Manual

O fluxo de Pix é manual por design (sem custo de gateway):
1. Usuário clica "Pagar via Pix"
2. Bot mostra sua chave Pix
3. Usuário envia comprovante como foto
4. Foto é encaminhada pra você (admin) no Telegram
5. Você ativa o Premium com `/ativar <user_id>`

> Quando escalar (50+ pagamentos/mês), integre com gateway automático (Stripe, Mercado Pago API, ou Pagar.me).

---

## 🚀 Como Colocar no Ar

### Passo 1: Criar o bot no Telegram

1. Abra o Telegram e fale com [@BotFather](https://t.me/BotFather)
2. Envie `/newbot`
3. Escolha um nome (ex: "Caderneta de Rendimentos")
4. Escolha um username (ex: `caderneta_rendimentos_bot`)
5. Copie o **token** que ele vai te dar

### Passo 2: Configurar

```bash
cd telegram-bot
cp .env.example .env
# Edite o .env com seu token e dados
```

### Passo 3: Instalar e rodar (local)

```bash
pip install -r requirements.txt
export BOT_TOKEN="seu-token-aqui"
export ADMIN_USER_ID="seu-user-id"
export PIX_KEY="sua-chave-pix"
python bot.py
```

### Passo 4: Deploy permanente (escolha uma opção)

#### Opção A — Railway (mais fácil, grátis pra começar)

1. Crie conta em [railway.app](https://railway.app)
2. "New Project" → "Deploy from GitHub Repo"
3. Aponte para este repositório, pasta `telegram-bot/`
4. Adicione as variáveis de ambiente (BOT_TOKEN, ADMIN_USER_ID, PIX_KEY)
5. Deploy automático!

**Custo:** Grátis até $5/mês de uso → depois ~$5/mês

#### Opção B — VPS barata (mais controle)

```bash
# Na VPS (ex: Oracle Cloud grátis, ou DigitalOcean $4/mês)
git clone https://github.com/brunnaarisa/caderneta-rendimentos.git
cd caderneta-rendimentos/telegram-bot
docker build -t caderneta-bot .
docker run -d --restart always \
  -e BOT_TOKEN="..." \
  -e ADMIN_USER_ID="..." \
  -e PIX_KEY="..." \
  --name caderneta-bot caderneta-bot
```

#### Opção C — Oracle Cloud Always Free (custo zero)

Oracle oferece uma VM ARM gratuita pra sempre. Tutorial rápido:
1. Crie conta em [cloud.oracle.com](https://cloud.oracle.com) (pede cartão mas não cobra)
2. Crie uma instância "Always Free" (ARM, 1 OCPU, 6GB RAM)
3. SSH na VM e siga os passos da Opção B

---

## 📊 Comandos do Bot

### Públicos (gratuitos com limite)
| Comando | Descrição |
|---------|-----------|
| `/start` | Mensagem de boas-vindas |
| `/cdi` | Taxa CDI e IPCA atuais |
| `/bancos` | Lista bancos e produtos |
| `/comparar 10000 12` | Compara rendimento de R$10k em 12 meses |
| `/simular Nubank 5000 6` | Simula R$5k no Nubank por 6 meses |
| `/ajuda` | Lista todos os comandos |

### Premium (ilimitado)
| Comando | Descrição |
|---------|-----------|
| `/melhor 50000 12` | Melhor distribuição pra R$50k em 12 meses |
| `/meta 100000 10000 24` | Quanto guardar/mês pra atingir R$100k |

### Conta
| Comando | Descrição |
|---------|-----------|
| `/premium` | Ver planos e assinar |
| `/indicar` | Link de indicação |
| `/minhaconta` | Ver plano, uso e estatísticas |

### Admin
| Comando | Descrição |
|---------|-----------|
| `/stats` | Estatísticas do bot |
| `/ativar 123456 1` | Ativar Premium pra user 123456 por 1 mês |

---

## 📈 Estratégia de Crescimento

### Semana 1-2: Lançamento
- [ ] Publicar em grupos de finanças pessoais no Telegram
- [ ] Postar no Reddit r/investimentos e r/farialimabets
- [ ] Compartilhar no Twitter/X com hashtags #investimentos #rendafixa
- [ ] Canal do YouTube shorts mostrando o bot funcionando

### Mês 1: Tração
- [ ] Criar canal próprio no Telegram com dicas diárias
- [ ] Parcerias com canais de finanças (eles divulgam, ganham código de indicação)
- [ ] TikTok/Reels: "Seu banco te rouba? Descubra em 5 segundos" (link pro bot)

### Mês 2-3: Monetização
- [ ] Com 1.000+ usuários: implementar gateway de pagamento automático
- [ ] Adicionar links de afiliado dos bancos no site
- [ ] Google AdSense no site (tráfego vindo do bot)

### Mês 3+: Escala
- [ ] Notificações diárias (resumo matinal pro canal do Telegram)
- [ ] Ranking semanal: "Top 5 rendimentos desta semana"
- [ ] Comparador de cartão de crédito (nova vertical)

---

## 🔧 Estrutura do Projeto

```
telegram-bot/
├── bot.py              # Bot principal (handlers de comando)
├── catalog.py          # Catálogo de bancos e produtos
├── calculator.py       # Motor de cálculos financeiros
├── cdi_fetcher.py      # Busca CDI/IPCA ao vivo do Banco Central
├── subscriptions.py    # Gerenciamento de planos e limites (SQLite)
├── requirements.txt    # Dependências Python
├── Dockerfile          # Container pra deploy
├── .env.example        # Template de variáveis de ambiente
└── README.md           # Este arquivo
```

---

## ⚠️ Importante

- As taxas do catálogo são **informativas** — sempre confira no app do banco antes de investir.
- O bot **não** faz recomendação de investimento — ele compara dados públicos.
- Adicione esse disclaimer nas mensagens se for escalar: _"Este bot é apenas informativo e não constitui recomendação de investimento."_

---

## 📋 Próximos Passos

- [ ] Integrar API do Mercado Pago ou Stripe para cobrar Premium automaticamente
- [ ] Webhook de CDI: enviar mensagem quando a Selic mudar
- [ ] Integração com a API do Telegram para pagamentos nativos (Telegram Stars)
- [ ] Dashboard admin web com métricas de uso
- [ ] Cache de respostas do bot (Redis) quando escalar
