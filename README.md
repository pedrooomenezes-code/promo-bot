# Bot de promoções (Mercado Livre → X)

De hora em hora (das 7h às 22h de Brasília), o bot:

1. lê os produtos de `produtos.csv`;
2. consulta o preço atual na API do Mercado Livre e guarda o histórico;
3. decide se é promoção de verdade;
4. monta o texto com o seu link de afiliado e a foto do produto;
5. agenda no X pelo Postiz, respeitando o intervalo entre posts e o limite diário.

Roda de graça no GitHub Actions, sem precisar deixar computador ligado.

## Quando o bot considera promoção

| Motivo | Regra (ajustável em `config.json`) |
|---|---|
| Desconto do anúncio | O anúncio mostra preço original e o desconto é de pelo menos 15%. Se já houver histórico, o preço também precisa estar abaixo da mediana dos dias anteriores (barra o "aumenta e dá desconto"). |
| Queda no histórico | Preço pelo menos 10% abaixo da mediana dos últimos 30 dias, com no mínimo 5 dias de histórico. |
| Preço-alvo | Chegou no `preco_alvo` que você colocou na planilha. |

Outras travas:
- O mesmo produto só volta a ser postado depois de 3 dias, a não ser que caia mais 5%.
- No máximo 6 posts por dia, com 40 minutos entre eles, das 8h às 23h. Aumente aos poucos, como no plano de aquecimento.
- "De R$ X por R$ Y" só aparece quando o próprio anúncio informa o preço original. O bot não inventa desconto.

## Modos (`config.json` → `"modo"`)

- `rascunho` (padrão): cria os posts como **rascunho** no Postiz. Você revisa e aprova no app. Comece assim.
- `agendar`: agenda direto, sem revisão.
- Para testar sem postar nada: `python -m bot --teste`.

## Configuração (uma vez)

### 1. Repositório no GitHub
Crie um repositório **privado** e suba esta pasta.

### 2. App no Mercado Livre (opcional)
Sem o app, o bot lê o preço direto da página do anúncio. O app só deixa a leitura mais estável. Se a sua conta não tiver permissão para criar aplicações ("No tenés permiso para crear aplicaciones"), pule este passo e não cadastre os secrets `ML_*` nem o `GH_PAT`.

1. Acesse developers.mercadolivre.com.br, faça login e crie uma aplicação.
2. Em Redirect URI, use qualquer endereço seu, por exemplo `https://www.google.com`.
3. Anote o **Client ID** e o **Client Secret**.
4. No seu computador, rode `python autorizar_ml.py` e siga as instruções. No fim, ele mostra o **refresh token**.

### 3. Postiz (publicação no X)
1. Crie uma conta em postiz.com e conecte o perfil do X.
2. Em Settings → Developers → Public API, gere a **API key**.
3. Descubra o id da integração do X. No computador:
   ```
   npm install -g postiz
   POSTIZ_API_KEY=sua_chave postiz integrations:list
   ```
   Copie o `id` da linha do X.

### 4. Token do GitHub (para o bot renovar o token do Mercado Livre sozinho)
Em GitHub → Settings → Developer settings → Fine-grained tokens, crie um token só para este repositório, com permissão **Secrets: Read and write**.

### 5. Secrets do repositório
Em Settings → Secrets and variables → Actions → New repository secret:

| Nome | Valor |
|---|---|
| `ML_CLIENT_ID` | Client ID do app do Mercado Livre |
| `ML_CLIENT_SECRET` | Client Secret |
| `ML_REFRESH_TOKEN` | resultado do `autorizar_ml.py` |
| `POSTIZ_API_KEY` | API key do Postiz |
| `POSTIZ_X_ID` | id da integração do X no Postiz |
| `GH_PAT` | token do passo 4 |

### 6. Ligar
Aba Actions → "Bot de promoções" → **Run workflow**. Com a caixa "Só testar" marcada, ele só mostra no log os posts que faria, sem agendar nada. Veja o log: cada produto aparece como "sem promoção", "já postado" ou "✔" com o texto do post.

## Uso do dia a dia

Para vigiar um produto novo:
1. Gere o link de afiliado dele no painel de afiliados do Mercado Livre.
2. Adicione uma linha em `produtos.csv` (dá para editar pelo site do GitHub):
   ```
   link do anúncio,link de afiliado,tech,,sim
   ```
3. Salve (commit). Na próxima hora o bot já começa a acompanhar.

O histórico leva alguns dias para se formar. Até lá, só entram descontos informados no próprio anúncio e produtos com preço-alvo.

## Arquivos

- `produtos.csv`: lista de produtos vigiados.
- `config.json`: regras e limites.
- `bot/`: o código (`ml.py` preço, `regras.py` decisão e agenda, `textos.py` modelos de post, `postiz.py` publicação).
- `data/`: histórico de preços e posts feitos (atualizado pelo próprio bot).
- `tests/`: testes (`python -m unittest`).
