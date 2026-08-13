# Caderneta de Rendimentos

App estático (HTML/CSS/JS puro, sem build, sem backend) que:

- Projeta o rendimento das suas caixinhas/cofrinhos.
- Compara automaticamente qual banco/corretora rende mais líquido (já descontando IR).
- Busca a taxa CDI atual **ao vivo**, direto da API pública do Banco Central
  (`https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados/ultimos/1?formato=json`),
  toda vez que a página é aberta.

Tudo roda no navegador de quem acessa — não há servidor, não há coleta de dados,
os dados de cada pessoa ficam só no `localStorage` do navegador dela.

## Como colocar no ar (escolha uma opção)

### Opção 1 — Netlify Drop (mais rápido, no ar em ~1 minuto)

1. Acesse **https://app.netlify.com/drop**
2. Arraste esta pasta inteira (`caderneta-rendimentos`) para a área indicada.
3. Pronto — você recebe uma URL pública tipo `https://nome-aleatorio.netlify.app`.
4. (Opcional) Crie uma conta gratuita no Netlify para "reivindicar" o site,
   poder atualizar depois e trocar o nome da URL.

### Opção 2 — GitHub Pages (melhor para manter atualizando com o tempo)

1. Crie uma conta gratuita em **https://github.com** (se ainda não tiver).
2. Crie um repositório novo (pode ser público), ex: `caderneta-rendimentos`.
3. Neste projeto local, rode:
   ```
   git remote add origin https://github.com/SEU_USUARIO/caderneta-rendimentos.git
   git branch -M main
   git push -u origin main
   ```
4. No GitHub, vá em **Settings → Pages**, escolha a branch `main` e pasta `/root`.
5. Em alguns minutos o site fica no ar em `https://SEU_USUARIO.github.io/caderneta-rendimentos`.

### Opção 3 — Vercel

1. Crie uma conta gratuita em **https://vercel.com** (pode entrar com GitHub).
2. "Add New Project" → importe o repositório do GitHub (depois de fazer a Opção 2, passo 1–3)
   ou use o comando `vercel` da Vercel CLI direto nesta pasta.
3. Deploy automático, sem configuração — é um site estático puro.

## Depois de publicado

- Qualquer atualização: edite `index.html`, faça commit e push (ou arraste de novo no Netlify Drop) —
  o site atualiza para todo mundo.
- Domínio próprio (ex: `caderneta.com.br`): dá pra configurar depois, em qualquer uma das três opções,
  nas configurações de "Custom Domain" do provedor escolhido.

## Sobre a taxa CDI ao vivo

A API do Banco Central libera CORS para qualquer origem (`Access-Control-Allow-Origin: *`),
então o `fetch()` funciona direto do navegador, sem precisar de servidor/proxy.
Se a busca falhar (ex: usuário sem internet), o app mostra um aviso e usa o último
valor salvo no navegador da pessoa.
